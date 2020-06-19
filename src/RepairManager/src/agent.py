#!/usr/bin/env python3

import argparse
import logging
import os
import threading
import time

from logging import handlers
from flask import Flask, Response, request
from flask_cors import CORS
from util import AtomicRef, get_logging_level, register_stack_trace_dump
from rule import instantiate_rules

logger = logging.getLogger(__name__)


class Agent(object):
    """Agent listens on incoming repair signal and executes repair.
    """
    def __init__(self, rules, port, dry_run=False):
        self.rules = rules
        self.port = port
        self.dry_run = dry_run
        self.repair_rules = AtomicRef()
        self.repair_handler = threading.Thread(
            target=self.handle, name="repair_handler", daemon=True)

    def run(self):
        self.repair_handler.start()
        self.serve()

    def serve(self):
        app = Flask(self.__class__.__name__)
        CORS(app)

        @app.route("/repair", methods=["POST"])
        def repair():
            req_data = request.get_json()
            if not isinstance(req_data, list):
                return Response(status=400)
            if not self.repair_rules.set_if_none(req_data):
                return Response(status=503)
            return Response(status=200)

        @app.route("/liveness")
        def metrics():
            # Agent is not alive if there is a repair going on.
            if self.repair_rules.get() is not None:
                return Response(status=503)
            return Response(status=200)

        app.run(host="0.0.0.0", port=self.port, debug=False, use_reloader=False)

    def handle(self):
        rules_mapping = {rule.name: rule for rule in self.rules}

        while True:
            repair_rules = self.repair_rules.get()
            # Execute repair rules is there is a repair request
            if repair_rules is not None:
                logger.info("handle rule repair: %s", repair_rules)
                try:
                    is_repaired = True
                    for rule_name in repair_rules:
                        rule = rules_mapping.get(rule_name)
                        if rule is None:
                            logger.warning(
                                "skip rule with no definition: %s", rule_name)
                            continue
                        if not self.dry_run:
                            logger.info("rule repair: %s", rule_name)
                            if rule.repair() is False:
                                is_repaired = False
                                break
                        else:
                            logger.info("DRY RUN rule repair: %s", rule_name)
                            is_repaired = False
                    # Only when the repair succeeds can the rules be cleared
                    if is_repaired:
                        self.repair_rules.set(None)
                except:
                    logger.exception(
                        "failed to handle rule repair: %s", repair_rules)
            time.sleep(3)


def main(params):
    register_stack_trace_dump()

    logger.info("Starting agent ...")
    try:
        rules = instantiate_rules()
        agent = Agent(rules, int(params.agent_port), dry_run=params.dry_run)
        agent.run()
    except:
        logger.exception("Exception in agent run")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--log",
                        "-l",
                        help="log dir to store log",
                        default="/var/log/repairmanager")
    parser.add_argument("--agent_port",
                        "-a",
                        help="port for agent",
                        default=9081)
    parser.add_argument("--dry_run",
                        "-d",
                        action="store_true",
                        help="dry run flag")
    args = parser.parse_args()

    console_handler = logging.StreamHandler()
    file_handler = handlers.RotatingFileHandler(
        os.path.join(args.log, "agent.log"),
        maxBytes=10240000, backupCount=10)
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(threadName)s - %(filename)s:%(lineno)s - %(message)s",
        level=get_logging_level(),
        handlers=[console_handler, file_handler])

    main(args)
