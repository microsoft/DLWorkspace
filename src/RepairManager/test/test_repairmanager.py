#!/usr/bin/env python3

import logging
import os
import requests
import sys
import threading
import time
import unittest
import urllib

sys.path.append(os.path.abspath("../src/"))

from repairmanager import RepairManager, RepairManagerAgent
from rule import K8sGpuRule, DcgmEccDBERule


logger = logging.getLogger(__name__)


class TestRepairManager(unittest.TestCase):
    def test_step(self):
        pass


class TestRepairManagerAgent(unittest.TestCase):
    def setUp(self):
        logging.basicConfig(
            format="%(asctime)s - %(levelname)s - %(threadName)s - %(filename)s:%(lineno)s - %(message)s",
            level="DEBUG")
        self.ip = "localhost"
        self.port = 9180
        self.agent = RepairManagerAgent(
            [K8sGpuRule(), DcgmEccDBERule()], 9180, dry_run=True)

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
        # Should be able to clear all repair rules whether it's valid or not
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
