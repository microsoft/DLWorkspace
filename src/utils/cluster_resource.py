#!/usr/bin/env python3

import copy
import logging
import numbers

from resource_stat import Cpu, Memory, Gpu, GpuMemory


logger = logging.getLogger(__name__)


class ClusterResource(object):
    def __init__(self, params=None, resource=None):
        """Class for job resource requirement.

        Args:
            params: Job params dictionary.
            resource: A dictionary containing "cpu" and "memory", i.e.
                resource = {
                    "cpu": {
                        "r1": ...
                    },
                    "memory": {
                        "r1": ...
                    },
                    "gpu": {
                        "r1": ...
                    },
                    "gpu_memory": {
                        "r1": ...
                    },
                }
        """
        self.params = params
        self.resource = resource

        self.cpu = Cpu()
        self.memory = Memory()
        self.gpu = Gpu()
        self.gpu_memory = GpuMemory()
        if self.params is not None:
            self.__set_from_params()
        elif self.resource is not None:
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
            # Each ps reserves 1 CPU and 0 memory
            num_ps = int(self.params.get("numps", 0))
            self.cpu += Cpu({sku: num_ps})
            self.memory += Memory({sku: 0})

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

    def floor(self):
        resource = {
            "cpu": self.cpu.floor,
            "memory": self.memory.floor,
            "gpu": self.gpu.floor,
            "gpu_memory": self.gpu_memory.floor,
        }
        return self.__class__(resource=resource)

    def ceil(self):
        resource = {
            "cpu": self.cpu.ceil,
            "memory": self.memory.ceil,
            "gpu": self.gpu.ceil,
            "gpu_memory": self.gpu_memory.ceil,
        }
        return self.__class__(resource=resource)

    def min_zero(self):
        self.cpu.min_zero()
        self.memory.min_zero()
        self.gpu.min_zero()
        self.gpu_memory.min_zero()
        return self

    def prune(self):
        self.cpu.prune()
        self.memory.prune()
        self.gpu.prune()
        self.gpu_memory.prune()
        return self

    def __repr__(self):
        return "cpu: %s. memory: %s. gpu: %s. gpu_memory: %s" % (
            self.cpu,
            self.memory,
            self.gpu,
            self.gpu_memory,
        )

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
        return self.cpu == other.cpu and \
            self.memory == other.memory and \
            self.gpu == other.gpu and \
            self.gpu_memory == other.gpu_memory

    def __ge__(self, other):
        if self.__class__ != other.__class__:
            raise ValueError("Incompatible class %s and %s" %
                             (self.__class__, other.__class__))

        return self.cpu >= other.cpu and \
            self.memory >= other.memory and \
            self.gpu >= other.gpu and \
            self.gpu_memory >= other.gpu_memory

    def __add__(self, other):
        if self.__class__ != other.__class__:
            raise ValueError("Incompatible class %s and %s" %
                             (self.__class__, other.__class__))

        result = copy.deepcopy(self)
        result.cpu += other.cpu
        result.memory += other.memory
        result.gpu += other.gpu
        result.gpu_memory += other.gpu_memory
        return result

    def __iadd__(self, other):
        if self.__class__ != other.__class__:
            raise ValueError("Incompatible class %s and %s" %
                             (self.__class__, other.__class__))

        self.cpu += other.cpu
        self.memory += other.memory
        self.gpu += other.gpu
        self.gpu_memory += other.gpu_memory
        return self

    def __sub__(self, other):
        if self.__class__ != other.__class__:
            raise ValueError("Incompatible class %s and %s" %
                             (self.__class__, other.__class__))

        result = copy.deepcopy(self)
        result.cpu -= other.cpu
        result.memory -= other.memory
        result.gpu -= other.gpu
        result.gpu_memory -= other.gpu_memory
        return result

    def __isub__(self, other):
        if self.__class__ != other.__class__:
            raise ValueError("Incompatible class %s and %s" %
                             (self.__class__, other.__class__))

        self.cpu -= other.cpu
        self.memory -= other.memory
        self.gpu -= other.gpu
        self.gpu_memory -= other.gpu_memory
        return self

    def __mul__(self, other):
        result = copy.deepcopy(self)
        if isinstance(other, numbers.Number):
            result.cpu *= other
            result.memory *= other
            result.gpu *= other
            result.gpu_memory *= other
        elif isinstance(other, ClusterResource):
            result.cpu *= other.cpu
            result.memory *= other.memory
            result.gpu *= other.gpu
            result.gpu_memory *= other.gpu_memory
        else:
            raise TypeError("Incompatible type %s and %s" %
                            (self.__class__, other.__class__))
        return result

    def __imul__(self, other):
        if isinstance(other, numbers.Number):
            self.cpu *= other
            self.memory *= other
            self.gpu *= other
            self.gpu_memory *= other
        elif isinstance(other, ClusterResource):
            self.cpu *= other.cpu
            self.memory *= other.memory
            self.gpu *= other.gpu
            self.gpu_memory *= other.gpu_memory
        else:
            raise TypeError("Incompatible type %s and %s" %
                            (self.__class__, other.__class__))
        return self

    def __truediv__(self, other):
        result = copy.deepcopy(self)
        if isinstance(other, numbers.Number):
            result.cpu /= other
            result.memory /= other
            result.gpu /= other
            result.gpu_memory /= other
        elif isinstance(other, ClusterResource):
            result.cpu /= other.cpu
            result.memory /= other.memory
            result.gpu /= other.gpu
            result.gpu_memory /= other.gpu_memory
        else:
            raise TypeError("Incompatible type %s and %s" %
                            (self.__class__, other.__class__))
        return result

    def __idiv__(self, other):
        if isinstance(other, numbers.Number):
            self.cpu /= other
            self.memory /= other
            self.gpu /= other
            self.gpu_memory /= other
        elif isinstance(other, ClusterResource):
            self.cpu /= other.cpu
            self.memory /= other.memory
            self.gpu /= other.gpu
            self.gpu_memory /= other.gpu_memory
        else:
            raise TypeError("Incompatible type %s and %s" %
                            (self.__class__, other.__class__))
        return self
