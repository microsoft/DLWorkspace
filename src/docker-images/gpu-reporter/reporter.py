#!/usr/bin/env python3

import time
import urllib.parse
import threading
import argparse
import logging
import datetime
import timeit
import collections
import faulthandler
import signal
import copy

import requests

import flask
from flask import Flask
from flask import request
from flask import Response
from flask_cors import CORS

import prometheus_client
from prometheus_client import Histogram
from prometheus_client.core import REGISTRY
from prometheus_client.core import GaugeMetricFamily

logger = logging.getLogger(__name__)

prometheus_request_histogram = Histogram(
    "reporter_req_latency_seconds",
    "latency for reporter requesting prometheus (seconds)",
    buckets=(.05, .075, .1, .25, .5, .75, 1.0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0,
             17.5, 20.0, float("inf")))

reporter_iteration_histogram = Histogram(
    "reporter_iteration_seconds",
    "latency for reporter to iterate one pass (seconds)",
    buckets=(.05, .075, .1, .25, .5, .75, 1.0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0,
             17.5, 20.0, float("inf")))


class AtomicRef(object):
    """ a thread safe way to store and get object,
    should not modify data get from this ref
    """
    def __init__(self):
        self.data = None
        self.lock = threading.RLock()

    def set(self, data):
        with self.lock:
            self.data = data

    def get(self):
        with self.lock:
            return self.data


def walk_json_field_safe(obj, *fields):
    """ for example a=[{"a": {"b": 2}}]
    walk_json_field_safe(a, 0, "a", "b") will get 2
    walk_json_field_safe(a, 0, "not_exist") will get None
    """
    try:
        for f in fields:
            obj = obj[f]
        return obj
    except:
        return None


def request_with_error_handling(url, timeout=180):
    try:
        response = requests.get(url, allow_redirects=True, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.exception(e)
        return None


def query_prometheus(prometheus_url, query, since, end, step_minute):
    args = urllib.parse.urlencode({
        "query": query,
        "start": str(since),
        "end": str(end),
        "step": str(step_minute) + "m",
    })

    url = urllib.parse.urljoin(prometheus_url,
                               "/prometheus/api/v1/query_range") + "?" + args

    start = timeit.default_timer()
    obj = request_with_error_handling(url)
    elapsed = timeit.default_timer() - start
    prometheus_request_histogram.observe(elapsed)
    logger.info("request spent %.2fs", elapsed)

    if walk_json_field_safe(obj, "status") != "success":
        logger.warning("requesting %s failed, body is %s", url, obj)
        return None

    return obj


def copy_without_next(m):
    result = {}
    for k, v in m.items():
        if k == "next":
            continue
        result[k] = v
    return result


class Register(object):
    def __init__(self):
        self.booked = 0
        self.idle = 0
        self.nonidle_util_sum = 0.0
        self.next = collections.defaultdict(lambda: Register()) # chained

    def add(self, step_seconds, idleness_threshold, actual_util):
        self.booked += step_seconds

        if actual_util <= idleness_threshold:
            self.idle += step_seconds
        else:
            self.nonidle_util_sum += actual_util * step_seconds

    def export(self):
        nonidle_time = self.booked - self.idle

        nonidle_util = 0.0
        if nonidle_time != 0:
            nonidle_util = self.nonidle_util_sum / nonidle_time
        assigned_util = 0.0
        if self.booked != 0:
            assigned_util = self.nonidle_util_sum / self.booked

        next_items = {}
        for key, reg in self.next.items():
            next_items[key] = reg.export()

        return {
            "booked": self.booked,
            "idle": self.idle,
            "nonidle_util": nonidle_util,
            "assigned_util": assigned_util,
            "next": next_items,
        }


class IdlenessCalculator(object):
    def __init__(self, step_seconds, idleness_threshold, now):
        self.step_seconds = step_seconds
        self.idleness_threshold = idleness_threshold
        self.now = now

        self.seven_day_ago = int(
            datetime.datetime.timestamp(now - datetime.timedelta(days=1)))
        self.fourteen_days_ago = int(
            datetime.datetime.timestamp(now - datetime.timedelta(days=14)))
        self.one_month_ago = int(
            datetime.datetime.timestamp(now - datetime.timedelta(days=31)))

        self.since_one_month = Register()
        self.since_fourteen_day = Register()
        self.since_seven_day = Register()

    def add_to_register(self, register, vc, user, job_id, util):
        register.add(self.step_seconds, self.idleness_threshold, util)

        vc_reg = register.next[vc]
        vc_reg.add(self.step_seconds, self.idleness_threshold, util)

        user_reg = vc_reg.next[user]
        user_reg.add(self.step_seconds, self.idleness_threshold, util)

        job_reg = user_reg.next[job_id]
        job_reg.add(self.step_seconds, self.idleness_threshold, util)

    def observe(self, vc, user, job_id, time, util):
        if time < self.one_month_ago:
            return

        self.add_to_register(self.since_one_month, vc, user, job_id, util)

        if time < self.fourteen_days_ago:
            return

        self.add_to_register(self.since_fourteen_day, vc, user, job_id, util)

        if time < self.seven_day_ago:
            return

        self.add_to_register(self.since_seven_day, vc, user, job_id, util)

    def export(self):
        return {
            "31d": self.since_one_month.export(),
            "14d": self.since_fourteen_day.export(),
            "7d": self.since_seven_day.export(),
        }


def calculate(obj, calculator):
    start = timeit.default_timer()

    metrics = walk_json_field_safe(obj, "data", "result")

    for metric in metrics:
        username = walk_json_field_safe(metric, "metric", "username")
        vc_name = walk_json_field_safe(metric, "metric", "vc_name")
        job_id = walk_json_field_safe(metric, "metric", "job_name")

        if username is None or vc_name is None or job_id is None:
            logger.warning(
                "username or vc_name or job_id is missing for metric %s",
                walk_json_field_safe(metric, "metric"))
            continue

        values = walk_json_field_safe(metric, "values")
        if values is None or len(values) == 0:
            continue

        for time, util in values:
            util = float(util)
            calculator.observe(vc_name, username, job_id, time, util)

    result = calculator.export()
    elapsed = timeit.default_timer() - start
    logger.info("calculation spent %.2fs", elapsed)
    return result


def get_monthly_idleness(prometheus_url):
    IDLENESS_THRESHOLD = 0
    STEP_MINUTE = 5
    QUERY = "task_gpu_percent"

    step_seconds = STEP_MINUTE * 60

    now = datetime.datetime.now()
    since = int(datetime.datetime.timestamp(now - datetime.timedelta(days=31)))
    end = int(datetime.datetime.timestamp(now))

    obj = query_prometheus(prometheus_url, QUERY, since, end, STEP_MINUTE)
    calculator = IdlenessCalculator(step_seconds, IDLENESS_THRESHOLD, now)
    return calculate(obj, calculator)


def refresher(prometheus_url, atomic_ref):
    while True:
        with reporter_iteration_histogram.time():
            try:
                result = get_monthly_idleness(prometheus_url)
                if result is not None:
                    atomic_ref.set(result)
            except Exception:
                logger.exception("caught exception while refreshing")
        time.sleep(5 * 60)


class CustomCollector(object):
    def __init__(self, atomic_ref):
        self.atomic_ref = atomic_ref

    def gen_gauges(self, level_name, labels):
        label_copy = copy.deepcopy(labels)

        booked = GaugeMetricFamily("%s_booked_gpu_second" % level_name,
                                   "booked gpu second per %s" % level_name,
                                   labels=label_copy)
        idle = GaugeMetricFamily("%s_idle_gpu_second" % level_name,
                                 "idle gpu second per %s" % level_name,
                                 labels=label_copy)
        nonidle_util = GaugeMetricFamily("%s_non_idle_utils" % level_name,
                                         "non idle gpu avg util %s" %
                                         level_name,
                                         labels=label_copy)
        assigned_util = GaugeMetricFamily("%s_assigned_utils" % level_name,
                                          "assigned gpu avg util %s" %
                                          level_name,
                                          labels=label_copy)

        return {
            "booked": booked,
            "idle": idle,
            "nonidle_util": nonidle_util,
            "assigned_util": assigned_util,
        }

    def add_metric(self, gauges, label_values, register):
        for gauge_key, gauge in gauges.items():
            gauge.add_metric(copy.deepcopy(label_values), register[gauge_key])

    def walk_exported_register(self, exported):
        level_names = ["vc", "user", "job_id"]
        labels = ["since"]

        cluster_gauges = self.gen_gauges("cluster", labels) # special case

        level_gauges = []
        for level_name in level_names:
            labels.append(level_name)
            if level_name == "job_id":
                level_name = "job"
            level_gauges.append(self.gen_gauges(level_name, labels))

        for since in ["31d", "14d", "7d"]:
            self.add_metric(cluster_gauges, [since], exported[since])
            self.add_leveled_metric(exported[since]["next"], level_gauges, 0,
                                    [since])

        result = []
        result.extend(cluster_gauges.values())
        for gauges in level_gauges:
            result.extend(gauges.values())
        return result

    def add_leveled_metric(self, exported, gauges, gauge_index, label_values):
        for key, register in exported.items():
            label_values.append(key)
            self.add_metric(gauges[gauge_index], label_values, register)

            self.add_leveled_metric(register["next"], gauges, gauge_index + 1,
                                    label_values)

            label_values.pop()

    def collect(self):
        exported = self.atomic_ref.get()
        if exported is None:
            return []

        return self.walk_exported_register(exported)


def serve(prometheus_url, port):
    app = Flask(__name__)
    CORS(app)

    atomic_ref = AtomicRef()

    t = threading.Thread(target=refresher,
                         name="refresher",
                         args=(prometheus_url, atomic_ref),
                         daemon=True)
    t.start()

    REGISTRY.register(CustomCollector(atomic_ref))

    @app.route("/gpu_idle", methods=["GET"])
    def get_gpu_idleness():
        vc_name = request.args.get("vc")
        user_name = request.args.get("user")
        if vc_name is None:
            return Response("should provide vc parameter", 400)

        since = "31d"

        if user_name is None:
            result = atomic_ref.get()
            vc_result = walk_json_field_safe(result, "31d", "next", vc_name,
                                             "next") or {}
            result = {}
            for username, user_val in vc_result.items():
                result[username] = copy_without_next(user_val)

            return flask.jsonify(result)
        else:
            result = atomic_ref.get()
            user_result = walk_json_field_safe(result, "31d", "next", vc_name,
                                               "next", user_name, "next") or {}
            result = {}
            for job_id, job_val in user_result.items():
                result[job_id] = copy_without_next(job_val)

            return flask.jsonify(result)

    @app.route("/metrics")
    def metrics():
        return Response(prometheus_client.generate_latest(),
                        mimetype="text/plain; version=0.0.4; charset=utf-8")

    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


def register_stack_trace_dump():
    faulthandler.register(signal.SIGTRAP, all_threads=True, chain=False)


def main(args):
    register_stack_trace_dump()
    serve(args.prometheus_url, args.port)


if __name__ == "__main__":
    logging.basicConfig(
        format=
        "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s - %(message)s",
        level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--prometheus_url",
                        "-p",
                        required=True,
                        help="Prometheus url, eg: http://127.0.0.1:9091")

    parser.add_argument("--port", type=int, default=9092, help="port to listen")

    args = parser.parse_args()

    main(args)
