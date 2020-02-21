#!/usr/bin/env python3

from unittest import TestCase
from virtual_cluster_status import VirtualClusterStatus, \
    VirtualClusterStatusesFactory


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
            "node_status",
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
            "vc_metrics_map",
            "jobs_without_pods",
        ]

        vcs = VirtualClusterStatus("", {}, {}, {}, {}, [])
        d = vcs.to_dict()

        for inc in inclusion:
            self.assertTrue(inc in d)

        for exc in exclusion:
            self.assertFalse(exc in d)

    def test_compute_vc_statuses(self):
        pass
