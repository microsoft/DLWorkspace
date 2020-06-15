#!/usr/bin/env python3

import argparse
import faulthandler
import logging
import os
import signal
import sys
import yaml

from logging import handlers
from repairmanager import RepairManager, RepairManagerAgent
from rule import Rule, instantiate_rules
from util import K8sUtil, RestUtil


logger = logging.getLogger(__name__)


def get_config(config_path):
    with open(os.path.join(config_path, "config.yaml"), "r") as f:
        config = yaml.safe_load(f)
    return config


def start_repairmanager(params):
    try:
        config = get_config(params.config)
        rules = instantiate_rules(config.get("rules", []))
        k8s_util = K8sUtil()
        rest_util = RestUtil()
        repair_manager = RepairManager(
            rules, int(params.port), k8s_util, rest_util,
            interval=params.interval, dry_run=params.dry_run)
        repair_manager.run()
    except:
        logger.exception("Exception in repairmanager run")


def start_repairmanager_agent(params):
    try:
        # Instantiate all available rule definitions for agent
        rules = instantiate_rules(list(Rule.subclasses.keys()))
        agent = RepairManagerAgent(
            rules, int(params.port), dry_run=params.dry_run)
        agent.run()
    except:
        logger.exception("Exception in repairmanager agent run")


def register_stack_trace_dump():
    faulthandler.register(signal.SIGTRAP, all_threads=True, chain=False)


def main(params):
    register_stack_trace_dump()

    if params.service == "repairmanager":
        start_repairmanager(params)
    elif params.service == "repairmanageragent":
        start_repairmanager_agent(params)
    else:
        logger.fatal("Unrecognized service %s", params.service)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--service",
                        "-s",
                        help="repairmanager or repairmanageragent",
                        default="repairmanager")
    parser.add_argument("--config",
                        "-c",
                        help="directory path containing config.yaml",
                        default="/etc/repairmanager")
    parser.add_argument("--log",
                        "-l",
                        help="log dir to store log",
                        default="/var/log/repairmanager")
    parser.add_argument("--interval",
                        "-i",
                        help="sleep time between repairmanager runs",
                        default=30,
                        type=int)
    parser.add_argument("--port",
                        "-p",
                        help="port for repairmanager",
                        default="9080")
    parser.add_argument("--agent_port",
                        "-a",
                        help="port for repairmanager agent",
                        default="9081")
    parser.add_argument("--dry_run",
                        "-d",
                        action="store_true",
                        help="dry run flag")
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

    console_handler = logging.StreamHandler(sys.stdout)
    file_handler = handlers.RotatingFileHandler(
        os.path.join(args.log, args.service, ".log"),
        maxBytes=10240000, backupCount=10)
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(threadName)s - %(filename)s:%(lineno)s - %(message)s",
        level=get_logging_level(),
        handlers=[console_handler, file_handler])

    main(args)
