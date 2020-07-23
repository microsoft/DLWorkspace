#!/usr/bin/env python3

from unittest import TestCase
from utils_for_test import get_test_quota, get_test_metadata
from job_params_util import make_job_params, get_resource_params_from_job_params


class TestRegularJobParams(TestCase):
    def setUp(self):
        self.quota = get_test_quota()
        self.metadata = get_test_metadata()
        self.params = {
            "jobtrainingtype": "RegularJob",
            "vcName": "platform",
        }
        self.config = {}

    def test_backward_compatibility_cpu_job(self):
        # Cpu job on cpu node
        self.params["resourcegpu"] = 0
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_D2s_v3", job_params.sku)
        self.assertEqual(None, job_params.gpu_type)
        self.assertEqual(0, job_params.gpu_limit)
        self.assertEqual("1000m", job_params.cpu_request)
        self.assertEqual("2000m", job_params.cpu_limit)
        self.assertEqual("0Mi", job_params.memory_request)
        self.assertEqual("8192Mi", job_params.memory_limit)

        # Cpu job on gpu node
        self.quota["cpu"].pop("Standard_D2s_v3", None)
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual("P40", job_params.gpu_type)
        self.assertEqual(0, job_params.gpu_limit)
        self.assertEqual("1000m", job_params.cpu_request)
        self.assertEqual("24000m", job_params.cpu_limit)
        self.assertEqual("0Mi", job_params.memory_request)
        self.assertEqual("458752Mi", job_params.memory_limit)

    def test_backward_compatibility_gpu_job(self):
        # Gpu job with proportionally assigned cpu and memory
        self.params["resourcegpu"] = 3
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual("P40", job_params.gpu_type)
        self.assertEqual(3, job_params.gpu_limit)
        self.assertEqual("1000m", job_params.cpu_request)
        self.assertEqual("24000m", job_params.cpu_limit)
        self.assertEqual("0Mi", job_params.memory_request)
        self.assertEqual("458752Mi", job_params.memory_limit)

    def test_normalize(self):
        # cpurequest absent, memorylimit absent
        self.params.update({
            "gpu_limit": 0,
            "cpulimit": "1000m",
            "memoryrequest": "2048Mi"
        })
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_D2s_v3", job_params.sku)
        self.assertEqual(None, job_params.gpu_type)
        self.assertEqual(0, job_params.gpu_limit)
        self.assertEqual("1000m", job_params.cpu_request)
        self.assertEqual("1000m", job_params.cpu_limit)
        self.assertEqual("2048Mi", job_params.memory_request)
        self.assertEqual("2048Mi", job_params.memory_limit)

        # cpurequest > cpulimit
        self.params["cpurequest"] = "2000m"
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_D2s_v3", job_params.sku)
        self.assertEqual(None, job_params.gpu_type)
        self.assertEqual("1000m", job_params.cpu_request)
        self.assertEqual("1000m", job_params.cpu_limit)
        self.assertEqual("2048Mi", job_params.memory_request)
        self.assertEqual("2048Mi", job_params.memory_limit)

    def test_cpu_job_on_cpu_node(self):
        self.params["gpu_limit"] = 0
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_D2s_v3", job_params.sku)
        self.assertEqual(None, job_params.gpu_type)
        self.assertEqual(0, job_params.gpu_limit)
        self.assertEqual("1000m", job_params.cpu_request)
        self.assertEqual("2000m", job_params.cpu_limit)
        self.assertEqual("0Mi", job_params.memory_request)
        self.assertEqual("8192Mi", job_params.memory_limit)

        # Gpu proportional should show the same
        self.config["job_resource_policy"] = "gpu_proportional"
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_D2s_v3", job_params.sku)
        self.assertEqual(None, job_params.gpu_type)
        self.assertEqual(0, job_params.gpu_limit)
        self.assertEqual("1000m", job_params.cpu_request)
        self.assertEqual("2000m", job_params.cpu_limit)
        self.assertEqual("0Mi", job_params.memory_request)
        self.assertEqual("8192Mi", job_params.memory_limit)

        # Request override
        self.params.update({
            "cpurequest": "1200m",
            "memoryrequest": "4096Mi",
        })
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_D2s_v3", job_params.sku)
        self.assertEqual(None, job_params.gpu_type)
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
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_D2s_v3", job_params.sku)
        self.assertEqual(None, job_params.gpu_type)
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
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual("P40", job_params.gpu_type)
        self.assertEqual(0, job_params.gpu_limit)
        self.assertEqual("1000m", job_params.cpu_request)
        self.assertEqual("24000m", job_params.cpu_limit)
        self.assertEqual("0Mi", job_params.memory_request)
        self.assertEqual("458752Mi", job_params.memory_limit)

        # Gpu proportional should show the same
        self.config["job_resource_policy"] = "gpu_proportional"
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual("P40", job_params.gpu_type)
        self.assertEqual(0, job_params.gpu_limit)
        self.assertEqual("1000m", job_params.cpu_request)
        self.assertEqual("24000m", job_params.cpu_limit)
        self.assertEqual("0Mi", job_params.memory_request)
        self.assertEqual("458752Mi", job_params.memory_limit)

    def test_gpu_job(self):
        # gpu_limit precedes resourcegpu
        self.params["resourcegpu"] = 0
        self.params["gpu_limit"] = 3
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual("P40", job_params.gpu_type)
        self.assertEqual(3, job_params.gpu_limit)
        self.assertEqual("1000m", job_params.cpu_request)
        self.assertEqual("24000m", job_params.cpu_limit)
        self.assertEqual("0Mi", job_params.memory_request)
        self.assertEqual("458752Mi", job_params.memory_limit)

        # Gpu proportional
        self.config["job_resource_policy"] = "gpu_proportional"
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual("P40", job_params.gpu_type)
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
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual("P40", job_params.gpu_type)
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
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual("P40", job_params.gpu_type)
        self.assertEqual(3, job_params.gpu_limit)
        self.assertEqual("1200m", job_params.cpu_request)
        self.assertEqual("1500m", job_params.cpu_limit)
        self.assertEqual("4096Mi", job_params.memory_request)
        self.assertEqual("4608Mi", job_params.memory_limit)


    def test_get_resource_params(self):
        self.params["gpu_limit"] = 3
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                    self.config)
        self.assertIsNotNone(job_params)
        params = {
            "sku": job_params.sku,
            "gpuType": job_params.gpu_type,
            "jobtrainingtype": "RegularJob",
            "resourcegpu": job_params.gpu_limit,
            "cpurequest": job_params.cpu_request,
            "cpulimit": job_params.cpu_limit,
            "memoryrequest": job_params.memory_request,
            "memorylimit": job_params.memory_limit
        }
        resource = get_resource_params_from_job_params(params)
        self.assertTrue({'Standard_ND24rs': 1.0} == resource["cpu"])
        self.assertTrue({'Standard_ND24rs': 0} == resource["memory"])
        self.assertTrue({'Standard_ND24rs': 3.0} == resource["gpu"])
        self.assertTrue({} == resource["gpu_memory"])

class TestPSDistJobParams(TestRegularJobParams):
    def setUp(self):
        super(TestPSDistJobParams, self).setUp()
        self.params["jobtrainingtype"] = "PSDistJob"

    def test_backward_compatibility_cpu_job(self):
        # Cpu job running on cpu nodes occupy entire nodes
        self.params["resourcegpu"] = 0
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_D2s_v3", job_params.sku)
        self.assertEqual(None, job_params.gpu_type)
        self.assertEqual(0, job_params.gpu_limit)
        self.assertEqual("1000m", job_params.cpu_request)
        self.assertEqual("2000m", job_params.cpu_limit)
        self.assertEqual("7372Mi", job_params.memory_request)
        self.assertEqual("8192Mi", job_params.memory_limit)

    def test_backward_compatibility_gpu_job(self):
        # Gpu jobs asking for all gpus on nodes
        self.params["resourcegpu"] = 4
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual("P40", job_params.gpu_type)
        self.assertEqual(4, job_params.gpu_limit)
        self.assertEqual("1000m", job_params.cpu_request)
        self.assertEqual("24000m", job_params.cpu_limit)
        self.assertEqual("0Mi", job_params.memory_request)
        self.assertEqual("458752Mi", job_params.memory_limit)

    def test_cpu_job_on_cpu_node(self):
        self.params["gpu_limit"] = 0
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_D2s_v3", job_params.sku)
        self.assertEqual(None, job_params.gpu_type)
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
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_D2s_v3", job_params.sku)
        self.assertEqual(None, job_params.gpu_type)
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
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_D2s_v3", job_params.sku)
        self.assertEqual(None, job_params.gpu_type)
        self.assertEqual(0, job_params.gpu_limit)
        self.assertEqual("1200m", job_params.cpu_request)
        self.assertEqual("1500m", job_params.cpu_limit)
        self.assertEqual("4096Mi", job_params.memory_request)
        self.assertEqual("4608Mi", job_params.memory_limit)

    def test_cpu_job_on_gpu_node(self):
        # This is disallowed
        pass

    def test_gpu_job(self):
        # gpu_limit precedes resourcegpu
        self.params["resourcegpu"] = 0
        self.params["gpu_limit"] = 3
        self.params["_allow_partial_node"] = True
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual("P40", job_params.gpu_type)
        self.assertEqual(4, job_params.gpu_limit)
        self.assertEqual("1000m", job_params.cpu_request)
        self.assertEqual("24000m", job_params.cpu_limit)
        self.assertEqual("0Mi", job_params.memory_request)
        self.assertEqual("458752Mi", job_params.memory_limit)

        # Admin is allowed to submit partial nodes
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config, is_admin=True)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual("P40", job_params.gpu_type)
        self.assertEqual(3, job_params.gpu_limit)
        self.assertEqual("1000m", job_params.cpu_request)
        self.assertEqual("24000m", job_params.cpu_limit)
        self.assertEqual("0Mi", job_params.memory_request)
        self.assertEqual("458752Mi", job_params.memory_limit)

        # Gpu proportional
        self.config["job_resource_policy"] = "gpu_proportional"
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual("P40", job_params.gpu_type)
        self.assertEqual(4, job_params.gpu_limit)
        self.assertEqual("21000m", job_params.cpu_request)
        self.assertEqual("24000m", job_params.cpu_limit)
        self.assertEqual("412876Mi", job_params.memory_request)
        self.assertEqual("458752Mi", job_params.memory_limit)

    def test_get_resource_params(self):
        self.params["gpu_limit"] = 3
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                    self.config)
        self.assertIsNotNone(job_params)
        params = {
            "sku": job_params.sku,
            "gpuType": job_params.gpu_type,
            "jobtrainingtype": "PSDistJob",
            "numpsworker": 2,
            "numps": 1,
            "resourcegpu": job_params.gpu_limit,
            "cpurequest": job_params.cpu_request,
            "cpulimit": job_params.cpu_limit,
            "memoryrequest": job_params.memory_request,
            "memorylimit": job_params.memory_limit
        }
        resource = get_resource_params_from_job_params(params)
        self.assertTrue({'Standard_ND24rs': 3.0} == resource["cpu"])
        self.assertTrue({'Standard_ND24rs': 0} == resource["memory"])
        self.assertTrue({'Standard_ND24rs': 8.0} == resource["gpu"])
        self.assertTrue({} == resource["gpu_memory"])

class TestInferenceJobParams(TestRegularJobParams):
    def setUp(self):
        super(TestInferenceJobParams, self).setUp()
        self.params["jobtrainingtype"] = "InferenceJob"

    def test_backward_compatibility_cpu_job(self):
        # CPU inference job is not yet supported
        pass


    def test_backward_compatibility_gpu_job(self):
        # 1 gpu per pod for workers on gpu nodes, total 2 gpus
        self.params["resourcegpu"] = 2
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual("P40", job_params.gpu_type)
        self.assertEqual(2, job_params.gpu_limit)
        self.assertEqual("1000m", job_params.cpu_request)
        self.assertEqual("24000m", job_params.cpu_limit)
        self.assertEqual("0Mi", job_params.memory_request)
        self.assertEqual("458752Mi", job_params.memory_limit)

    def test_cpu_job_on_cpu_node(self):
        # Cpu job on cpu node
        self.params["jobtrainingtype"] = "CPUInferenceJob"
        self.params["numOfCPUWorker"] = '2'
        self.params["numOfCPUPerWorker"] = '2'
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_D2s_v3", job_params.sku)
        self.assertEqual(None, job_params.gpu_type)
        self.assertEqual(0, job_params.gpu_limit)
        self.assertEqual("2", job_params.cpu_request)
        self.assertEqual("2", job_params.cpu_limit)
        self.assertEqual("0Mi", job_params.memory_request)
        self.assertEqual("8192Mi", job_params.memory_limit)
        self.assertEqual(2, job_params.num_cpu_workers)

    def test_cpu_job_on_gpu_node(self):
        # Cpu job on gpu node
        self.params["jobtrainingtype"] = "CPUInferenceJob"
        self.params["numOfCPUWorker"] = '2'
        self.params["numOfCPUPerWorker"] = '2'
        self.params["sku"] = "Standard_ND24rs"
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual("P40", job_params.gpu_type)
        self.assertEqual(0, job_params.gpu_limit)
        self.assertEqual("2", job_params.cpu_request)
        self.assertEqual("2", job_params.cpu_limit)
        self.assertEqual("0Mi", job_params.memory_request)
        self.assertEqual("458752Mi", job_params.memory_limit)
        self.assertEqual(2, job_params.num_cpu_workers)

    def test_gpu_job(self):
        # gpu_limit precedes resourcegpu
        self.params["resourcegpu"] = 0
        self.params["gpu_limit"] = 3
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual("P40", job_params.gpu_type)
        self.assertEqual(3, job_params.gpu_limit)
        self.assertEqual("1000m", job_params.cpu_request)
        self.assertEqual("24000m", job_params.cpu_limit)
        self.assertEqual("0Mi", job_params.memory_request)
        self.assertEqual("458752Mi", job_params.memory_limit)

        # Gpu proportional
        self.config["job_resource_policy"] = "gpu_proportional"
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual("P40", job_params.gpu_type)
        self.assertEqual(3, job_params.gpu_limit)
        self.assertEqual("5000m", job_params.cpu_request)
        self.assertEqual("6000m", job_params.cpu_limit)
        self.assertEqual("103219Mi", job_params.memory_request)
        self.assertEqual("114688Mi", job_params.memory_limit)

        # Request override
        self.params.update({
            "cpurequest": "1200m",
            "memoryrequest": "4096Mi",
        })
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual("P40", job_params.gpu_type)
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
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual("P40", job_params.gpu_type)
        self.assertEqual(3, job_params.gpu_limit)
        self.assertEqual("1200m", job_params.cpu_request)
        self.assertEqual("1500m", job_params.cpu_limit)
        self.assertEqual("4096Mi", job_params.memory_request)
        self.assertEqual("4608Mi", job_params.memory_limit)

    def test_preempt_gpu_job(self):
        self.params["mingpu"] = 2
        self.params["maxgpu"] = 4
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                     self.config)
        self.assertIsNotNone(job_params)
        self.assertTrue(job_params.is_valid())
        self.assertEqual("Standard_ND24rs", job_params.sku)
        self.assertEqual("P40", job_params.gpu_type)
        self.assertEqual(2, job_params.gpu_limit)
        self.assertEqual(2, job_params.min_gpu)
        self.assertEqual(4, job_params.max_gpu)
        self.assertEqual("1000m", job_params.cpu_request)
        self.assertEqual("24000m", job_params.cpu_limit)
        self.assertEqual("0Mi", job_params.memory_request)
        self.assertEqual("458752Mi", job_params.memory_limit)

    def test_get_resource_params(self):
        self.params["mingpu"] = 1
        self.params["maxgpu"] = 4
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                    self.config)
        self.assertIsNotNone(job_params)
        params = {
            "sku": job_params.sku,
            "gpuType": job_params.gpu_type,
            "jobtrainingtype": "InferenceJob",
            "resourcegpu": job_params.gpu_limit,
            "cpurequest": job_params.cpu_request,
            "cpulimit": job_params.cpu_limit,
            "memoryrequest": job_params.memory_request,
            "memorylimit": job_params.memory_limit,
            "mingpu": job_params.min_gpu,
            "maxgpu": job_params.max_gpu
        }
        resource = get_resource_params_from_job_params(params)
        self.assertTrue({'Standard_ND24rs': 2.0} == resource["cpu"])
        self.assertTrue({'Standard_ND24rs': 0} == resource["memory"])
        self.assertTrue({'Standard_ND24rs': 1.0} == resource["gpu"])
        self.assertTrue({} == resource["gpu_memory"])
        self.assertIsNotNone(resource["preemptable_resource"])
        self.assertTrue({'Standard_ND24rs': 3.0} == resource["preemptable_resource"]["cpu"])
        self.assertTrue({'Standard_ND24rs': 0} == resource["preemptable_resource"]["memory"])
        self.assertTrue({'Standard_ND24rs': 3.0} == resource["preemptable_resource"]["gpu"])
        self.assertTrue({} == resource["preemptable_resource"]["gpu_memory"])

        self.params["maxgpu"] = 1
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                    self.config)
        params = {
            "sku": job_params.sku,
            "gpuType": job_params.gpu_type,
            "jobtrainingtype": "InferenceJob",
            "resourcegpu": job_params.gpu_limit,
            "cpurequest": job_params.cpu_request,
            "cpulimit": job_params.cpu_limit,
            "memoryrequest": job_params.memory_request,
            "memorylimit": job_params.memory_limit,
            "mingpu": job_params.min_gpu,
            "maxgpu": job_params.max_gpu
        }
        resource = get_resource_params_from_job_params(params)
        self.assertTrue("preemptable_resource" not in resource)

    def test_get_resource_params_cpu(self):
        self.params["numOfCPUWorker"] = "2"
        self.params["numOfCPUPerWorker"] = "2"
        self.params["jobtrainingtype"] = "CPUInferenceJob"
        job_params = make_job_params(self.params, self.quota, self.metadata,
                                    self.config)
        self.assertIsNotNone(job_params)
        params = {
            "sku": job_params.sku,
            "gpuType": job_params.gpu_type,
            "jobtrainingtype": "CPUInferenceJob",
            "resourcegpu": job_params.gpu_limit,
            "cpurequest": job_params.cpu_request,
            "cpulimit": job_params.cpu_limit,
            "memoryrequest": job_params.memory_request,
            "memorylimit": job_params.memory_limit,
            "numOfCPUWorker": job_params.num_cpu_workers
        }
        resource = get_resource_params_from_job_params(params)
        self.assertTrue({'Standard_D2s_v3': 6.0} == resource["cpu"])
        self.assertTrue({'Standard_D2s_v3': 0} == resource["memory"])
        self.assertTrue({} == resource["gpu"])
        self.assertTrue({} == resource["gpu_memory"])