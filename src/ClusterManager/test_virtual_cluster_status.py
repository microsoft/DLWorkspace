#!/usr/bin/env python3

import os
import sys

from unittest import TestCase
from cluster_status import ClusterStatus, ClusterStatusFactory
from virtual_cluster_status import VirtualClusterStatus, \
    VirtualClusterStatusesFactory
from cluster_test_utils import BaseTestClusterSetup

sys.path.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../utils"))


class TestVirtualClusterStatus(TestCase):
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
            "pod_status",
            "user_status",
            "user_status_preemptable",
            "available_job_num",
            "vc_name",
        ]
        exclusion = [
            "jobs",
            "node_statuses",
            "pod_statuses",
            "user_statuses",
            "user_statuses_preemptable",
            "jobs_without_pods",
            "vc_info",
            "vc_pod_statuses",
            "vc_jobs",
            "vc_jobs_without_pods",
            "node_status",
        ]

        cs = ClusterStatus({}, {}, [])
        vcs = VirtualClusterStatus("", {}, cs, {}, {}, {})
        d = vcs.to_dict()

        for inc in inclusion:
            self.assertTrue(inc in d)

        for exc in exclusion:
            self.assertFalse(exc in d)

    def test_compute_vc_statuses(self):
        test_cluster = BaseTestClusterSetup()
        nodes = test_cluster.nodes
        pods = test_cluster.pods
        jobs = test_cluster.jobs
        vc_list = test_cluster.vc_list

        cs_factory = ClusterStatusFactory("", nodes, pods, jobs)
        cs = cs_factory.make()

        vcs_factory = VirtualClusterStatusesFactory(cs, vc_list)
        vc_statuses = vcs_factory.make()
        self.assertIsNotNone(vc_statuses)

        t_vc_statuses = test_cluster.vc_statuses
        self.assertEqual(t_vc_statuses, vc_statuses)
