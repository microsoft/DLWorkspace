#!/usr/bin/env python3

import faulthandler
import os
import yaml
import signal
import logging
import threading
import prometheus_client

from flask import Flask
from flask import Response
from flask_cors import CORS
from logging.config import dictConfig

from prometheus_client.core import REGISTRY
from storage_manager import StorageManager

LOGGING_FILE = "logging.yaml"
CONFIG_FILE = "config.yaml"

dir_path = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(dir_path, LOGGING_FILE), "r") as f:
    logging_config = yaml.safe_load(f)
    dictConfig(logging_config)
logger = logging.getLogger(__name__)

with open(os.path.join(dir_path, CONFIG_FILE), "r") as f:
    config = yaml.safe_load(f)


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


class CustomCollector(object):
    def __init__(self, ref):
        self.ref = ref

    def collect(self):
        metric = self.ref.get()
        if metric is not None:
            yield metric


def storage_manager_runner(sm_config, smtp, cluster_name, atomic_ref):
    while True:
        try:
            sm = StorageManager(sm_config, smtp, cluster_name, atomic_ref)
            sm.run()
        except:
            logger.exception("storage_manager_runner failed")


def serve():
    # Get port for Prometheus scraping
    port = os.getenv("PROMETHEUS_IO_PORT")
    if port is None:
        logger.error("Environment variable PROMETHEUS_IO_PORT is missing!")
        return

    # Get config for storage manager
    sm_config = config.get("storage_manager", None)
    if sm_config is None:
        logger.warning("storage_manager is not enabled. Exiting ...")
        return

    smtp = config.get("smtp", None)
    cluster_name = config.get("cluster_name_friendly", None)

    app = Flask(__name__)
    CORS(app)

    # Start storage manager
    atomic_ref = AtomicRef()
    t1 = threading.Thread(target=storage_manager_runner,
                          name="storage_manager_runner",
                          args=(sm_config, smtp, cluster_name, atomic_ref),
                          daemon=True)
    t1.start()

    REGISTRY.register(CustomCollector(atomic_ref))

    @app.route("/metrics")
    def metrics():
        return Response(prometheus_client.generate_latest(),
                        mimetype="text/plain; version=0.0.4; charset=utf-8")

    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


def register_stack_trace_dump():
    faulthandler.register(signal.SIGTRAP, all_threads=True, chain=False)


def main():
    register_stack_trace_dump()
    serve()


if __name__ == "__main__":
    main()
