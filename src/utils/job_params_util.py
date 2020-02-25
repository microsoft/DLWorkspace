#!/usr/bin/env python3

import logging

from resource_stat import make_resource

logger = logging.getLogger(__name__)


DEFAULT_CPU_REQUEST = 1
DEFAULT_CPU_LIMIT = 1
DEFAULT_MEMORY_REQUEST = "2048Mi"
DEFAULT_MEMORY_LIMIT = "2560Mi"


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
        self.gen_sku()
        self.gen_gpu()
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

    @override
    def gen_sku(self):
        sku = self.params.get("sku", "")
        if sku != "":
            self.sku = sku
            return

        if self.gpu_limit > 0:
            sku_from_key = "gpu"
        else:
            sku_from_key = "cpu"
        sku_list = [
            sku_val for sku_val, _ in self.quota.get(sku_from_key, {}).items()
        ]
        if len(sku_list) > 0:
            self.sku = sku_list[0]

    @override
    def gen_gpu(self):
        self.gpu_limit = int(self.params.get("resourcegpu"))

    @override
    def gen_cpu(self):
        self.cpu_request = self.params.get("cpurequest", DEFAULT_CPU_REQUEST)
        self.cpu_limit = self.params.get("cpulimit", DEFAULT_CPU_LIMIT)

    @override
    def gen_memory(self):
        self.memory_request = self.params.get("memoryrequest",
                                              DEFAULT_MEMORY_REQUEST)
        self.memory_limit = self.params.get("memorylimit", DEFAULT_MEMORY_LIMIT)

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

    def get_sku_resource_info(self, resource_type):
        """Returns resource per node and the corresponding schedulable ratio.

        Args:
            resource_type: "gpu", "cpu", or "memory".

        Returns:
            per_node resource, schedulable_ratio
        """
        sku_info = self.metadata.get(resource_type, {}).get(self.sku, {})
        per_node = make_resource(resource_type,
                                 {self.sku: sku_info.get("per_node", 0)})
        schedulable_ratio = float(sku_info.get("schedulable_ratio", 1))
        return per_node, schedulable_ratio

    def gen_cpu_proportional(self):
        gpu_per_node, _ = self.get_sku_resource_info("gpu")
        gpu_per_node = gpu_per_node.scalar(self.sku)

        cpu_per_node, cpu_schedulable_ratio = self.get_sku_resource_info("cpu")
        cpu_schedulable_per_node = cpu_per_node * cpu_schedulable_ratio

        req = cpu_schedulable_per_node * self.gpu_limit / gpu_per_node
        lim = cpu_per_node * self.gpu_limit / gpu_per_node
        self.cpu_request = req.scalar(self.sku)
        self.cpu_limit = lim.scalar(self.sku)

    def gen_memory_proportional(self):
        gpu_per_node, _ = self.get_sku_resource_info("gpu")
        gpu_per_node = gpu_per_node.scalar(self.sku)

        memory_per_node, memory_schedulable_ratio = \
            self.get_sku_resource_info("memory")
        memory_schedulable_per_node = \
            memory_per_node * memory_schedulable_ratio

        req = memory_schedulable_per_node * self.gpu_limit / gpu_per_node
        lim = memory_per_node * self.gpu_limit / gpu_per_node
        self.memory_request = req.scalar(self.sku)
        self.memory_limit = lim.scalar(self.sku)


@JobParams.register_subclass("RegularJob")
class RegularJobParams(JobParams):
    def __init__(self, params, quota, metadata):
        super(RegularJobParams, self).__init__(params, quota, metadata)

    def gen_gpu(self):
        self.gpu_limit = max(0, int(self.params.get("resourcegpu", 0)))

    def gen_cpu(self):
        if self.gpu_limit > 0:
            self.gen_cpu_proportional()
        else:
            self.cpu_request = self.params.get("cpurequest",
                                               DEFAULT_CPU_REQUEST)
            self.cpu_limit = self.params.get("cpulimit", DEFAULT_CPU_LIMIT)

    def gen_memory(self):
        if self.gpu_limit > 0:
            self.gen_memory_proportional()
        else:
            self.memory_request = self.params.get("memoryrequest",
                                                  DEFAULT_MEMORY_REQUEST)
            self.memory_limit = self.params.get("memorylimit",
                                                DEFAULT_MEMORY_LIMIT)


@JobParams.register_subclass("PSDistJob")
class PSDistJobParams(JobParams):
    """Always allocate entire nodes. Ignore resource count requirement from user
    """
    def __init__(self, params, quota, metadata):
        super(PSDistJobParams, self).__init__(params, quota, metadata)

    def gen_gpu(self):
        per_node, _ = self.get_sku_resource_info("gpu")
        self.gpu_limit = per_node.scalar(self.sku)

    def gen_cpu(self):
        per_node, schedulable_ratio = self.get_sku_resource_info("cpu")
        self.cpu_request = (per_node * schedulable_ratio).scalar(self.sku)
        self.cpu_limit = per_node.scalar(self.sku)

    def gen_memory(self):
        per_node, schedulable_ratio = self.get_sku_resource_info("memory")
        self.memory_request = (per_node * schedulable_ratio).scalar(self.sku)
        self.memory_limit = per_node.scalar(self.sku)


@JobParams.register_subclass("InferenceJob")
class InferenceJobParams(JobParams):
    """Always allocate 1 GPU for each worker.

    TODO: inference job should also support CPU workload.
    """
    def __init__(self, params, quota, metadata):
        super(InferenceJobParams, self).__init__(params, quota, metadata)

    def gen_gpu(self):
        self.gpu_limit = 1

    def gen_cpu(self):
        self.gen_cpu_proportional()

    def gen_memory(self):
        self.gen_memory_proportional()


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
