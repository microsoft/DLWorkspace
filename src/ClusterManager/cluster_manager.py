#!/usr/bin/env python3

import yaml
import os
import logging
import logging.config
import sys
import time
import datetime
import argparse
import threading
import traceback
import signal
import timeit
import functools
import subprocess
import faulthandler

from prometheus_client.twisted import MetricsResource
from prometheus_client.core import REGISTRY
from prometheus_client import Histogram

from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.internet import reactor

logger = logging.getLogger(__name__)

manager_iteration_histogram = Histogram("manager_iteration_latency_seconds",
                                        "latency for manager to iterate",
                                        buckets=(2.5, 5.0, 10.0, 20.0, 40.0,
                                                 80.0, 160.0, float("inf")),
                                        labelnames=("name",))

fn_histogram = Histogram("manager_fn_latency_seconds",
                         "latency for executing *manager's function (seconds)",
                         buckets=(1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0,
                                  256.0, 512.0, 1024.0, float("inf")),
                         labelnames=("file_name", "fn_name"))


def record(fn):
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        start = timeit.default_timer()
        try:
            return fn(*args, **kwargs)
        finally:
            elapsed = timeit.default_timer() - start
            fn_histogram.labels(os.path.basename(sys.argv[0]),
                                fn.__name__).observe(elapsed)

    return wrapped


class HealthResource(Resource):
    def render_GET(self, request):
        request.setHeader("Content-Type", "text/html; charset=utf-8")
        return "<html>Ok</html>".encode("utf-8")


class AtomicRef(object):
    """ a thread safe way to store and get object,
    should not modify data get from this ref,
    each get and set method should provide a time obj,
    so this ref decide whether the data is out of date or not,
    return None on expired """
    def __init__(self, decay_time):
        self.data = None
        self.date_in_produced = datetime.datetime.now()
        self.decay_time = decay_time
        self.lock = threading.RLock()

    def set(self, data, now):
        with self.lock:
            self.data, self.date_in_produced = data, now

    def get(self, now):
        with self.lock:
            if self.decay_time.seconds != 0 and \
                    self.date_in_produced + self.decay_time < now:
                return None
            return self.data


class CustomCollector(object):
    def __init__(self, atomic_refs):
        self.atomic_refs = atomic_refs

    def collect(self):
        data = []

        now = datetime.datetime.now()

        for ref in self.atomic_refs:
            d = ref.get(now)
            if d is not None:
                data.extend(d)

        if len(data) > 0:
            for datum in data:
                yield datum
        else:
            # https://stackoverflow.com/a/6266586
            # yield nothing
            return
            yield


def exporter_thread(port, refs):
    try:
        if refs is not None:
            REGISTRY.register(CustomCollector(refs))

        root = Resource()
        root.putChild(b"metrics", MetricsResource())
        root.putChild(b"healthz", HealthResource())

        factory = Site(root)
        reactor.listenTCP(port, factory)
        reactor.run(installSignalHandlers=False)
    except Exception:
        logger.exception("exporter thread failed")


def setup_exporter_thread(port, refs=None):
    t = threading.Thread(target=exporter_thread,
                         args=(port, refs),
                         name="exporter")
    t.daemon = True
    t.start()
    return t


def create_log(logdir="/var/log/dlworkspace"):
    if not os.path.exists(logdir):
        os.system("mkdir -p " + logdir)
    with open("logging.yaml") as f:
        logging_config = yaml.full_load(f)
    logging_config["handlers"]["file"]["filename"] = logdir + \
        "/clustermanager.log"
    logging.config.dictConfig(logging_config)


def register_stack_trace_dump():
    faulthandler.register(signal.SIGTRAP, all_threads=True, chain=False)


def update_file_modification_time(path):
    if not os.path.isfile(path):
        f = open(path, "w")
        f.close()

    mod_time = time.mktime(datetime.datetime.now().timetuple())
    os.utime(path, (mod_time, mod_time))


def get_elapsed_seconds(path):
    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(path))
    return (datetime.datetime.now() - mtime).seconds


def run(args):
    register_stack_trace_dump()
    create_log()

    cwd = os.path.dirname(__file__)
    cmds = {
        "job_manager_killing,pausing,unapproved": [
            "python3",
            os.path.join(cwd, "job_manager.py"), "--port",
            str(args.j1), "--status", "killing,pausing,unapproved"
        ],
        "job_manager_running": [
            "python3",
            os.path.join(cwd, "job_manager.py"), "--port",
            str(args.j2), "--status", "running"
        ],
        "job_manager_scheduling": [
            "python3",
            os.path.join(cwd, "job_manager.py"), "--port",
            str(args.j3), "--status", "scheduling"
        ],
        "job_manager_queued": [
            "python3",
            os.path.join(cwd, "job_manager.py"), "--port",
            str(args.j4), "--status", "queued"
        ],
        "user_manager": [
            "python3",
            os.path.join(cwd, "user_manager.py"), "--port",
            str(args.u)
        ],
        "node_manager": [
            "python3",
            os.path.join(cwd, "node_manager.py"), "--port",
            str(args.n)
        ],
        "joblog_manager": [
            "python3",
            os.path.join(cwd, "joblog_manager.py"), "--port",
            str(args.l)
        ],
        "endpoint_manager": [
            "python3",
            os.path.join(cwd, "endpoint_manager.py"), "--port",
            str(args.e)
        ],
        "db_manager": [
            "python3",
            os.path.join(cwd, "db_manager.py"), "--port",
            str(args.d)
        ],
    }

    FNULL = open(os.devnull, "w")

    childs = {}

    while True:
        try:
            work(cmds, childs, FNULL)
        except Exception as e:
            logger.exception("caught exception while doing work")
        time.sleep(60)


def work(cmds, childs, FNULL):
    for key, cmd in list(cmds.items()):
        sys.stdout.flush()
        sys.stderr.flush()

        child = childs.get(key)
        need_start = False

        if child is None or child.poll() is not None:
            if child is not None:
                logger.info("%s is dead restart it", cmd)
            need_start = True
        else:
            sec = get_elapsed_seconds(key)
            if sec <= args.tictoc:
                continue
            logger.info("%s did not update file for %d seconds, restart it",
                        key, sec)
            child.send_signal(signal.SIGTRAP) # try to print their stacktrace
            time.sleep(1)
            child.kill()
            need_start = True

        if need_start:
            update_file_modification_time(key)
            try:
                childs[key] = subprocess.Popen(cmd, stdin=FNULL)
            except Exception as e:
                logger.exception(
                    "caught exception when trying to start %s, ignore", cmd)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tictoc",
                        help="how many seconds to wait until kill subprocess",
                        type=int,
                        default=600)
    parser.add_argument("-j1",
                        help="port of job_manager",
                        type=int,
                        default=9200)
    parser.add_argument("-j2",
                        help="port of job_manager",
                        type=int,
                        default=9206)
    parser.add_argument("-j3",
                        help="port of job_manager",
                        type=int,
                        default=9207)
    parser.add_argument("-j4",
                        help="port of job_manager",
                        type=int,
                        default=9208)
    parser.add_argument("-u",
                        help="port of user_manager",
                        type=int,
                        default=9201)
    parser.add_argument("-n",
                        help="port of node_manager",
                        type=int,
                        default=9202)
    parser.add_argument("-l",
                        help="port of joblog_manager",
                        type=int,
                        default=9203)
    parser.add_argument("-e",
                        help="port of endpoint_manager",
                        type=int,
                        default=9205)
    parser.add_argument("-d", help="port of db_manager", type=int, default=9209)
    args = parser.parse_args()

    sys.exit(run(args))
