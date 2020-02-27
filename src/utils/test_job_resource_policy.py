#!/usr/bin/env python3

from unittest import TestCase
from job_resource_policy import make_job_resource_policy


class TestJobResourcePolicy(TestCase):
    def setUp(self):
        self.quota = {
            "cpu": {
                "Standard_D2s_v3": 4,
                "Standard_ND24rs": 72,
            },
            "memory": {
                "Standard_D2s_v3": "16Gi",
                "Standard_ND24rs": "1344Gi",
            },
            "gpu": {
                "Standard_ND24rs": 12,
            },
        }

        self.metadata = {
            "cpu": {
                "Standard_D2s_v3": {
                    "per_node": 2,
                    "schedulable_ratio": 0.9,
                },
                "Standard_ND24rs": {
                    "per_node": 24,
                    "schedulable_ratio": 0.9,
                },
            },
            "memory": {
                "Standard_D2s_v3": {
                    "per_node": "8Gi",
                    "schedulable_ratio": 0.9,
                },
                "Standard_ND24rs": {
                    "per_node": "448Gi",
                    "schedulable_ratio": 0.9,
                },
            },
            "gpu": {
                "Standard_ND24rs": {
                    "per_node": 4,
                    "gpu_type": "P40",
                    "schedulable_ratio": 1,
                },
            },
        }

        self.config = {
            "job_resource_policy": "default",
        }

    def test_override(self):
        self.config.update({
            "default_cpurequest": "12000m",
            "default_cpulimit": "14000m",
            "default_memoryrequest": "102400Mi",
            "default_memorylimit": "409600Mi",
        })
        policy = make_job_resource_policy("Standard_ND24rs", 0, self.config,
                                          self.quota, self.metadata)
        self.assertIsNotNone(policy)
        self.assertEqual("12000m", policy.default_cpu_request)
        self.assertEqual("14000m", policy.default_cpu_limit)
        self.assertEqual("102400Mi", policy.default_memory_request)
        self.assertEqual("409600Mi", policy.default_memory_limit)

    def test_cpu_job(self):
        policy = make_job_resource_policy("Standard_ND24rs", 0, self.config,
                                          self.quota, self.metadata)
        self.assertIsNotNone(policy)
        self.assertEqual("1000m", policy.default_cpu_request)
        self.assertEqual("24000m", policy.default_cpu_limit)
        self.assertEqual("0Mi", policy.default_memory_request)
        self.assertEqual("458752Mi", policy.default_memory_limit)

    def test_gpu_job(self):
        policy = make_job_resource_policy("Standard_ND24rs", 3, self.config,
                                          self.quota, self.metadata)
        self.assertIsNotNone(policy)
        self.assertEqual("1000m", policy.default_cpu_request)
        self.assertEqual("24000m", policy.default_cpu_limit)
        self.assertEqual("0Mi", policy.default_memory_request)
        self.assertEqual("458752Mi", policy.default_memory_limit)


class TestGpuProportionalPolicy(TestJobResourcePolicy):
    def setUp(self):
        super(TestGpuProportionalPolicy, self).setUp()
        self.config["job_resource_policy"] = "gpu_proportional"

    def test_gpu_job(self):
        policy = make_job_resource_policy("Standard_ND24rs", 3, self.config,
                                          self.quota, self.metadata)
        self.assertIsNotNone(policy)
        self.assertEqual("16000m", policy.default_cpu_request)
        self.assertEqual("18000m", policy.default_cpu_limit)
        self.assertEqual("309657Mi", policy.default_memory_request)
        self.assertEqual("344064Mi", policy.default_memory_limit)
