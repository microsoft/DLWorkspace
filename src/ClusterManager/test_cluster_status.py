#!/usr/bin/env python3

from unittest import TestCase
from cluster_status import str2bool, ClusterStatus


class TestClusterStatus(TestCase):
    def test_str2bool(self):
        self.assertTrue(str2bool("True"))
        self.assertTrue(str2bool("1"))
        self.assertTrue(str2bool("Y"))
        self.assertTrue(str2bool("Yes"))
        self.assertTrue(str2bool("T"))
        self.assertFalse(str2bool("false"))
        self.assertFalse(str2bool("0"))

    def test_get_node_statuses(self):
        pass

    def test_get_cluster_status(self):
        pass
