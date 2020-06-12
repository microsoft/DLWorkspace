#!/usr/bin/env python3

import logging
import os
import random
import requests
import sys
import threading
import time
import unittest
import urllib

sys.path.append(os.path.abspath("../src/"))

from repairmanager import RepairManager, RepairManagerAgent
from rule import K8sGpuRule, DcgmEccDBERule
from util import State, Node, Job


logger = logging.getLogger(__name__)


random.seed(1)


class TestRepairManager(unittest.TestCase):
    def setUp(self):
        logging.basicConfig(
            format="%(asctime)s - %(levelname)s - %(threadName)s - %(filename)s:%(lineno)s - %(message)s",
            level="DEBUG")
        self.ip = "localhost"
        self.agent_port = random.randrange(9000, 9200)
        rules = [K8sGpuRule(), DcgmEccDBERule()]
        self.repairmanager = RepairManager(
            rules, self.agent_port, None, None, dry_run=True)
        self.agent = RepairManagerAgent(rules, self.agent_port, dry_run=True)
        self.server = threading.Thread(
            target=self.agent.serve, name="agent_server", daemon=True)
        self.node = Node(self.ip, self.ip, True, False, 4, State.IN_SERVICE, [])

    def test_send_repair_request(self):
        # Nothing to send
        self.assertTrue(self.repairmanager.send_repair_request(self.node))

        # Agent is not running
        self.node.unhealthy_rules = [K8sGpuRule()]
        self.assertFalse(self.repairmanager.send_repair_request(self.node))

        # Agent is running
        self.server.start()
        self.assertTrue(self.repairmanager.send_repair_request(self.node))

        # Cannot send a new repair request before the previous one finishes
        self.assertFalse(self.repairmanager.send_repair_request(self.node))

    def test_check_liveness(self):
        # Agent is not running
        self.assertFalse(self.repairmanager.check_liveness(self.node))

        # Agent is running
        self.server.start()
        self.assertTrue(self.repairmanager.check_liveness(self.node))

        # Post a repair
        self.node.unhealthy_rules = [K8sGpuRule()]
        self.assertTrue(self.repairmanager.send_repair_request(self.node))

        # Agent is not alive when a repair is in progress
        self.assertFalse(self.repairmanager.check_liveness(self.node))


class TestRepairManagerAgent(unittest.TestCase):
    def setUp(self):
        logging.basicConfig(
            format="%(asctime)s - %(levelname)s - %(threadName)s - %(filename)s:%(lineno)s - %(message)s",
            level="DEBUG")
        self.ip = "localhost"
        self.port = random.randrange(9000, 9200)
        self.agent = RepairManagerAgent(
            [K8sGpuRule(), DcgmEccDBERule()], self.port, dry_run=True)

    def test_serve(self):
        server = threading.Thread(
            target=self.agent.serve, name="agent_server", daemon=True)
        server.start()

        def check_liveness():
            url = urllib.parse.urljoin(
                "http://%s:%s" % (self.ip, self.port), "/liveness")
            return requests.get(url)

        def wait_for_liveness(timeout=10):
            start = time.time()
            while True:
                if time.time() - start > timeout:
                    return False
                resp = check_liveness()
                if resp.status_code == 200:
                    return True

        def post_repair(rules):
            repair_url = urllib.parse.urljoin(
                "http://%s:%s" % (self.ip, self.port), "/repair")
            return requests.post(repair_url, json=rules)

        alive = wait_for_liveness()
        self.assertTrue(alive)
        resp = check_liveness()
        self.assertEqual(200, resp.status_code)
        self.assertIsNone(self.agent.repair_rules.get())

        # Wrong data format
        resp = post_repair("NoDefRule")
        self.assertEqual(400, resp.status_code)

        # Correct data format
        resp = post_repair(["NoDefRule"])
        self.assertEqual(200, resp.status_code)
        self.assertIsNotNone(self.agent.repair_rules.get())

        # Post again should fail
        resp = post_repair(["NoDefRule"])
        self.assertEqual(503, resp.status_code)

        # Clean up
        self.agent.repair_rules.set(None)
        self.assertIsNone(self.agent.repair_rules.get())

        # Alive again
        resp = check_liveness()
        self.assertEqual(200, resp.status_code)

    def test_handle(self):
        # Should be able to clear all repair rules whether they are valid or not
        handler = threading.Thread(
            target=self.agent.handle, name="agent_handler", daemon=True)
        handler.start()

        self.assertIsNone(self.agent.repair_rules.get())
        self.agent.repair_rules.set(
            ["NoDefRule", "K8sGpuRule", "DcgmEccDBERule"])

        def wait_for_rule_cleanup(timeout=10):
            start = time.time()
            while True:
                if time.time() - start > timeout:
                    return False
                if self.agent.repair_rules.get() is None:
                    return True

        self.assertTrue(wait_for_rule_cleanup())
