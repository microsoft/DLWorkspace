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
    labelnames=("type",),
    buckets=(.05, .075, .1, .25, .5, .75, 1.0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0,
             17.5, 20.0, float("inf")))

reporter_iteration_histogram = Histogram(
    "reporter_iteration_seconds",
    "latency for reporter to iterate one pass (seconds)",
    labelnames=("type",),
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
    prometheus_request_histogram.labels("job_idle").observe(elapsed)
    logger.info("request %s spent %.2fs", query, elapsed)

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
    def __init__(self, parent):
        self.parent = parent
        self.booked = 0
        self.idle = 0
        self.nonidle_util_sum = 0.0
        self.next = collections.defaultdict(lambda: Register(self)) # chained

    def add(self, booked, idle, nonidle_util):
        self.booked += booked
        self.idle += idle
        self.nonidle_util_sum += nonidle_util
        if self.parent is not None:
            self.parent.add(booked, idle, nonidle_util)

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


class Calculator(object):
    def observe_metric(self, metric):
        pass

    def name(self):
        return self.__class__.__name__

    def export(self):
        pass


class IdlenessCalculator(Calculator):
    def __init__(self, step_seconds, idleness_threshold, now):
        self.step_seconds = step_seconds
        self.idleness_threshold = idleness_threshold
        self.now = now

        self.seven_days_ago = int(
            datetime.datetime.timestamp(now - datetime.timedelta(days=7)))
        self.fourteen_days_ago = int(
            datetime.datetime.timestamp(now - datetime.timedelta(days=14)))
        self.one_month_ago = int(
            datetime.datetime.timestamp(now - datetime.timedelta(days=31)))

        self.since_one_month = Register(None)
        self.since_fourteen_days = Register(None)
        self.since_seven_days = Register(None)

    def calculate_increment(self, util):
        booked = self.step_seconds
        idle = 0
        nonidle_util = 0.0

        if util <= self.idleness_threshold:
            idle = self.step_seconds
        else:
            nonidle_util = util * self.step_seconds
        return booked, idle, nonidle_util

    def observe_metric(self, metric):
        username = walk_json_field_safe(metric, "metric", "username")
        vc_name = walk_json_field_safe(metric, "metric", "vc_name")
        job_id = walk_json_field_safe(metric, "metric", "job_name")
        preemptible = walk_json_field_safe(metric, "metric",
                                           "preemptible") or "false"

        if username is None or vc_name is None or job_id is None:
            logger.warning(
                "username or vc_name or job_id is missing for metric %s",
                walk_json_field_safe(metric, "metric"))
            return

        values = walk_json_field_safe(metric, "values")
        if values is None or len(values) == 0:
            return

        for time, util in values:
            util = float(util)
            self.observe(preemptible, vc_name, username, job_id, time, util)

    def observe(self, preemptible, vc, user, job_id, time, util):
        if time < self.one_month_ago:
            return

        booked, idle, nonidle_util = self.calculate_increment(util)

        # do not implment __getitem__ here. That's slow
        self.since_one_month.next[preemptible].next[vc].next[user].next[
            job_id].add(booked, idle, nonidle_util)

        if time < self.fourteen_days_ago:
            return

        self.since_fourteen_days.next[preemptible].next[vc].next[user].next[
            job_id].add(booked, idle, nonidle_util)

        if time < self.seven_days_ago:
            return

        self.since_seven_days.next[preemptible].next[vc].next[user].next[
            job_id].add(booked, idle, nonidle_util)

    def export(self):
        return {
            "31d": self.since_one_month.export(),
            "14d": self.since_fourteen_days.export(),
            "7d": self.since_seven_days.export(),
        }


class VCDataCalculator(Calculator):
    def __init__(self, now, step_seconds):
        self.step_seconds = step_seconds

        self.seven_days_ago = int(
            datetime.datetime.timestamp(now - datetime.timedelta(days=7)))
        self.fourteen_days_ago = int(
            datetime.datetime.timestamp(now - datetime.timedelta(days=14)))
        self.one_month_ago = int(
            datetime.datetime.timestamp(now - datetime.timedelta(days=31)))

        # key is (vc, gpu_type)
        self.since_seven_days = collections.defaultdict(lambda: 0)
        self.since_fourteen_days = collections.defaultdict(lambda: 0)
        self.since_one_month = collections.defaultdict(lambda: 0)

    def observe_metric(self, metric):
        vc_name = walk_json_field_safe(metric, "metric", "vc_name")
        gpu_type = walk_json_field_safe(metric, "metric", "gpu_type")

        if vc_name is None or gpu_type is None:
            logger.warning("vc_name or gpu_type is missing for metric %s",
                           walk_json_field_safe(metric, "metric"))
            return

        values = walk_json_field_safe(metric, "values")

        if values is None or len(values) == 0:
            return

        key = (vc_name, gpu_type)

        for time, val in values:
            self.observe(time, key, float(val))

    def observe(self, time, key, val):
        if time < self.one_month_ago:
            return

        inc = val * self.step_seconds

        self.since_one_month[key] += inc

        if time < self.fourteen_days_ago:
            return

        self.since_fourteen_days[key] += inc

        if time < self.seven_days_ago:
            return

        self.since_seven_days[key] += inc

    def export(self):
        return {
            "31d": self.since_one_month,
            "14d": self.since_fourteen_days,
            "7d": self.since_seven_days,
        }


def calculate(obj, calculator):
    start = timeit.default_timer()

    metrics = walk_json_field_safe(obj, "data", "result")

    for metric in metrics:
        calculator.observe_metric(metric)

    result = calculator.export()
    elapsed = timeit.default_timer() - start
    logger.info("%s spent %.2fs", calculator.name(), elapsed)
    return result


class Exportable(object):
    """ object exchanged in AtomicRef, have a to_metrics method to generate Metrics
    for Collector to consume """
    def to_metrics(self):
        pass


class IdlenessExportable(Exportable):
    def __init__(self, raw):
        self.raw = raw

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

    def add_leveled_metric(self, exported, gauges, gauge_index, label_values):
        for key, register in exported.items():
            label_values.append(key)
            self.add_metric(gauges[gauge_index], label_values, register)

            self.add_leveled_metric(register["next"], gauges, gauge_index + 1,
                                    label_values)

            label_values.pop()

    def to_metrics(self):
        level_names = ["vc", "user", "job_id"]
        labels = ["since", "preemptible"]

        cluster_gauges = self.gen_gauges("cluster", labels) # special case

        level_gauges = []
        for level_name in level_names:
            labels.append(level_name)
            if level_name == "job_id":
                level_name = "job"
            level_gauges.append(self.gen_gauges(level_name, labels))

        for since in ["31d", "14d", "7d"]:
            for preemptible in ["true", "false"]:
                start_reg = walk_json_field_safe(self.raw, since, "next",
                                                 preemptible)
                if start_reg is None:
                    continue
                self.add_metric(cluster_gauges, [since, preemptible], start_reg)
                self.add_leveled_metric(start_reg["next"], level_gauges, 0,
                                        [since, preemptible])

        result = []
        result.extend(cluster_gauges.values())
        for gauges in level_gauges:
            result.extend(gauges.values())
        return result


class VCDataExportable(Exportable):
    def __init__(self, raw):
        self.raw = raw

    def to_metrics(self):
        total_gauge = GaugeMetricFamily(
            "vc_allocated_gpu_second",
            "GPU quota allocated to VC since past date",
            labels=["since", "vc", "gpu_type"])
        unschedulable_gauge = GaugeMetricFamily(
            "vc_unschedulable_gpu_second",
            "GPU unschedulable to VC since past date",
            labels=["since", "vc", "gpu_type"])

        for since in ["31d", "14d", "7d"]:
            for (vc, gpu_type), val in self.raw["total"][since].items():
                total_gauge.add_metric([since, vc, gpu_type], val)

            for (vc, gpu_type), val in self.raw["unschedulable"][since].items():
                unschedulable_gauge.add_metric([since, vc, gpu_type], val)

        return [total_gauge, unschedulable_gauge]


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


def get_monthly_vc_data(prometheus_url, query, step_minute):
    step_seconds = step_minute * 60

    now = datetime.datetime.now()
    since = int(datetime.datetime.timestamp(now - datetime.timedelta(days=31)))
    end = int(datetime.datetime.timestamp(now))

    obj = query_prometheus(prometheus_url, query, since, end, step_minute)
    calculator = VCDataCalculator(now, step_seconds)
    return calculate(obj, calculator)


def job_idleness_refresher(prometheus_url, atomic_ref):
    while True:
        with reporter_iteration_histogram.labels("job_idle").time():
            try:
                result = get_monthly_idleness(prometheus_url)
                if result is not None:
                    atomic_ref.set(IdlenessExportable(result))
            except Exception:
                logger.exception("caught exception while refreshing job idle")
        time.sleep(5 * 60)


def vc_quota_refresher(prometheus_url, atomic_ref):
    STEP_MINUTE = 5

    while True:
        with reporter_iteration_histogram.labels("vc_quota").time():
            try:
                total = get_monthly_vc_data(prometheus_url, "k8s_vc_gpu_total",
                                            STEP_MINUTE)
                unschedulable = get_monthly_vc_data(prometheus_url,
                                                    "k8s_vc_gpu_unschedulable",
                                                    STEP_MINUTE)
                atomic_ref.set(
                    VCDataExportable({
                        "total": total,
                        "unschedulable": unschedulable
                    }))
            except Exception:
                logger.exception("caught exception while refreshing vc quota")
        time.sleep(60) # this loop latency is usually 0.02s


class CustomCollector(object):
    def __init__(self, refs):
        self.refs = refs

    def collect(self):
        for ref in self.refs:
            exportable = ref.get()
            if exportable is not None:
                for m in exportable.to_metrics():
                    yield m


def serve(prometheus_url, port):
    app = Flask(__name__)
    CORS(app)

    atomic_ref1 = AtomicRef()
    t1 = threading.Thread(target=job_idleness_refresher,
                          name="job_idleness_refresher",
                          args=(prometheus_url, atomic_ref1),
                          daemon=True)
    t1.start()

    atomic_ref2 = AtomicRef()
    t2 = threading.Thread(target=vc_quota_refresher,
                          name="vc_quota_refresher",
                          args=(prometheus_url, atomic_ref2),
                          daemon=True)
    t2.start()

    REGISTRY.register(CustomCollector([atomic_ref1, atomic_ref2]))

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
