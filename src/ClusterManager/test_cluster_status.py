#!/usr/bin/env python3

import os
import logging
import sys

import unittest
from cluster_status import str2bool, ClusterStatus, ClusterStatusFactory
from cluster_test_utils import BaseTestClusterSetup

sys.path.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../utils"))


class TestUtils(unittest.TestCase):
    def test_str2bool(self):
        self.assertTrue(str2bool("True"))
        self.assertTrue(str2bool("1"))
        self.assertTrue(str2bool("Y"))
        self.assertTrue(str2bool("Yes"))
        self.assertTrue(str2bool("T"))
        self.assertFalse(str2bool("false"))
        self.assertFalse(str2bool("0"))


class TestClusterStatus(unittest.TestCase):
    def setUp(self):
        logging.basicConfig(
            format="%(asctime)s - %(levelname)s - %(threadName)s - %(filename)s:%(lineno)s - %(message)s",
            level="DEBUG")

    def test_to_dict(self):
        inclusion = [
            "gpu_capacity",
            "gpu_used",
            "gpu_preemptable_used",
            "gpu_available",
            "gpu_unschedulable",
            "gpu_reserved",
            "cpu_capacity",
            "cpu_used",
            "cpu_preemptable_used",
            "cpu_available",
            "cpu_unschedulable",
            "cpu_reserved",
            "memory_capacity",
            "memory_used",
            "memory_preemptable_used",
            "memory_available",
            "memory_unschedulable",
            "memory_reserved",
            "node_status",
            "pod_status",
            "user_status",
            "user_status_preemptable",
            "available_job_num",
        ]
        exclusion = [
            "exclusion", # exclude self
            "jobs",
            "jobs_without_pods",
            "pods_without_node_assignment",
            "node_statuses",
            "pod_statuses",
            "user_statuses",
            "user_statuses_preemptable",
        ]

        cs = ClusterStatus({}, {}, [])
        d = cs.to_dict()

        for inc in inclusion:
            self.assertTrue(inc in d)

        for exc in exclusion:
            self.assertFalse(exc in d)

    def test_compute_cluster_status(self):
        test_cluster = BaseTestClusterSetup()
        nodes = test_cluster.nodes
        pods = test_cluster.pods
        jobs = test_cluster.jobs

        cs_factory = ClusterStatusFactory("", nodes, pods, jobs)
        cs = cs_factory.make()

        t_cluster_status = test_cluster.cluster_status
        self.assertEqual(t_cluster_status, cs)


if __name__ == '__main__':
    logging.basicConfig(
        format=
        '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        level=logging.DEBUG)
    unittest.main()
