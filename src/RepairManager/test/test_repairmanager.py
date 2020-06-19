#!/usr/bin/env python3

import copy
import datetime
import logging
import os
import random
import sys
import threading
import time
import unittest

sys.path.append(os.path.abspath("../src/"))

from repairmanager import RepairManager
from agent import Agent
from rule import Rule
from util import State, Node


logger = logging.getLogger(__name__)


random.seed(1)


class RuleForTest(Rule):
    def __init__(self):
        super(RuleForTest, self).__init__("test")
        self.health = True
        self.prepared = False

    def update_data(self):
        pass

    def check_health(self, node, stat=None):
        return self.health

    def prepare(self, node):
        return self.prepared

    def repair(self):
        return True


class K8sUtilForTest(object):
    def __init__(self):
        self.patch_result = True

    def patch_node(self, node, unschedulable=None, labels=None,
                   annotations=None):
        return self.patch_result


class TestRepairManager(unittest.TestCase):
    def setUp(self):
        logging.basicConfig(
            format="%(asctime)s - %(levelname)s - %(threadName)s - %(filename)s:%(lineno)s - %(message)s",
            level="DEBUG")
        self.ip = "localhost"
        self.port = 8999
        self.agent_port = random.randrange(9000, 9200)
        self.rules = [RuleForTest()]
        self.k8s_util = K8sUtilForTest()
        self.repairmanager = RepairManager(self.rules,
                                           {},
                                           self.port,
                                           self.agent_port,
                                           self.k8s_util,
                                           None,
                                           dry_run=True)
        self.agent = Agent(self.rules, self.agent_port)
        self.server = threading.Thread(
            target=self.agent.serve, name="agent_server", daemon=True)
        self.node = Node(self.ip,
                         self.ip,
                         True,
                         False,
                         "Standard_ND24rs",
                         4,
                         4,
                         4,
                         State.IN_SERVICE,
                         [])

    def test_validate(self):
        self.repairmanager.dry_run = False

        # Node is in valid state
        self.assertTrue(self.repairmanager.validate(self.node))

        # Node is not in a valid state, patch is working
        for state in [State.OUT_OF_POOL, State.READY_FOR_REPAIR,
                      State.IN_REPAIR, State.AFTER_REPAIR]:
            self.node.unschedulable = False
            self.node.state = state
            self.assertTrue(self.repairmanager.validate(self.node))
            self.assertEqual(State.OUT_OF_POOL, self.node.state)
            self.assertEqual(True, self.node.unschedulable)

        # Node is not in a valid state, patch is not working
        self.k8s_util.patch_result = False
        for state in [State.OUT_OF_POOL, State.READY_FOR_REPAIR,
                      State.IN_REPAIR, State.AFTER_REPAIR]:
            self.node.unschedulable = False
            self.node.state = state
            self.assertFalse(self.repairmanager.validate(self.node))
            self.assertEqual(state, self.node.state)
            self.assertEqual(False, self.node.unschedulable)

    def wait_for_alive(self, timeout=10):
        start = time.time()
        while True:
            if time.time() - start > timeout:
                return False
            try:
                if self.repairmanager.check_liveness():
                    return True
            except:
                pass

    def wait_for_repair(self, timeout=10):
        start = time.time()
        while True:
            self.repairmanager.update(self.node)
            if time.time() - start > timeout:
                return False
            if self.node.state == State.AFTER_REPAIR:
                return True
            time.sleep(1)

    def test_repair_cycle_update(self):
        # IN_SERVICE -> OUT_OF_POOL
        self.rules[0].health = True
        self.repairmanager.update(self.node)
        self.assertEqual(State.IN_SERVICE, self.node.state)
        self.assertEqual(False, self.node.unschedulable)
        self.assertEqual([], self.node.unhealthy_rules)

        self.rules[0].health = False
        self.repairmanager.update(self.node)
        self.assertEqual(State.OUT_OF_POOL, self.node.state)
        self.assertEqual(True, self.node.unschedulable)
        self.assertEqual(self.rules, self.node.unhealthy_rules)

        # OUT_OF_POOL -> READY_FOR_REPAIR
        self.rules[0].prepared = False
        self.repairmanager.update(self.node)
        self.assertEqual(State.OUT_OF_POOL, self.node.state)
        self.assertEqual(True, self.node.unschedulable)

        self.rules[0].prepared = True
        self.repairmanager.update(self.node)
        self.assertEqual(State.READY_FOR_REPAIR, self.node.state)
        self.assertEqual(True, self.node.unschedulable)

        # READY_FOR_REPAIR -> IN_REPAIR
        self.repairmanager.update(self.node)
        self.assertEqual(State.READY_FOR_REPAIR, self.node.state)
        self.assertEqual(True, self.node.unschedulable)

        # Agent becomes alive
        self.server.start()
        self.wait_for_alive()

        self.repairmanager.update(self.node)
        self.assertEqual(State.IN_REPAIR, self.node.state)
        self.assertEqual(True, self.node.unschedulable)

        # IN_REPAIR -> IN_REPAIR
        self.repairmanager.update(self.node)
        self.assertEqual(State.IN_REPAIR, self.node.state)
        self.assertEqual(True, self.node.unschedulable)

        # Agent start to consume repair signal
        self.agent.repair_handler.start()

        def wait_for_repair(timeout=10):
            start = time.time()
            while True:
                self.repairmanager.update(self.node)
                if time.time() - start > timeout:
                    return False
                if self.node.state == State.AFTER_REPAIR:
                    return True
                time.sleep(1)

        # IN_REPAIR -> AFTER_REPAIR
        self.assertTrue(wait_for_repair())

        node = copy.deepcopy(self.node)

        # AFTER_REPAIR -> AFTER_REPAIR
        # unhealthy in grace period
        self.repairmanager.grace_period = 60
        node.last_update_time = str(datetime.datetime.timestamp(
            datetime.datetime.utcnow()))
        self.rules[0].health = False
        self.repairmanager.update(node)
        self.assertEqual(State.AFTER_REPAIR, node.state)
        self.assertEqual(True, node.unschedulable)
        self.assertEqual(self.rules, node.unhealthy_rules)

        # AFTER_REPAIR -> OUT_OF_POOL
        # unhealthy after grace period
        self.repairmanager.grace_period = -1  # Make sure it's after grace period
        self.repairmanager.update(node)
        self.assertEqual(State.OUT_OF_POOL, node.state)
        self.assertEqual(True, node.unschedulable)
        self.assertEqual(self.rules, node.unhealthy_rules)

        # AFTER_REPAIR -> IN_SERVICE
        self.rules[0].health = True
        self.repairmanager.update(self.node)
        self.assertEqual(State.IN_SERVICE, self.node.state)
        self.assertEqual(False, self.node.unschedulable)
        self.assertEqual([], self.node.unhealthy_rules)

    def test_check_health(self):
        # Node is healthy
        self.assertTrue(self.repairmanager.check_health(self.node))

        # Node becomes unhealthy
        self.rules[0].health = False
        self.assertFalse(self.repairmanager.check_health(self.node))

    def test_prepare(self):
        self.node.state = State.OUT_OF_POOL
        self.node.unschedulable = True
        self.node.unhealthy_rules = self.rules

        # Node is not prepared
        self.assertFalse(self.repairmanager.prepare(self.node))

        # Node becomes prepared
        self.rules[0].prepared = True
        self.assertTrue(self.repairmanager.prepare(self.node))

    def test_send_repair_request(self):
        # Nothing to send
        self.assertTrue(self.repairmanager.send_repair_request(self.node))

        # Agent is not running
        self.node.unhealthy_rules = [RuleForTest()]
        self.assertFalse(self.repairmanager.send_repair_request(self.node))

        # Agent is running
        self.server.start()
        self.wait_for_alive()
        self.assertTrue(self.repairmanager.send_repair_request(self.node))

        # Cannot send a new repair request before the previous one finishes
        self.assertFalse(self.repairmanager.send_repair_request(self.node))

    def test_check_liveness(self):
        # Agent is not running
        self.assertFalse(self.repairmanager.check_liveness(self.node))

        # Agent is running
        self.server.start()
        self.wait_for_alive()
        self.assertTrue(self.repairmanager.check_liveness(self.node))

        # Post a repair
        self.node.unhealthy_rules = [RuleForTest()]
        self.assertTrue(self.repairmanager.send_repair_request(self.node))

        # Agent is not alive when a repair is in progress
        self.assertFalse(self.repairmanager.check_liveness(self.node))

    def test_get_unhealthy_rules_value(self):
        self.assertEqual(
            None, self.repairmanager.get_unhealthy_rules_value(self.node))

        self.node.unhealthy_rules = [RuleForTest()]
        self.assertEqual(
            "RuleForTest",
            self.repairmanager.get_unhealthy_rules_value(self.node))


if __name__ == '__main__':
    unittest.main()
