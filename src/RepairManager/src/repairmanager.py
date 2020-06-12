#!/usr/bin/env python3

import logging
import requests
import threading
import time
import urllib.parse

from flask import Flask, Response, request
from flask_cors import CORS
from requests.exceptions import ConnectionError
from util import AtomicRef, State, K8sUtil, RestUtil, parse_for_nodes

logger = logging.getLogger(__name__)


class RepairManager(object):
    def __init__(self, rules, agent_port, k8s_util, rest_util, dry_run=False):
        self.rules = rules
        self.agent_port = agent_port
        self.dry_run = dry_run

        self.k8s_util = k8s_util
        self.rest_util = rest_util

        self.nodes = []

    def get_repair_state(self):
        try:
            k8s_nodes = self.k8s_util.list_node()
            k8s_pods = self.k8s_util.list_pods()
            vc_list = self.rest_util.list_vcs().get("result", {})
            self.nodes = parse_for_nodes(k8s_nodes, k8s_pods, vc_list)
            [rule.update_metric_data() for rule in self.rules]
        except:
            logger.exception("failed to get repair state")
            self.nodes = []

    def run(self):
        self.get_repair_state()
        for node in self.nodes:
            self.update_one_node(node)

    def update_one_node(self, node):
        try:
            if node.state == State.IN_SERVICE:
                if self.check_health(node) is False:
                    self.change_unhealthy_rules(node)
                    self.cordon(node)
                    self.change_repair_state(node, State.OUT_OF_POOL)
            elif node.state == State.OUT_OF_POOL:
                if self.prepare(node):
                    self.change_repair_state(node, State.READY_FOR_REPAIR)
            elif node.state == State.READY_FOR_REPAIR:
                if self.send_repair_request(node):
                    self.change_repair_state(node, State.IN_REPAIR)
            elif node.state == State.IN_REPAIR:
                if self.check_liveness(node):
                    self.change_repair_state(node, State.AFTER_REPAIR)
            elif node.state == State.AFTER_REPAIR:
                if self.check_health(node, stat="current"):
                    self.change_unhealthy_rules(node)
                    self.uncordon(node)
                    self.change_repair_state(node, State.IN_SERVICE)
                else:
                    self.change_unhealthy_rules(node)
                    self.change_repair_state(node, State.OUT_OF_POOL)
            else:
                logger.error("Node % has unrecognized state: %s", node.name,
                             node.state)
        except:
            logger.exception("Exception in step for node %s", node.name)

    def cordon(self, node):
        return self.k8s_util.cordon(node.name)

    def uncordon(self, node):
        return self.k8s_util.uncordon(node.name)

    def change_repair_state(self, node, target_state):
        return self.k8s_util.label(node.name, "REPAIR_STATE", target_state.name)

    def change_unhealthy_rules(self, node):
        if not isinstance(node.unhealthy_rules, list) or len(node.unhealthy_rules) == 0:
            value = None
        else:
            value = ",".join([rule.__class__.__name__
                              for rule in node.unhealthy_rules])
        return self.k8s_util.annotate(
            node.name, "REPAIR_UNHEALTHY_RULES", value)

    def check_health(self, node, stat="interval"):
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
            return False
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
            return False
        except:
            logger.exception("failed to send liveness request: %s", url)
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

    while True:
        try:
            resp = requests.get(liveness_url)
            if resp.status_code == 200:
                break
        except:
            pass

    resp = requests.get(liveness_url)
    logger.info("agent liveness: %s", resp.status_code == 200)

    resp = requests.post(repair_url, json=["K8sGpuRule", "DcgmEccDBERule"])
    logger.info("agent repair: %s", resp.status_code == 200)

    while True:
        try:
            resp = requests.get(liveness_url)
            logger.info("agent liveness: %s", resp.status_code == 200)
            if resp.status_code == 200:
                break
            time.sleep(1)
        except:
            pass
