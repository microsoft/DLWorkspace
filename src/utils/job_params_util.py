#!/usr/bin/env python3

import logging

from resource_stat import make_resource
from job_resource_policy import make_job_resource_policy

logger = logging.getLogger(__name__)


def override(func):
    return func


def get_resourcegpu(params):
    return max(0, int(params.get("resourcegpu", 0)))


def get_gpu_limit(params):
    return int(params.get("gpu_limit", get_resourcegpu(params)))


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
        resource_gpu = get_gpu_limit(params)
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
        # Only support 1 GPU per worker now
        # Master
        cpu += make_resource("cpu", {sku: cpu_request})
        memory += make_resource("memory", {sku: mem_request})

        # Inference workers
        for i in range(resource_gpu):
            cpu += make_resource("cpu", {sku: cpu_request})
            memory += make_resource("memory", {sku: mem_request})
            gpu += make_resource("gpu", {sku: 1})
    else:
        logger.warning("Unrecognized job type %s", job_type)

    return {
        "cpu": cpu.to_dict(),
        "memory": memory.to_dict(),
        "gpu": gpu.to_dict(),
        "gpu_memory": gpu_memory.to_dict(),
    }


class JobParams(object):
    def __init__(self, params, quota, metadata, config, is_admin=False):
        """Constructor for JobParams.

        Args:
            params: A dictionary of job parameters
            quota: Resource quota
            metadata: Resource metadata
        """
        self.job_id = params.get("jobId")
        self.params = params
        self.quota = quota
        self.metadata = metadata
        self.config = config
        self.is_admin = is_admin

        self.policy = None

        self.sku = None
        self.gpu_limit = None
        self.cpu_request = None
        self.cpu_limit = None
        self.memory_request = None
        self.memory_limit = None

        self.generate()

    def generate(self):
        self.gen_sku()
        self.gen_gpu()
        # Job resource policy is dependent on sku and gpu
        self.gen_policy()
        self.gen_cpu()
        self.gen_memory()

    def is_valid(self):
        checklist = [
            "sku",
            "gpu_limit",
            "cpu_request",
            "cpu_limit",
            "memory_request",
            "memory_limit",
        ]
        for key in checklist:
            if self.__dict__[key] is None:
                return False
        return True

    def gen_sku(self):
        sku = self.params.get("sku", "")
        if sku != "":
            self.sku = sku
            return

        sku_list = self.get_sku_list()
        if len(sku_list) > 0:
            self.sku = sku_list[0]

    @override
    def gen_gpu(self):
        # TODO: Deprecate resource_gpu in the future
        resource_gpu = self.params.get("resourcegpu")
        self.gpu_limit = self.params.get("gpu_limit", resource_gpu)

        gpu_limit = self.get_gpu_limit()

        if self.gpu_limit is None:
            self.gpu_limit = gpu_limit
        if self.gpu_limit is not None:
            self.gpu_limit = int(self.gpu_limit)

    @override
    def gen_policy(self):
        self.policy = make_job_resource_policy(self.sku, self.gpu_limit,
                                               self.config, self.quota,
                                               self.metadata)

    def gen_cpu(self):
        self.cpu_request = self.params.get("cpurequest")
        self.cpu_limit = self.params.get("cpulimit")
        self.cpu_request, self.cpu_limit = \
            self.normalize("cpu", self.cpu_request, self.cpu_limit)

        request, limit = self.get_default_cpu_request_and_limit()
        request, limit = self.normalize("cpu", request, limit)

        if self.cpu_request is None:
            self.cpu_request = request
            self.cpu_limit = limit

    def gen_memory(self):
        self.memory_request = self.params.get("memoryrequest")
        self.memory_limit = self.params.get("memorylimit")
        self.memory_request, self.memory_limit = \
            self.normalize("memory", self.memory_request, self.memory_limit)

        request, limit = self.get_default_memory_request_and_limit()
        request, limit = self.normalize("memory", request, limit)

        if self.memory_request is None:
            self.memory_request = request
            self.memory_limit = limit

    def get_sku_list(self):
        gpu_sku_list = [
            sku_val for sku_val, _ in self.quota.get("gpu", {}).items()
        ]
        cpu_sku_list = [
            sku_val for sku_val, _ in self.quota.get("cpu", {}).items()
            if self.metadata.get("gpu", {}).get(sku_val) is None
        ]
        if len(cpu_sku_list) == 0:
            cpu_sku_list = gpu_sku_list

        gpu_limit = get_gpu_limit(self.params)
        if gpu_limit > 0:
            return gpu_sku_list
        else:
            return cpu_sku_list

    @override
    def get_gpu_limit(self):
        return get_gpu_limit(self.params)

    @override
    def get_default_cpu_request_and_limit(self):
        request = self.policy.default_cpu_request
        limit = self.policy.default_cpu_limit
        return request, limit

    @override
    def get_default_memory_request_and_limit(self):
        request = self.policy.default_memory_request
        limit = self.policy.default_memory_limit
        return request, limit

    def __repr__(self):
        return "%s" % {
            "job_id": self.job_id,
            "sku": self.sku,
            "gpu_limit": self.gpu_limit,
            "cpu_request": self.cpu_request,
            "cpu_limit": self.cpu_limit,
            "memory_request": self.memory_request,
            "memory_limit": self.memory_limit,
        }

    def normalize(self, r_type, request, limit):
        if request is None and limit is not None:
            request = limit
        elif request is not None and limit is None:
            limit = request
        elif request is not None and limit is not None:
            request_res = make_resource(r_type, {self.sku: request})
            limit_res = make_resource(r_type, {self.sku: limit})
            if request_res >= limit_res:
                request = limit
        return request, limit


class RegularJobParams(JobParams):
    def __init__(self, params, quota, metadata, config, is_admin=False):
        super(RegularJobParams, self).__init__(params, quota, metadata, config,
                                               is_admin)


class PSDistJobParams(JobParams):
    """Always allocate entire nodes for workers if no resource request.
    """
    def __init__(self, params, quota, metadata, config, is_admin=False):
        super(PSDistJobParams, self).__init__(params, quota, metadata, config,
                                              is_admin)

    def gen_gpu(self):
        # Allow admins to specify 0 GPU for efficient integration tests
        if self.is_admin and self.params.get("_allow_partial_node", False):
            super(PSDistJobParams, self).gen_gpu()
        else:
            # Allocate all GPUs in a node for workers
            self.gpu_limit = self.metadata.get("gpu", {}).get(self.sku, {}).\
                get("per_node", 0)

    def get_default_cpu_request_and_limit(self):
        if self.cpu_job_on_cpu_node:
            policy = self.policy
            per_node, schedulable_ratio = policy.get_sku_resource_info("cpu")
            request = (per_node * schedulable_ratio).scalar(self.sku)
            limit = per_node.scalar(self.sku)
        else:
            request, limit = super(PSDistJobParams, self).\
                get_default_cpu_request_and_limit()
        return request, limit

    def get_default_memory_request_and_limit(self):
        if self.cpu_job_on_cpu_node:
            policy = self.policy
            per_node, schedulable_ratio = policy.get_sku_resource_info("memory")
            request = (per_node * schedulable_ratio).scalar(self.sku)
            limit = per_node.scalar(self.sku)
        else:
            request, limit = super(PSDistJobParams, self).\
                get_default_memory_request_and_limit()
        return request, limit

    @property
    def cpu_job_on_cpu_node(self):
        is_cpu_job = self.gpu_limit == 0
        on_cpu_node = self.metadata.get("gpu", {}).get(self.sku) is None
        return is_cpu_job and on_cpu_node


class InferenceJobParams(JobParams):
    """Always allocate 1 GPU for each worker if any.
    NOTE: The behavior of a CPU inference job is undefined.
    """
    def __init__(self, params, quota, metadata, config, is_admin=False):
        super(InferenceJobParams, self).__init__(params, quota, metadata,
                                                 config, is_admin)

    def gen_policy(self):
        self.policy = make_job_resource_policy(
            self.sku,
            1, # 1 GPU per worker
            self.config,
            self.quota,
            self.metadata)


JOB_PARAMS_MAPPING = {
    "RegularJob": RegularJobParams,
    "PSDistJob": PSDistJobParams,
    "InferenceJob": InferenceJobParams,
}


def make_job_params(params, quota, metadata, config, is_admin=False):
    job_params = None
    try:
        job_type = params.get("jobtrainingtype")
        job_params = JOB_PARAMS_MAPPING[job_type](params, quota, metadata,
                                                  config, is_admin)
    except ValueError:
        logger.exception("Bad job type in params %s", params)
    except Exception:
        logger.exception("Exception in creating job_params with params %s",
                         params)
    return job_params
