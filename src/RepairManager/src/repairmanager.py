#!/usr/bin/env python3

import logging
import urllib.parse

from util import State, K8sUtil, RestUtil, parse_for_nodes

logger = logging.getLogger(__name__)


class RepairManager(object):
    def __init__(self, rules, dry_run=False):
        self.rules = rules
        self.dry_run = dry_run

        self.k8s_util = K8sUtil()
        self.rest_util = RestUtil()

        self.nodes = []

    def get_repair_state(self):
        k8s_nodes = self.k8s_util.list_node()
        k8s_pods = self.k8s_util.list_pods()
        vc_list = self.rest_util.list_vcs().get("result", {})["result"]
        self.nodes = parse_for_nodes(k8s_nodes, k8s_pods, vc_list)
        [rule.update_metric_data() for rule in self.rules]

    def step(self):
        self.get_repair_state()
        for node in self.nodes:
            self.step_for_one_node(node)

    def step_for_one_node(self, node):
        try:
            if node.state == State.IN_SERVICE:
                if self.check_health(node) is False:
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
                    self.uncordon(node)
                    self.change_repair_state(node, State.IN_SERVICE)
                else:
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

    def check_health(self, node, stat="interval"):
        unhealthy_rules = []
        for rule in self.rules:
            if not rule.check_health(node, stat):
                unhealthy_rules.append(rule)
        node.unhealthy_rules = unhealthy_rules
        if len(unhealthy_rules) > 0:
            self.k8s_util.annotate(
                node.name, "REPAIR_UNHEALTHY_RULES",
                ",".join([rule.__class__.__name__ for rule in unhealthy_rules]))
            return False
        return True

    def prepare(self, node):
        for rule in node.unhealthy_rules:
            if not rule.prepare(node):
                return False
        return True

    def send_repair_request(self, node):
        args = urllib.parse.urlencode({
            "repair": ",".join([rule.__class__.__name__
                                for rule in node.unhealthy_rules])
        })
        url = urllib.parse.urljoin("http://%s:9180" % node.ip, "/repair")


    def check_liveness(self, node):
        return False


class RepairManagerAgent(object):
    def __init__(self):
        pass

    def run(self):
        pass
