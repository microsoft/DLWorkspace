#!/usr/bin/env python3

import logging

from resource_stat import make_resource

logger = logging.getLogger(__name__)


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
