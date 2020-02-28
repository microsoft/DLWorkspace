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

import requests

import flask
from flask import Flask
from flask import request
from flask import Response
from flask_cors import CORS

import prometheus_client
from prometheus_client import Histogram

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


def get_monthly_idleness(prometheus_url):
    IDLENESS_THRESHOLD = 0
    STEP_MINUTE = 5

    step_seconds = STEP_MINUTE * 60

    now = datetime.datetime.now()
    delta = datetime.timedelta(days=31)
    one_month_ago = int(datetime.datetime.timestamp(now - delta))
    now = int(datetime.datetime.timestamp(now))

    args = urllib.parse.urlencode({
        "query": "task_gpu_percent",
        "start": str(one_month_ago),
        "end": str(now),
        "step": str(STEP_MINUTE) + "m",
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

    metrics = walk_json_field_safe(obj, "data", "result")

    default = lambda: {"booked": 0, "idle": 0, "nonidle_util_sum": 0.0}

    # the first level is vc, the second level is user
    vc_level = collections.defaultdict(
        lambda: collections.defaultdict(default))

    # the first level is vc, the second level is user, the third level is job
    user_level = collections.defaultdict(lambda: collections.defaultdict(
        lambda: collections.defaultdict(default)))

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

        booked_seconds = values[-1][0] - values[0][0] + step_seconds
        idleness_seconds = 0
        nonidle_util_sum = 0.0

        for time, utils in values:
            utils = float(utils)
            if utils <= IDLENESS_THRESHOLD:
                idleness_seconds += step_seconds
            else:
                nonidle_util_sum += utils * step_seconds

        vc_level[vc_name][username]["booked"] += booked_seconds
        vc_level[vc_name][username]["idle"] += idleness_seconds
        vc_level[vc_name][username]["nonidle_util_sum"] += nonidle_util_sum

        user_level[vc_name][username][job_id]["booked"] += booked_seconds
        user_level[vc_name][username][job_id]["idle"] += idleness_seconds
        user_level[vc_name][username][job_id][
            "nonidle_util_sum"] += nonidle_util_sum

    for vc_name, vc_values in vc_level.items():
        for username, user_val in vc_values.items():
            nonidle_time = user_val["booked"] - user_val["idle"]
            nonidle_util_sum = user_val["nonidle_util_sum"]

            if nonidle_time == 0:
                user_val["nonidle_util"] = 0.0
            else:
                user_val["nonidle_util"] = nonidle_util_sum / nonidle_time
            user_val.pop("nonidle_util_sum")

    for vc_name, vc_values in user_level.items():
        for username, user_values in vc_values.items():
            for job_id, job_val in user_values.items():
                nonidle_time = job_val["booked"] - job_val["idle"]
                nonidle_util_sum = job_val["nonidle_util_sum"]

                if nonidle_time == 0:
                    job_val["nonidle_util"] = 0.0
                else:
                    job_val["nonidle_util"] = nonidle_util_sum / nonidle_time
                job_val.pop("nonidle_util_sum")

    return {"vc_level": vc_level, "user_level": user_level}


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


def serve(prometheus_url, port):
    app = Flask(__name__)
    CORS(app)

    atomic_ref = AtomicRef()

    t = threading.Thread(target=refresher,
                         name="refresher",
                         args=(prometheus_url, atomic_ref),
                         daemon=True)
    t.start()

    @app.route("/gpu_idle", methods=["GET"])
    def get_gpu_idleness():
        vc_name = request.args.get("vc")
        user_name = request.args.get("user")
        if vc_name is None:
            return Response("should provide vc parameter", 400)

        if user_name is None:
            result = atomic_ref.get()
            vc_level = result["vc_level"]
            if result is None or vc_level.get(vc_name) is None:
                return flask.jsonify({})

            return flask.jsonify(vc_level[vc_name])
        else:
            result = atomic_ref.get()
            user_level = result["user_level"]
            if result is None or user_level.get(vc_name) is None or user_level[
                    vc_name].get(user_name) is None:
                return flask.jsonify({})

            return flask.jsonify(user_level[vc_name][user_name])

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

    parser.add_argument("--port",
                        type=int,
                        default=9092,
                        help="port to listen")

    args = parser.parse_args()

    main(args)
