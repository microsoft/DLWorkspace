#!/usr/bin/env python3

import logging

from resource_stat import Cpu, Memory


logger = logging.getLogger(__name__)


class JobResource(object):
    def __init__(self, params=None, resource=None):
        """Class for job resource requirement.

        Args:
            params: Job params dictionary.
            resource: A dictionary containing "cpu" and "memory".
        """
        self.params = params
        self.resource = resource

        self.cpu = Cpu()
        self.memory = Memory()
        if params is not None:
            self.__set_from_params()
        elif resource is None:
            self.__set_from_resource()

    def __set_from_params(self):
        job_type = self.params.get("jobtrainingtype", "RegularJob")
        sku = self.params.get("sku", "")

        # Default to 1 CPU, 0 memory if not specified
        # Consistent with pod.yaml.template
        cpu_request = self.params.get("cpurequest", 1)
        mem_request = self.params.get("memoryrequest", 0)
        if job_type == "RegularJob":
            self.cpu = Cpu({sku: cpu_request})
            self.memory = Memory({sku: mem_request})
        elif job_type == "PSDistJob":
            # Each ps requires 1 CPU
            num_ps = int(self.params.get("numps", 0))
            self.cpu += Cpu({sku: num_ps})
            self.memory += Memory({sku: num_ps})

            # Add worker CPU requirement
            num_worker = int(self.params.get("numpsworker", 0))
            for i in range(num_worker):
                self.cpu += Cpu({sku: cpu_request})
                self.memory += Memory({sku: mem_request})
        else:
            logger.warning("Unrecognized job type %s", job_type)

    def __set_from_resource(self):
        self.cpu = Cpu(self.resource.get("cpu"))
        self.memory = Memory(self.resource.get("memory"))

    def __ge__(self, other):
        return self.cpu >= other.cpu and self.memory >= other.memory

    def __sub__(self, other):
        pass

    def __isub__(self, other):
        return self
