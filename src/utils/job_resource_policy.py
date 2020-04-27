#!/usr/bin/env python3

import logging

from common import override
from resource_stat import make_resource

logger = logging.getLogger(__name__)


class JobResourcePolicy(object):
    def __init__(self,
                 sku=None,
                 gpu_limit=0,
                 config=None,
                 quota=None,
                 metadata=None):
        self.sku = sku
        self.gpu_limit = int(gpu_limit)
        self.config = config
        self.quota = quota
        self.metadata = metadata

        # Backward compatible: use 1 core to reserve
        self.sys_cpu_request = "1000m"

        # Backward compatible: allow using up cpu on node
        cpu_per_node, _ = self.get_sku_resource_info("cpu")
        self.sys_cpu_limit = cpu_per_node.scalar(self.sku)

        # Backward compatible: use 0 memory to reserve
        self.sys_memory_request = "0Mi"

        # Backward compatible: allow using up memory on node
        memory_per_node, _ = self.get_sku_resource_info("memory")
        self.sys_memory_limit = memory_per_node.scalar(self.sku)

    @override
    @property
    def default_cpu_request(self):
        return self.config.get("default_cpurequest", self.sys_cpu_request)

    @override
    @property
    def default_cpu_limit(self):
        return self.config.get("default_cpulimit", self.sys_cpu_limit)

    @override
    @property
    def default_memory_request(self):
        return self.config.get("default_memoryrequest", self.sys_memory_request)

    @override
    @property
    def default_memory_limit(self):
        return self.config.get("default_memorylimit", self.sys_memory_limit)

    def get_sku_resource_info(self, r_type):
        info = self.metadata.get(r_type, {}).get(self.sku, {})
        per_node = make_resource(r_type, {self.sku: info.get("per_node", 0)})
        schedulable_ratio = float(info.get("schedulable_ratio", 1))
        return per_node, schedulable_ratio


class GpuProportionalPolicy(JobResourcePolicy):
    @property
    def default_cpu_request(self):
        if self.gpu_limit == 0:
            return super(GpuProportionalPolicy, self).default_cpu_request
        else:
            return self.get_request_proportional("cpu")

    @property
    def default_cpu_limit(self):
        if self.gpu_limit == 0:
            return super(GpuProportionalPolicy, self).default_cpu_limit
        else:
            return self.get_limit_proportional("cpu")

    @property
    def default_memory_request(self):
        if self.gpu_limit == 0:
            return super(GpuProportionalPolicy, self).default_memory_request
        else:
            return self.get_request_proportional("memory")

    @property
    def default_memory_limit(self):
        if self.gpu_limit == 0:
            return super(GpuProportionalPolicy, self).default_memory_limit
        else:
            return self.get_limit_proportional("memory")

    def get_request_proportional(self, r_type):
        gpu_per_node, _ = self.get_sku_resource_info("gpu")
        gpu_per_node = gpu_per_node.scalar(self.sku)

        per_node, schedulable_ratio = self.get_sku_resource_info(r_type)
        schedulable_per_node = per_node * schedulable_ratio

        request = schedulable_per_node * self.gpu_limit / gpu_per_node
        return request.scalar(self.sku)

    def get_limit_proportional(self, r_type):
        gpu_per_node, _ = self.get_sku_resource_info("gpu")
        gpu_per_node = gpu_per_node.scalar(self.sku)

        per_node, _ = self.get_sku_resource_info(r_type)

        limit = per_node * self.gpu_limit / gpu_per_node
        return limit.scalar(self.sku)


JOB_RESOURCE_POLICY_MAPPING = {
    "default": JobResourcePolicy,
    "gpu_proportional": GpuProportionalPolicy,
}


def make_job_resource_policy(sku, gpu_limit, config, quota, metadata):
    policy = None
    try:
        policy_type = config.get("job_resource_policy", "default")
        policy = JOB_RESOURCE_POLICY_MAPPING[policy_type](sku, gpu_limit,
                                                          config, quota,
                                                          metadata)
    except:
        logger.exception(
            "Failed to make job resource policy with sku %s, "
            "gpu_limit %s, config %s, quota %s, metadata %s", sku, gpu_limit,
            config, quota, metadata)
    return policy
