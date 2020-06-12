#!/usr/bin/env python3

import argparse
import faulthandler
import logging
import os
import signal
import sys
import time

from repairmanager import RepairManager, RepairManagerAgent


logger = logging.getLogger(__name__)


def start_repairmanager(params):
    try:
        interval = int(params.interval)
        rules = [

        ]
        repair_manager = RepairManager(rules)
        while True:
            repair_manager.step()
            time.sleep(interval)
    except:
        logger.exception("Exception in repairmanager step")


def start_repairmanager_agent(params):
    try:
        agent = RepairManagerAgent()
        agent.run()
    except:
        logger.exception("Exception in repairmanager agent run")


def register_stack_trace_dump():
    faulthandler.register(signal.SIGTRAP, all_threads=True, chain=False)


def main(params):
    register_stack_trace_dump()

    service = params.service
    if service == "repairmanager":
        start_repairmanager(params)
    elif service == "repairmanageragent":
        start_repairmanager_agent(params)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--service",
                        "-s",
                        help="repairmanager or repairmanageragent")
    parser.add_argument("--log",
                        "-l",
                        help="log dir to store log",
                        default="/var/log/repairmanager")
    parser.add_argument("--interval",
                        "-i",
                        help="interval in seconds to sleep between runs",
                        default=30)
    parser.add_argument("--port",
                        "-p",
                        help="port to expose metrics",
                        default="9102")
    args = parser.parse_args()

    def get_logging_level():
        mapping = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING
        }

        result = logging.INFO

        if os.environ.get("LOGGING_LEVEL") is not None:
            level = os.environ["LOGGING_LEVEL"]
            result = mapping.get(level.upper())
            if result is None:
                sys.stderr.write("unknown logging level " + level +
                                 ", default to INFO\n")
                result = logging.INFO

        return result

    logging.basicConfig(
        format=
        "%(asctime)s - %(levelname)s - %(threadName)s - %(filename)s:%(lineno)s - %(message)s",
        level=get_logging_level())

    main(args)
