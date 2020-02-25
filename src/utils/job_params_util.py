#!/usr/bin/env python3

import logging

from resource_stat import make_resource

logger = logging.getLogger(__name__)


def override(func):
    return func


def get_resource_params_from_job_params(params):
    cpu = make_resource("cpu")
    memory = make_resource("memory")
    gpu = make_resource("gpu")
    gpu_memory = make_resource("gpu_memory")

    job_type = params.get("jobtrainingtype", "RegularJob")
    sku = params.get("sku", "")

    # Default to 1 CPU, 0 memory if not specified
    # Consistent with pod.yaml.template
    cpu_request = params.get("cpurequest", 1)
    mem_request = params.get("memoryrequest", 0)
    try:
        resource_gpu = max(0, int(params.get("resourcegpu", 0)))
    except:
        logger.warning("Parsing resourcegpu in %s failed. Set to 0.", params)
        resource_gpu = 0

    if job_type == "RegularJob":
        cpu = make_resource("cpu", {sku: cpu_request})
        memory = make_resource("memory", {sku: mem_request})
        gpu = make_resource("gpu", {sku: resource_gpu})
    elif job_type == "PSDistJob":
        # Each ps reserves 1 CPU and 0 memory
        num_ps = int(params.get("numps", 0))
        cpu += make_resource("cpu", {sku: num_ps})
        memory += make_resource("memory", {sku: 0})

        # Add worker CPU requirement
        num_worker = int(params.get("numpsworker", 0))
        for i in range(num_worker):
            cpu += make_resource("cpu", {sku: cpu_request})
            memory += make_resource("memory", {sku: mem_request})
            gpu += make_resource("gpu", {sku: resource_gpu})
    elif job_type == "InferenceJob":
        # Master
        cpu += make_resource("cpu", {sku: cpu_request})
        memory += make_resource("memory", {sku: mem_request})

        # Inference workers
        for i in range(resource_gpu):
            cpu += make_resource("cpu", {sku: cpu_request})
            memory += make_resource("memory", {sku: mem_request})
            gpu += make_resource("gpu", {sku: resource_gpu})
    else:
        logger.warning("Unrecognized job type %s", job_type)

    return {
        "cpu": cpu.to_dict(),
        "memory": memory.to_dict(),
        "gpu": gpu.to_dict(),
        "gpu_memory": gpu_memory.to_dict(),
    }


DEFAULT_CPU_REQUEST = "500m"
DEFAULT_CPU_LIMIT = "500m"
DEFAULT_MEMORY_REQUEST = "2048Mi"
DEFAULT_MEMORY_LIMIT = "2560Mi"


class JobParams(object):
    subclasses = {}

    @classmethod
    def register_subclass(cls, job_type):
        def decorator(subclass):
            cls.subclasses[job_type] = subclass
            return subclass

        return decorator

    @classmethod
    def create(cls, job_type, params, quota, metadata):
        if job_type not in cls.subclasses:
            raise ValueError("Bad job type %s" % job_type)
        return cls.subclasses[job_type](params, quota, metadata)

    def __init__(self, params, quota, metadata):
        self.params = params
        self.quota = quota
        self.metadata = metadata
        self.job_id = params.get("jobId")

        self.sku = None
        self.gpu_limit = None
        self.cpu_request = None
        self.cpu_limit = None
        self.memory_request = None
        self.memory_limit = None

        self.generate()

    def generate(self):
        self.gen_gpu()
        self.gen_cpu()
        self.gen_memory()
        self.gen_sku()

    @override
    def gen_gpu(self):
        gpu = 0
        try:
            gpu = max(0, int(self.params.get("resourcegpu")))
        except:
            logger.exception("Parsing resourcegpu in params %s failed",
                             self.params)
        self.gpu_limit = gpu

    @override
    def gen_cpu(self):
        self.cpu_request = self.params.get("cpurequest", DEFAULT_CPU_REQUEST)
        self.cpu_limit = self.params.get("cpulimit", DEFAULT_CPU_LIMIT)

    @override
    def gen_memory(self):
        self.memory_request = self.params.get("memoryrequest",
                                              DEFAULT_MEMORY_REQUEST)
        self.memory_limit = self.params.get("memorylimit", DEFAULT_MEMORY_LIMIT)

    @override
    def gen_sku(self):
        if self.gpu_limit > 0:
            sku_from_key = "gpu"
        else:
            sku_from_key = "cpu"
        sku_list = [
            sku for sku, _ in self.quota.get(sku_from_key, {}).items()
        ]
        if len(sku_list) > 0:
            self.sku = sku_list[0]

    def __repr__(self):
        return "sku: %s. gpu_limit: %s. cpu_request: %s. cpu_limit: %s. " \
               "memory_request: %s. memory_limit: %s" % (
                self.sku, self.gpu_limit, self.cpu_request, self.cpu_limit,
                self.memory_request, self.memory_limit)


@JobParams.register_subclass("RegularJob")
class RegularJobParams(JobParams):
    def __init__(self, params, quota, metadata):
        super(RegularJobParams, self).__init__(params, quota, metadata)


@JobParams.register_subclass("PSDistJob")
class PSDistJobParams(JobParams):
    def __init__(self, params, quota, metadata):
        super(PSDistJobParams, self).__init__(params, quota, metadata)


@JobParams.register_subclass("InferenceJob")
class InferenceJobParams(JobParams):
    def __init__(self, params, quota, metadata):
        super(InferenceJobParams, self).__init__(params, quota, metadata)


def make_job_params(params, quota, metadata):
    job_params = None
    try:
        job_type = params.get("jobtrainingtype")
        job_params = JobParams.create(job_type, params, quota, metadata)
    except ValueError:
        logger.exception("Bad job type in params %s", params)
    except Exception:
        logger.exception("Exception in creating job_params with params %s",
                         params)
    return job_params
