#!/usr/bin/env python3

import logging

from enum import IntEnum
from util import K8sUtil, RestUtil

logger = logging.getLogger(__name__)


class State(IntEnum):
    IN_SERVICE = 1
    OUT_OF_POOL = 2
    READY_FOR_REPAIR = 3
    IN_REPAIR = 4
    AFTER_REPAIR = 5


class Pod(object):
    def __init__(self, name, phase, job_id, username, vc_name):
        self.name = name
        self.phase = phase
        self.job_id = job_id
        self.username = username
        self.vc_name = vc_name


class Node(object):
    def __init__(self, name, host_ip, state, ready, schedulable, unhealthy_rules, pods):
        self.name = name
        self.host_ip = host_ip
        self.state = state
        self.ready = ready
        self.schedulable = schedulable
        self.unhealthy_rules = unhealthy_rules
        self.pods = pods


class Job(object):
    def __init__(self, job_id, status, username, vc_name):
        self.job_id = job_id
        self.status = status
        self.username = username
        self.vc_name = vc_name


class RepairManager(object):
    def __init__(self, rules, dry_run=False):
        self.rules = rules
        self.dry_run = dry_run

        self.k8s_util = K8sUtil()
        self.rest_util = RestUtil()

        self.nodes = []

    def get_repair_state(self):
        nodes = self.k8s_util.list_node()
        pods = self.k8s_util.list_pods()
        for rule in self.rules:
            rule.get_metric_data()

    def update_repair_state(self):
        pass

    def step(self):
        [self.step_for_one_node(node) for node in self.nodes]

    def step_for_one_node(self, node):
        try:
            if node.state == State.IN_SERVICE:
                if self.check_health(node) is False:
                    node.state = State.OUT_OF_POOL
                    # cordon
            elif node.state == State.OUT_OF_POOL:
                if self.prepare(node):
                    node.state = State.READY_FOR_REPAIR
            elif node.state == State.READY_FOR_REPAIR:
                if self.send_repair_request(node):
                    node.state = State.IN_REPAIR
            elif node.state == State.IN_REPAIR:
                if self.check_liveness(node):
                    node.state = State.AFTER_REPAIR
            elif node.state == State.AFTER_REPAIR:
                if self.check_health(node):
                    node.state = State.IN_SERVICE
                    # Uncordon
                else:
                    node.state = State.OUT_OF_POOL
            else:
                logger.error("Node % has unrecognized state: %s", node.name,
                             node.state)
        except:
            logger.exception("Exception in step for node %s", node.name)

    def check_health(self, node):
        unhealthy_rules = []
        for rule in self.rules:
            if not rule.check_health(node):
                unhealthy_rules.append(rule)
        node.unhealthy_rules = unhealthy_rules
        if len(unhealthy_rules) > 0:
            return False
        return True

    def prepare(self, node):
        if self.dry_run:
            return True

        for rule in node.unhealthy_rules:
            if not rule.prepare(node):
                return False
        return True

    def send_repair_request(self, node):
        if self.dry_run:
            return True

        for rule in node.unhealthy_rules:
            if not rule.repair(node):
                return False
        return True

    def check_liveness(self, node):
        if self.dry_run:
            return True

        return False


class RepairManagerAgent(object):
    def __init__(self):
        pass

    def run(self):
        pass
