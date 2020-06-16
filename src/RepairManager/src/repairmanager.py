#!/usr/bin/env python3

import datetime
import logging
import requests
import threading
import time
import urllib.parse

from flask import Flask, Response, request
from flask_cors import CORS
from requests.exceptions import ConnectionError
from constant import REPAIR_STATE, \
    REPAIR_STATE_LAST_UPDATE_TIME, \
    REPAIR_UNHEALTHY_RULES
from util import AtomicRef, State, parse_for_nodes

logger = logging.getLogger(__name__)


class RepairManager(object):
    def __init__(self, rules, config, agent_port, k8s_util, rest_util, interval=30,
                 dry_run=False):
        self.rules = rules
        self.config = config
        self.agent_port = agent_port
        self.dry_run = dry_run

        self.k8s_util = k8s_util
        self.rest_util = rest_util
        self.interval = interval

        self.nodes = []

    def get_repair_state(self):
        try:
            k8s_nodes = self.k8s_util.list_node()
            k8s_pods = self.k8s_util.list_pods()
            vc_list = self.rest_util.list_vcs().get("result", {})
            self.nodes = parse_for_nodes(
                k8s_nodes, k8s_pods, vc_list, self.rules, self.config)
            [rule.update_data() for rule in self.rules]
        except:
            logger.exception("failed to get repair state")
            self.nodes = []

    def run(self):
        while True:
            logger.info(
                "Running repair update on nodes against rules: %s", 
                [rule.__class__.__name__ for rule in self.rules])
            try:
                self.get_repair_state()
                for node in self.nodes:
                    if self.validate(node):
                        self.update(node)
                    else:
                        logger.error("validation failed for node %s", node)
            except:
                logger.exception("failed to run")
            time.sleep(self.interval)

    def validate(self, node):
        if node.state != State.IN_SERVICE and node.unschedulable is False:
            if self.from_any_to_out_of_pool(node):
                return True
            else:
                return False
        return True

    def update(self, node):
        try:
            if node.state == State.IN_SERVICE:
                if self.check_health(node) is False:
                    self.from_in_service_to_out_of_pool(node)
            elif node.state == State.OUT_OF_POOL:
                if self.prepare(node):
                    self.from_out_of_pool_to_ready_for_repair(node)
            elif node.state == State.READY_FOR_REPAIR:
                if self.send_repair_request(node):
                    self.from_ready_for_repair_to_in_repair(node)
            elif node.state == State.IN_REPAIR:
                if self.check_liveness(node):
                    self.from_in_repair_to_after_repair(node)
            elif node.state == State.AFTER_REPAIR:
                if self.check_health(node, stat="current"):
                    self.from_after_repair_to_in_service(node)
                else:
                    self.from_after_repair_to_out_of_pool(node)
            else:
                logger.error("Node % has unrecognized state", node)
        except:
            logger.exception("Exception in step for node %s", node)

    def check_health(self, node, stat=None):
        unhealthy_rules = []
        for rule in self.rules:
            if not rule.check_health(node, stat):
                unhealthy_rules.append(rule)
        node.unhealthy_rules = unhealthy_rules
        return len(unhealthy_rules) == 0

    def prepare(self, node):
        for rule in node.unhealthy_rules:
            if not rule.prepare(node):
                return False
        return True

    def send_repair_request(self, node):
        url = urllib.parse.urljoin(
            "http://%s:%s" % (node.ip, self.agent_port), "/repair")

        if not isinstance(node.unhealthy_rules, list) or \
                len(node.unhealthy_rules) == 0:
            logger.info("nothing in unhealthy_rules for %s", url)
            return True

        repair_rules = [
            rule.__class__.__name__ for rule in node.unhealthy_rules]
        try:
            resp = requests.post(url, json=repair_rules)
            return resp.status_code == 200
        except ConnectionError:
            logger.error(
                "connection error when sending repair request: %s, %s", url,
                repair_rules)
        except:
            logger.exception(
                "failed to send repair request: %s. %s", url, repair_rules)
        return False

    def check_liveness(self, node):
        url = urllib.parse.urljoin(
            "http://%s:%s" % (node.ip, self.agent_port), "/liveness")
        try:
            resp = requests.get(url)
            return resp.status_code == 200
        except ConnectionError:
            logger.error(
                "connection error when sending liveness request: %s", url)
        except:
            logger.exception("failed to send liveness request: %s", url)
        return False

    def get_unhealthy_rules_value(self, node):
        if not isinstance(node.unhealthy_rules, list) or \
                len(node.unhealthy_rules) == 0:
            value = None
        else:
            value = ",".join([rule.__class__.__name__
                              for rule in node.unhealthy_rules])
        return value

    def patch(self, node, unschedulable=None, labels=None, annotations=None):
        if self.dry_run:
            logger.info(
                "node %s (%s) dry run. current state: %s, current "
                "unschedulable: %s, target unschedulable: %s, target "
                "labels: %s, target annotations: %s", node.name, node.ip, 
                node.state.name, node.unschedulable, unschedulable, labels, 
                annotations)
            return True

        return self.k8s_util.patch_node(
            node.name, unschedulable, labels, annotations)

    def from_any_to_out_of_pool(self, node):
        unschedulable = True
        labels = {REPAIR_STATE: State.OUT_OF_POOL.name}
        annotations = {
            REPAIR_STATE_LAST_UPDATE_TIME: str(datetime.datetime.utcnow()),
            REPAIR_UNHEALTHY_RULES: None,
        }
        if self.patch(node, unschedulable=unschedulable, labels=labels,
                      annotations=annotations):
            node.unschedulable = unschedulable
            node.state = State.OUT_OF_POOL
            return True
        else:
            return False

    def from_in_service_to_out_of_pool(self, node):
        unschedulable = True
        labels = {REPAIR_STATE: State.OUT_OF_POOL.name}
        annotations = {
            REPAIR_STATE_LAST_UPDATE_TIME: str(datetime.datetime.utcnow()),
            REPAIR_UNHEALTHY_RULES: self.get_unhealthy_rules_value(node),
        }
        if self.patch(node, unschedulable=unschedulable, labels=labels,
                      annotations=annotations):
            node.unschedulable = unschedulable
            node.state = State.OUT_OF_POOL
            return True
        else:
            return False

    def from_out_of_pool_to_ready_for_repair(self, node):
        labels = {REPAIR_STATE: State.READY_FOR_REPAIR.name}
        annotations = {
            REPAIR_STATE_LAST_UPDATE_TIME: str(datetime.datetime.utcnow()),
        }
        if self.patch(node, labels=labels, annotations=annotations):
            node.state = State.READY_FOR_REPAIR
            return True
        else:
            return False

    def from_ready_for_repair_to_in_repair(self, node):
        labels = {REPAIR_STATE: State.IN_REPAIR.name}
        annotations = {
            REPAIR_STATE_LAST_UPDATE_TIME: str(datetime.datetime.utcnow()),
        }
        if self.patch(node, labels=labels, annotations=annotations):
            node.state = State.IN_REPAIR
            return True
        else:
            return False

    def from_in_repair_to_after_repair(self, node):
        labels = {REPAIR_STATE: State.AFTER_REPAIR.name}
        annotations = {
            REPAIR_STATE_LAST_UPDATE_TIME: str(datetime.datetime.utcnow()),
        }
        if self.patch(node, labels=labels, annotations=annotations):
            node.state = State.AFTER_REPAIR
            return True
        else:
            return False

    def from_after_repair_to_in_service(self, node):
        unschedulable = False
        labels = {REPAIR_STATE: State.IN_SERVICE.name}
        annotations = {
            REPAIR_STATE_LAST_UPDATE_TIME: str(datetime.datetime.utcnow()),
            REPAIR_UNHEALTHY_RULES: None,
        }
        if self.patch(node, unschedulable=unschedulable, labels=labels,
                      annotations=annotations):
            node.unschedulable = unschedulable
            node.state = State.IN_SERVICE
            return True
        else:
            return False

    def from_after_repair_to_out_of_pool(self, node):
        labels = {REPAIR_STATE: State.OUT_OF_POOL.name}
        annotations = {
            REPAIR_STATE_LAST_UPDATE_TIME: str(datetime.datetime.utcnow()),
            REPAIR_UNHEALTHY_RULES: self.get_unhealthy_rules_value(node),
        }
        if self.patch(node, labels=labels, annotations=annotations):
            node.state = State.OUT_OF_POOL
            return True
        else:
            return False


class RepairManagerAgent(object):
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
            if self.repair_rules.get() is not None:
                return Response(status=503)
            return Response(status=200)

        app.run(host="0.0.0.0", port=self.port, debug=False, use_reloader=False)

    def handle(self):
        rules_mapping = {
            rule.__class__.__name__: rule for rule in self.rules
        }

        while True:
            repair_rules = self.repair_rules.get()
            if repair_rules is not None:
                logger.info("handle rule repair: %s", repair_rules)
                try:
                    for rule_name in repair_rules:
                        rule = rules_mapping.get(rule_name)
                        if rule is None:
                            logger.warning(
                                "skip rule with no definition: %s", rule_name)
                            continue
                        if not self.dry_run:
                            rule.repair()
                        else:
                            logger.info("dry run rule repair: %s", rule_name)
                except:
                    logger.exception("failed to handle rule repair: %s",
                                     repair_rules)
                self.repair_rules.set(None)
            time.sleep(3)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(threadName)s - %(filename)s:%(lineno)s - %(message)s",
        level="INFO")

    # Local test on repairmanager agent
    from rule import K8sGpuRule, DcgmEccDBERule

    agent = RepairManagerAgent(
        [K8sGpuRule(), DcgmEccDBERule()], 9180, dry_run=True)
    t = threading.Thread(target=agent.run, name="agent_runner", daemon=True)
    t.start()

    liveness_url = urllib.parse.urljoin("http://localhost:9180", "/liveness")
    repair_url = urllib.parse.urljoin("http://localhost:9180", "/repair")

    def wait_for_alive():
        while True:
            try:
                resp = requests.get(liveness_url)
                logger.info("agent liveness: %s", resp.status_code == 200)
                if resp.status_code == 200:
                    break
            except:
                pass

    wait_for_alive()
    resp = requests.get(liveness_url)
    logger.info("agent liveness: %s", resp.status_code == 200)

    resp = requests.post(repair_url, json=["K8sGpuRule", "DcgmEccDBERule"])
    logger.info("agent repair: %s", resp.status_code == 200)

    wait_for_alive()
