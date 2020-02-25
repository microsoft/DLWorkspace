#!/usr/bin/env python3

from unittest import TestCase
from job_params_util import make_job_params, \
    DEFAULT_CPU_REQUEST, \
    DEFAULT_CPU_LIMIT, \
    DEFAULT_MEMORY_REQUEST, \
    DEFAULT_MEMORY_LIMIT


class TestJobParams(TestCase):
    def setUp(self):
        self.quota = {
            "platform": {
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
            },
        }
        self.metadata = {
            "platform": {
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
            },
        }

        self.params = {
            "jobtrainingtype": "RegularJob",
            "vcName": "platform",
        }


class TestRegularJobParams(TestJobParams):
    def setUp(self):
        super(TestRegularJobParams, self).setUp()
        self.params.update({
            "jobtrainingtype": "RegularJob",
        })

    def test_backward_compatibility_cpu_job(self):
        # Cpu job on cpu node
        self.params["resourcegpu"] = 0
        job_params = make_job_params(self.params, self.quota, self.metadata)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_D2s_v3", job_params.sku)
        self.assertEqual(0, job_params.gpu_limit)
        self.assertEqual(DEFAULT_CPU_REQUEST, job_params.cpu_request)
        self.assertEqual(DEFAULT_CPU_LIMIT, job_params.cpu_limit)
        self.assertEqual(DEFAULT_MEMORY_REQUEST, job_params.memory_request)
        self.assertEqual(DEFAULT_MEMORY_LIMIT, job_params.memory_limit)

        # Cpu job on gpu node
        self.quota["platform"]["cpu"].pop("Standard_D2s_v3", None)
        job_params = make_job_params(self.params, self.quota, self.metadata)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual(0, job_params.gpu_limit)
        self.assertEqual(DEFAULT_CPU_REQUEST, job_params.cpu_request)
        self.assertEqual(DEFAULT_CPU_LIMIT, job_params.cpu_limit)
        self.assertEqual(DEFAULT_MEMORY_REQUEST, job_params.memory_request)
        self.assertEqual(DEFAULT_MEMORY_LIMIT, job_params.memory_limit)

    def test_backward_compatibility_gpu_job(self):
        # Gpu job with proportionally assigned cpu and memory
        self.params["resourcegpu"] = 3
        job_params = make_job_params(self.params, self.quota, self.metadata)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual(3, job_params.gpu_limit)
        self.assertEqual("16000m", job_params.cpu_request)
        self.assertEqual("18000m", job_params.cpu_limit)
        self.assertEqual("309657Mi", job_params.memory_request)
        self.assertEqual("344064Mi", job_params.memory_limit)

    def test_cpu_job_on_cpu_node(self):
        self.params["gpu_limit"] = 0
        job_params = make_job_params(self.params, self.quota, self.metadata)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_D2s_v3", job_params.sku)
        self.assertEqual(0, job_params.gpu_limit)
        self.assertEqual(DEFAULT_CPU_REQUEST, job_params.cpu_request)
        self.assertEqual(DEFAULT_CPU_LIMIT, job_params.cpu_limit)
        self.assertEqual(DEFAULT_MEMORY_REQUEST, job_params.memory_request)
        self.assertEqual(DEFAULT_MEMORY_LIMIT, job_params.memory_limit)

        # Request override
        self.params.update({
            "cpurequest": "1200m",
            "memoryrequest": "4096Mi",
        })
        job_params = make_job_params(self.params, self.quota, self.metadata)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_D2s_v3", job_params.sku)
        self.assertEqual(0, job_params.gpu_limit)
        self.assertEqual("1200m", job_params.cpu_request)
        self.assertEqual("1200m", job_params.cpu_limit)
        self.assertEqual("4096Mi", job_params.memory_request)
        self.assertEqual("4096Mi", job_params.memory_limit)

        # Limit override
        self.params.update({
            "cpulimit": "1500m",
            "memorylimit": "4608Mi",
        })
        job_params = make_job_params(self.params, self.quota, self.metadata)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_D2s_v3", job_params.sku)
        self.assertEqual(0, job_params.gpu_limit)
        self.assertEqual("1200m", job_params.cpu_request)
        self.assertEqual("1500m", job_params.cpu_limit)
        self.assertEqual("4096Mi", job_params.memory_request)
        self.assertEqual("4608Mi", job_params.memory_limit)

    def test_cpu_job_on_gpu_node(self):
        # Cpu job on gpu node will have default value
        self.params.update({
            "gpu_limit": 0,
            "sku": "Standard_ND24rs",
        })
        job_params = make_job_params(self.params, self.quota, self.metadata)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual(0, job_params.gpu_limit)
        self.assertEqual(DEFAULT_CPU_REQUEST, job_params.cpu_request)
        self.assertEqual(DEFAULT_CPU_LIMIT, job_params.cpu_limit)
        self.assertEqual(DEFAULT_MEMORY_REQUEST, job_params.memory_request)
        self.assertEqual(DEFAULT_MEMORY_LIMIT, job_params.memory_limit)

    def test_gpu_job(self):
        # gpu_limit precedes resourcegpu
        self.params["resourcegpu"] = 0
        self.params["gpu_limit"] = 3
        job_params = make_job_params(self.params, self.quota, self.metadata)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual(3, job_params.gpu_limit)
        self.assertEqual("16000m", job_params.cpu_request)
        self.assertEqual("18000m", job_params.cpu_limit)
        self.assertEqual("309657Mi", job_params.memory_request)
        self.assertEqual("344064Mi", job_params.memory_limit)

        # Request override
        self.params.update({
            "cpurequest": "1200m",
            "memoryrequest": "4096Mi",
        })
        job_params = make_job_params(self.params, self.quota, self.metadata)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual(3, job_params.gpu_limit)
        self.assertEqual("1200m", job_params.cpu_request)
        self.assertEqual("1200m", job_params.cpu_limit)
        self.assertEqual("4096Mi", job_params.memory_request)
        self.assertEqual("4096Mi", job_params.memory_limit)

        # Limit override
        self.params.update({
            "cpulimit": "1500m",
            "memorylimit": "4608Mi",
        })
        job_params = make_job_params(self.params, self.quota, self.metadata)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual(3, job_params.gpu_limit)
        self.assertEqual("1200m", job_params.cpu_request)
        self.assertEqual("1500m", job_params.cpu_limit)
        self.assertEqual("4096Mi", job_params.memory_request)
        self.assertEqual("4608Mi", job_params.memory_limit)


class TestPSDistJobParams(TestJobParams):
    def setUp(self):
        super(TestPSDistJobParams, self).setUp()
        self.params.update({
            "jobtrainingtype": "PSDistJob",
        })

    def test_backward_compatibility_cpu_job(self):
        # Cpu job running on cpu nodes occupy entire nodes
        self.params["resourcegpu"] = 0
        job_params = make_job_params(self.params, self.quota, self.metadata)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_D2s_v3", job_params.sku)
        self.assertEqual(0, job_params.gpu_limit)
        self.assertEqual("1000m", job_params.cpu_request)
        self.assertEqual("2000m", job_params.cpu_limit)
        self.assertEqual("7372Mi", job_params.memory_request)
        self.assertEqual("8192Mi", job_params.memory_limit)

    def test_backward_compatibility_gpu_job(self):
        # Gpu jobs asking for all gpus on nodes
        self.params["resourcegpu"] = 4
        job_params = make_job_params(self.params, self.quota, self.metadata)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual(4, job_params.gpu_limit)
        self.assertEqual("21000m", job_params.cpu_request)
        self.assertEqual("24000m", job_params.cpu_limit)
        self.assertEqual("412876Mi", job_params.memory_request)
        self.assertEqual("458752Mi", job_params.memory_limit)

    def test_cpu_job_on_cpu_node(self):
        self.params["gpu_limit"] = 0
        job_params = make_job_params(self.params, self.quota, self.metadata)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_D2s_v3", job_params.sku)
        self.assertEqual(0, job_params.gpu_limit)
        self.assertEqual("1000m", job_params.cpu_request)
        self.assertEqual("2000m", job_params.cpu_limit)
        self.assertEqual("7372Mi", job_params.memory_request)
        self.assertEqual("8192Mi", job_params.memory_limit)

        # Request override
        self.params.update({
            "cpurequest": "1200m",
            "memoryrequest": "4096Mi",
        })
        job_params = make_job_params(self.params, self.quota, self.metadata)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_D2s_v3", job_params.sku)
        self.assertEqual(0, job_params.gpu_limit)
        self.assertEqual("1200m", job_params.cpu_request)
        self.assertEqual("1200m", job_params.cpu_limit)
        self.assertEqual("4096Mi", job_params.memory_request)
        self.assertEqual("4096Mi", job_params.memory_limit)

        # Limit override
        self.params.update({
            "cpulimit": "1500m",
            "memorylimit": "4608Mi",
        })
        job_params = make_job_params(self.params, self.quota, self.metadata)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_D2s_v3", job_params.sku)
        self.assertEqual(0, job_params.gpu_limit)
        self.assertEqual("1200m", job_params.cpu_request)
        self.assertEqual("1500m", job_params.cpu_limit)
        self.assertEqual("4096Mi", job_params.memory_request)
        self.assertEqual("4608Mi", job_params.memory_limit)

    def test_cpu_job_on_gpu_node(self):
        self.params.update({
            "gpu_limit": 0,
            "sku": "Standard_ND24rs",
        })
        job_params = make_job_params(self.params, self.quota, self.metadata)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual(0, job_params.gpu_limit)
        self.assertEqual(DEFAULT_CPU_REQUEST, job_params.cpu_request)
        self.assertEqual(DEFAULT_CPU_LIMIT, job_params.cpu_limit)
        self.assertEqual(DEFAULT_MEMORY_REQUEST, job_params.memory_request)
        self.assertEqual(DEFAULT_MEMORY_LIMIT, job_params.memory_limit)

    def test_gpu_job(self):
        # gpu_limit precedes resourcegpu
        self.params["resourcegpu"] = 0
        self.params["gpu_limit"] = 3
        job_params = make_job_params(self.params, self.quota, self.metadata)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual(3, job_params.gpu_limit)
        self.assertEqual("16000m", job_params.cpu_request)
        self.assertEqual("18000m", job_params.cpu_limit)
        self.assertEqual("309657Mi", job_params.memory_request)
        self.assertEqual("344064Mi", job_params.memory_limit)

        # Request override
        self.params.update({
            "cpurequest": "1200m",
            "memoryrequest": "4096Mi",
        })
        job_params = make_job_params(self.params, self.quota, self.metadata)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual(3, job_params.gpu_limit)
        self.assertEqual("1200m", job_params.cpu_request)
        self.assertEqual("1200m", job_params.cpu_limit)
        self.assertEqual("4096Mi", job_params.memory_request)
        self.assertEqual("4096Mi", job_params.memory_limit)

        # Limit override
        self.params.update({
            "cpulimit": "1500m",
            "memorylimit": "4608Mi",
        })
        job_params = make_job_params(self.params, self.quota, self.metadata)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual(3, job_params.gpu_limit)
        self.assertEqual("1200m", job_params.cpu_request)
        self.assertEqual("1500m", job_params.cpu_limit)
        self.assertEqual("4096Mi", job_params.memory_request)
        self.assertEqual("4608Mi", job_params.memory_limit)


class TestInferenceJobParams(TestJobParams):
    def setUp(self):
        super(TestInferenceJobParams, self).setUp()
        self.params.update({
            "jobtrainingtype": "InferenceJob",
        })

    def test_backward_compatibility_gpu_job(self):
        # 1 gpu per pod for workers on gpu nodes
        self.params["resourcegpu"] = 1
        job_params = make_job_params(self.params, self.quota, self.metadata)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual(1, job_params.gpu_limit)
        self.assertEqual("5000m", job_params.cpu_request)
        self.assertEqual("6000m", job_params.cpu_limit)
        self.assertEqual("103219Mi", job_params.memory_request)
        self.assertEqual("114688Mi", job_params.memory_limit)

    def test_cpu_job_on_cpu_node(self):
        self.params["gpu_limit"] = 0
        job_params = make_job_params(self.params, self.quota, self.metadata)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_D2s_v3", job_params.sku)
        self.assertEqual(0, job_params.gpu_limit)
        self.assertEqual(DEFAULT_CPU_REQUEST, job_params.cpu_request)
        self.assertEqual(DEFAULT_CPU_LIMIT, job_params.cpu_limit)
        self.assertEqual(DEFAULT_MEMORY_REQUEST, job_params.memory_request)
        self.assertEqual(DEFAULT_MEMORY_LIMIT, job_params.memory_limit)

        # Request override
        self.params.update({
            "cpurequest": "1200m",
            "memoryrequest": "4096Mi",
        })
        job_params = make_job_params(self.params, self.quota, self.metadata)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_D2s_v3", job_params.sku)
        self.assertEqual(0, job_params.gpu_limit)
        self.assertEqual("1200m", job_params.cpu_request)
        self.assertEqual("1200m", job_params.cpu_limit)
        self.assertEqual("4096Mi", job_params.memory_request)
        self.assertEqual("4096Mi", job_params.memory_limit)

        # Limit override
        self.params.update({
            "cpulimit": "1500m",
            "memorylimit": "4608Mi",
        })
        job_params = make_job_params(self.params, self.quota, self.metadata)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_D2s_v3", job_params.sku)
        self.assertEqual(0, job_params.gpu_limit)
        self.assertEqual("1200m", job_params.cpu_request)
        self.assertEqual("1500m", job_params.cpu_limit)
        self.assertEqual("4096Mi", job_params.memory_request)
        self.assertEqual("4608Mi", job_params.memory_limit)

    def test_cpu_job_on_gpu_node(self):
        # Cpu job on gpu node will have default value
        self.params.update({
            "gpu_limit": 0,
            "sku": "Standard_ND24rs",
        })
        job_params = make_job_params(self.params, self.quota, self.metadata)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual(0, job_params.gpu_limit)
        self.assertEqual(DEFAULT_CPU_REQUEST, job_params.cpu_request)
        self.assertEqual(DEFAULT_CPU_LIMIT, job_params.cpu_limit)
        self.assertEqual(DEFAULT_MEMORY_REQUEST, job_params.memory_request)
        self.assertEqual(DEFAULT_MEMORY_LIMIT, job_params.memory_limit)

    def test_gpu_job(self):
        # gpu_limit precedes resourcegpu
        self.params["resourcegpu"] = 0
        self.params["gpu_limit"] = 3
        job_params = make_job_params(self.params, self.quota, self.metadata)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual(3, job_params.gpu_limit)
        self.assertEqual("16000m", job_params.cpu_request)
        self.assertEqual("18000m", job_params.cpu_limit)
        self.assertEqual("309657Mi", job_params.memory_request)
        self.assertEqual("344064Mi", job_params.memory_limit)

        # Request override
        self.params.update({
            "cpurequest": "1200m",
            "memoryrequest": "4096Mi",
        })
        job_params = make_job_params(self.params, self.quota, self.metadata)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual(3, job_params.gpu_limit)
        self.assertEqual("1200m", job_params.cpu_request)
        self.assertEqual("1200m", job_params.cpu_limit)
        self.assertEqual("4096Mi", job_params.memory_request)
        self.assertEqual("4096Mi", job_params.memory_limit)

        # Limit override
        self.params.update({
            "cpulimit": "1500m",
            "memorylimit": "4608Mi",
        })
        job_params = make_job_params(self.params, self.quota, self.metadata)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual(3, job_params.gpu_limit)
        self.assertEqual("1200m", job_params.cpu_request)
        self.assertEqual("1500m", job_params.cpu_limit)
        self.assertEqual("4096Mi", job_params.memory_request)
        self.assertEqual("4608Mi", job_params.memory_limit)
