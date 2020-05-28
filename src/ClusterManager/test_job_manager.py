#!/usr/bin/env python3
import sys
import os
import copy

import unittest

sys.path.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../utils"))

from config import config
config["datasource"] = "MySQL"
from cluster_resource import ClusterResource
from job_manager import discount_cluster_resource, \
    get_cluster_schedulable as get_cluster_schedulable_from_reserved, \
    mark_schedulable_non_preemptable_jobs, \
    is_version_satisified


def get_cluster_schedulable_from_unschedulable(cluster_status):
    # Compute cluster schedulable resource
    cluster_capacity = ClusterResource(
        params={
            "cpu": cluster_status["cpu_capacity"],
            "memory": cluster_status["memory_capacity"],
            "gpu": cluster_status["gpu_capacity"],
        })
    cluster_unschedulable = ClusterResource(
        params={
            "cpu": cluster_status["cpu_unschedulable"],
            "memory": cluster_status["memory_unschedulable"],
            "gpu": cluster_status["gpu_unschedulable"],
        })

    cluster_schedulable = cluster_capacity - cluster_unschedulable
    cluster_schedulable = discount_cluster_resource(cluster_schedulable)
    return cluster_schedulable


class TestJobManager(unittest.TestCase):
    def test_mark_schedulable_non_preemptable_gpu_jobs(self):
        # job1 is running on an unschedulable node
        job1_info = {
            "job": {
                "vcName": "platform",
                "jobId": "job1",
            },
            "jobId":
                "job1",
            "job_resource":
                ClusterResource(
                    params={
                        "cpu": {
                            "Standard_ND24rs": 1
                        },
                        "memory": {
                            "Standard_ND24rs": 0
                        },
                        "gpu": {
                            "Standard_ND24rs": 3
                        },
                        "gpu_memory": {
                            "Standard_ND24rs": 0
                        },
                    }),
            "preemptionAllowed":
                False,
            "sort_key":
                "0_0_999899_2020-03-31 08:07:46",
            "allowed":
                False,
        }

        # job2 is running on a good node
        job2_info = {
            "job": {
                "vcName": "platform",
                "jobId": "job2",
            },
            "jobId":
                "job2",
            "job_resource":
                ClusterResource(
                    params={
                        "cpu": {
                            "Standard_ND24rs": 1
                        },
                        "memory": {
                            "Standard_ND24rs": 0
                        },
                        "gpu": {
                            "Standard_ND24rs": 4
                        },
                        "gpu_memory": {
                            "Standard_ND24rs": 0
                        },
                    }),
            "preemptionAllowed":
                False,
            "sort_key":
                "0_0_999899_2020-03-31 08:08:49",
            "allowed":
                False,
        }

        # job3 is submitted just now
        job3_info = {
            "job": {
                "vcName": "platform",
                "jobId": "job3",
            },
            "jobId":
                "job3",
            "job_resource":
                ClusterResource(
                    params={
                        "cpu": {
                            "Standard_ND24rs": 1
                        },
                        "memory": {
                            "Standard_ND24rs": 0
                        },
                        "gpu": {
                            "Standard_ND24rs": 4
                        },
                        "gpu_memory": {
                            "Standard_ND24rs": 0
                        },
                    }),
            "preemptionAllowed":
                False,
            "sort_key":
                "0_2_999899_2020-03-31 09:00:10",
            "allowed":
                False,
        }

        jobs_info = [job1_info, job2_info, job3_info]

        cluster_status = {
            "gpu_capacity": {
                "Standard_ND24rs": 12
            },
            "gpu_reserved": {
                "Standard_ND24rs": 0
            },
            "gpu_unschedulable": {
                "Standard_ND24rs": 4
            },
            "cpu_capacity": {
                "Standard_ND24rs": 72
            },
            "cpu_reserved": {
                "Standard_ND24rs": 23
            },
            "cpu_unschedulable": {
                "Standard_ND24rs": 24
            },
            "memory_capacity": {
                "Standard_ND24rs": "1344Gi"
            },
            "memory_reserved": {
                "Standard_ND24rs": "448Gi"
            },
            "memory_unschedulable": {
                "Standard_ND24rs": "448Gi"
            },
        }

        cluster_capacity = ClusterResource(
            params={
                "cpu": cluster_status["cpu_capacity"],
                "memory": cluster_status["memory_capacity"],
                "gpu": cluster_status["gpu_capacity"],
            })
        cluster_reserved = ClusterResource(
            params={
                "cpu": cluster_status["cpu_reserved"],
                "memory": cluster_status["memory_reserved"],
                "gpu": cluster_status["gpu_reserved"],
            })
        cluster_unschedulable = ClusterResource(
            params={
                "cpu": cluster_status["cpu_unschedulable"],
                "memory": cluster_status["memory_unschedulable"],
                "gpu": cluster_status["gpu_unschedulable"],
            })

        vc_capacity = ClusterResource(
            params={
                "cpu": cluster_status["cpu_capacity"],
                "memory": cluster_status["memory_capacity"],
                "gpu": cluster_status["gpu_capacity"],
            })
        vc_unschedulable = ClusterResource(
            params={
                "cpu": cluster_status["cpu_reserved"],
                "memory": cluster_status["memory_reserved"],
                "gpu": cluster_status["gpu_reserved"],
            })
        vc_schedulable = discount_cluster_resource(vc_capacity -
                                                   vc_unschedulable)
        vc_schedulables = {"platform": vc_schedulable}

        # job3 will not but should be scheduled if using
        # cluster_schedulable = cluster_capacity - cluster_unschedulable
        c_schedulable = discount_cluster_resource(cluster_capacity -
                                                  cluster_unschedulable)

        jobs_info_list = copy.deepcopy(jobs_info)
        mark_schedulable_non_preemptable_jobs(jobs_info_list, c_schedulable,
                                              copy.deepcopy(vc_schedulables))

        self.assertTrue(jobs_info_list[0]["allowed"])
        self.assertTrue(jobs_info_list[1]["allowed"])
        self.assertFalse(jobs_info_list[2]["allowed"])

        # job3 will and should be scheduled if using
        # cluster_schedulable = cluster_capacity - cluster_reserved
        c_schedulable = discount_cluster_resource(cluster_capacity -
                                                  cluster_reserved)

        jobs_info_list = copy.deepcopy(jobs_info)
        mark_schedulable_non_preemptable_jobs(jobs_info_list, c_schedulable,
                                              copy.deepcopy(vc_schedulables))

        self.assertTrue(jobs_info_list[0]["allowed"])
        self.assertTrue(jobs_info_list[1]["allowed"])
        self.assertTrue(jobs_info_list[2]["allowed"])

    def test_version_satisified(self):
        self.assertTrue(is_version_satisified("1.15.1", "1.15"))
        self.assertTrue(is_version_satisified("1.15", "1.15"))
        self.assertTrue(is_version_satisified("1.16", "1.15"))
        self.assertTrue(is_version_satisified("2.16", "1.15"))
        self.assertFalse(is_version_satisified("0", "1.15"))
        self.assertFalse(is_version_satisified("0", "1"))


if __name__ == '__main__':
    unittest.main()
