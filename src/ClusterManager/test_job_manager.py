#!/usr/bin/env python3
import sys
import os
import copy
import logging

import unittest

sys.path.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../utils"))

from config import config
config["datasource"] = "MySQL"
from cluster_resource import ClusterResource
from job_manager import discount_cluster_resource, \
    get_cluster_schedulable as get_cluster_schedulable_from_reserved, \
    mark_schedulable_non_preemptable_jobs, \
    mark_schedulable_inference_jobs_non_preemptable_part, \
    mark_schedulable_inference_jobs_preemptable_part, \
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
    def setUp(self):
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

        self.cluster_capacity = ClusterResource(
            params={
                "cpu": cluster_status["cpu_capacity"],
                "memory": cluster_status["memory_capacity"],
                "gpu": cluster_status["gpu_capacity"],
            })

        self.cluster_reserved = ClusterResource(
            params={
                "cpu": cluster_status["cpu_reserved"],
                "memory": cluster_status["memory_reserved"],
                "gpu": cluster_status["gpu_reserved"],
            })

        self.cluster_unschedulable = ClusterResource(
            params={
                "cpu": cluster_status["cpu_unschedulable"],
                "memory": cluster_status["memory_unschedulable"],
                "gpu": cluster_status["gpu_unschedulable"],
            })

        self.vc_capacity = ClusterResource(
            params={
                "cpu": cluster_status["cpu_capacity"],
                "memory": cluster_status["memory_capacity"],
                "gpu": cluster_status["gpu_capacity"],
            })

        self.vc_unschedulable = ClusterResource(
            params={
                "cpu": cluster_status["cpu_reserved"],
                "memory": cluster_status["memory_reserved"],
                "gpu": cluster_status["gpu_reserved"],
            })
        vc_schedulable = discount_cluster_resource(self.vc_capacity -
                                                self.vc_unschedulable)
        self.vc_schedulables = {"platform": vc_schedulable}

    def gen_job_info(self, jobId, job_resource, job_training_type="RegularJob", job_preemptable_resource=None):
        return {
            "job": {
                "vcName": "platform",
                "jobId": jobId,
            },
            "preemptionAllowed": False,
            "jobId": jobId,
            "jobtrainingtype": job_training_type,
            "job_resource": job_resource,
            "job_preemptable_resource": job_preemptable_resource,
            "sort_key": "",
            "allowed": False,
            "allowed_resource": None,
            "status": "queued",
            "reason": None
        }

    def gen_job_resource(self, gpu, cpu=1, memory=0, gpu_memory=0):
        return ClusterResource(
                    params={
                        "cpu": {
                            "Standard_ND24rs": cpu
                        },
                        "memory": {
                            "Standard_ND24rs": memory
                        },
                        "gpu": {
                            "Standard_ND24rs": gpu
                        },
                        "gpu_memory": {
                            "Standard_ND24rs": gpu_memory
                        },
                    })

    def test_mark_schedulable_non_preemptable_gpu_jobs(self):
        # job1 is running on an unschedulable node
        job1_resource = self.gen_job_resource(3)
        job1_info = self.gen_job_info("job1", job1_resource)
        job1_info["sort_key"] = "0_0_999899_2020-03-31 08:07:46"
        job1_info["status"] = "running"

        # job2 is running on a good node
        job2_resource = self.gen_job_resource(4)
        job2_info = self.gen_job_info("job2", job2_resource)
        job2_info["sort_key"] = "0_0_999899_2020-03-31 08:08:49"
        job2_info["status"] = "running"

        # job3 is submitted just now
        job3_resource = self.gen_job_resource(4)
        job3_info = self.gen_job_info("job3", job3_resource)
        job3_info["sort_key"] = "0_2_999899_2020-03-31 09:00:10"
        job3_info["status"] = "queued"

        jobs_info = [job1_info, job2_info, job3_info]

        # job3 will not but should be scheduled if using
        # cluster_schedulable = cluster_capacity - cluster_unschedulable
        c_schedulable = discount_cluster_resource(self.cluster_capacity -
                                                  self.cluster_unschedulable)

        jobs_info_list = copy.deepcopy(jobs_info)
        mark_schedulable_non_preemptable_jobs(jobs_info_list, c_schedulable,
                                              copy.deepcopy(self.vc_schedulables),
                                              {})

        self.assertTrue(jobs_info_list[0]["allowed"])
        self.assertTrue(jobs_info_list[1]["allowed"])
        self.assertFalse(jobs_info_list[2]["allowed"])

        # job3 will and should be scheduled if using
        # cluster_schedulable = cluster_capacity - cluster_reserved
        c_schedulable = discount_cluster_resource(self.cluster_capacity -
                                                  self.cluster_reserved)

        jobs_info_list = copy.deepcopy(jobs_info)
        mark_schedulable_non_preemptable_jobs(jobs_info_list, c_schedulable,
                                              copy.deepcopy(self.vc_schedulables),
                                              {})

        self.assertTrue(jobs_info_list[0]["allowed"])
        self.assertTrue(jobs_info_list[1]["allowed"])
        self.assertTrue(jobs_info_list[2]["allowed"])

    def test_mark_inference_jobs(self):
        # vc gpu: 12, cluster gpu: 8
        # job1: mingpu:1, maxgpu:1. use 1 vc gpu
        job1_resource = self.gen_job_resource(1)
        job1_info = self.gen_job_info("job1", job1_resource, "InferenceJob")

        # job2: mingpu:4, maxgpu: 6. use 4 vc gpu, and 2 cluster gpu
        job2_resource = self.gen_job_resource(4)
        job2_preemptable_resource = self.gen_job_resource(2)
        job2_info = self.gen_job_info("job2", job2_resource, "InferenceJob", job2_preemptable_resource)

        # job3: mingpu:4, maxgpu:6. cannot schedule since cluster gpu cannot satisfy mingpu
        job3_resource = self.gen_job_resource(4)
        job3_preemptable_resource = self.gen_job_resource(2)
        job3_info = self.gen_job_info("job3", job3_resource, "InferenceJob", job3_preemptable_resource)

        # job4: mingpu:0, maxgpu:4. use 4 cluster gpu
        job4_resource = self.gen_job_resource(0)
        job4_preemptable_resource = self.gen_job_resource(4)
        job4_info = self.gen_job_info("job4", job4_resource, "InferenceJob", job4_preemptable_resource)

        jobs_info = [job1_info, job2_info, job3_info, job4_info]

        c_schedulable = discount_cluster_resource(self.cluster_capacity -
                                                  self.cluster_unschedulable)

        self.assertEqual(list(c_schedulable.gpu.to_dict().values())[0], 8.0)
        self.assertEqual(list(self.vc_schedulables["platform"].gpu.to_dict().values())[0], 12.0)

        mark_schedulable_inference_jobs_non_preemptable_part(jobs_info, c_schedulable,
                                                             self.vc_schedulables)
        self.assertTrue(job1_info["allowed"])
        self.assertEqual(job1_info["allowed_resource"], job1_resource)
        self.assertTrue(job2_info["allowed"])
        self.assertEqual(job2_info["allowed_resource"], job2_resource)
        self.assertFalse(job3_info["allowed"])
        self.assertTrue(job4_info["allowed"])
        self.assertEqual(list(c_schedulable.gpu.to_dict().values())[0], 3.0)
        self.assertEqual(list(self.vc_schedulables["platform"].gpu.to_dict().values())[0], 7.0)

        mark_schedulable_inference_jobs_preemptable_part(jobs_info, c_schedulable)

        self.assertTrue(job1_info["allowed"])
        self.assertEqual(job1_info["allowed_resource"], job1_resource)
        self.assertTrue(job2_info["allowed"])
        self.assertEqual(job2_info["allowed_resource"], job2_resource + job2_preemptable_resource)
        self.assertFalse(job3_info["allowed"])
        self.assertTrue(job4_info["allowed"])
        job4_allowed_resource = self.gen_job_resource(1, 0.25)
        self.assertTrue(job4_info["allowed_resource"], job4_allowed_resource)
        self.assertEqual(list(c_schedulable.gpu.to_dict().values())[0], 0)

    def test_version_satisified(self):
        self.assertTrue(is_version_satisified("1.15.1", "1.15"))
        self.assertTrue(is_version_satisified("1.15", "1.15"))
        self.assertTrue(is_version_satisified("1.16", "1.15"))
        self.assertTrue(is_version_satisified("2.16", "1.15"))
        self.assertFalse(is_version_satisified("0", "1.15"))
        self.assertFalse(is_version_satisified("0", "1"))


if __name__ == '__main__':
    logging.basicConfig(
        format=
        '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        level=logging.DEBUG)
    unittest.main()
