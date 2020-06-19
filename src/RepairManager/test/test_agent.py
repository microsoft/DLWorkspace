#!/usr/bin/env python3

import copy
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

from agent import Agent
from rule import Rule


logger = logging.getLogger(__name__)


random.seed(1)


class RuleForTest(Rule):
    def __init__(self):
        super(RuleForTest, self).__init__("test")
        self.health = True
        self.prepared = False
        self.is_repaired = False

    def update_data(self):
        pass

    def check_health(self, node, stat=None):
        return self.health

    def prepare(self, node):
        return self.prepared

    def repair(self):
        return self.is_repaired


class TestAgent(unittest.TestCase):
    def setUp(self):
        logging.basicConfig(
            format="%(asctime)s - %(levelname)s - %(threadName)s - %(filename)s:%(lineno)s - %(message)s",
            level="DEBUG")
        self.ip = "localhost"
        self.port = random.randrange(9000, 9200)
        self.agent = Agent([RuleForTest()], self.port)

    def test_serve(self):
        server = threading.Thread(
            target=self.agent.serve, name="agent_server", daemon=True)
        server.start()

        def check_liveness():
            url = urllib.parse.urljoin(
                "http://%s:%s" % (self.ip, self.port), "/liveness")
            return requests.get(url)

        def wait_for_alive(timeout=10):
            start = time.time()
            while True:
                if time.time() - start > timeout:
                    return False
                try:
                    resp = check_liveness()
                    if resp.status_code == 200:
                        return resp
                except:
                    pass

        def post_repair(rules):
            repair_url = urllib.parse.urljoin(
                "http://%s:%s" % (self.ip, self.port), "/repair")
            return requests.post(repair_url, json=rules)

        alive = wait_for_alive()
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
        self.assertIsNone(self.agent.repair_rules.get())
        self.agent.repair_rules.set(["NoDefRule", "RuleForTest"])

        # Should be able to clear all repair rules whether they are valid or not
        handler = threading.Thread(
            target=self.agent.handle, name="agent_handler", daemon=True)
        handler.start()

        def wait_for_rule_cleanup(timeout=6):
            start = time.time()
            while True:
                if time.time() - start > timeout:
                    return False
                if self.agent.repair_rules.get() is None:
                    return True

        # Agent should keep repairing if failed to repair
        self.agent.rules[0].is_repaired = False
        self.assertFalse(wait_for_rule_cleanup())

        # Agent should keep repairing if failed to repair
        self.agent.rules[0].is_repaired = True
        self.assertTrue(wait_for_rule_cleanup())


if __name__ == '__main__':
    unittest.main()
