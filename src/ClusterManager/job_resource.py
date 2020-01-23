#!/usr/bin/env python3

import copy
import logging
import numbers

from resource_stat import Cpu, Memory


logger = logging.getLogger(__name__)


class JobResource(object):
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
                    }
        """
        self.params = params
        self.resource = resource

        self.cpu = Cpu()
        self.memory = Memory()
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

    def __repr__(self):
        return "cpu: %s. memory: %s." % (self.cpu, self.memory)

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
        return self.cpu == other.cpu and self.memory == other.memory

    def __ge__(self, other):
        if self.__class__ != other.__class__:
            raise ValueError("Incompatible class %s and %s" %
                             (self.__class__, other.__class__))

        return self.cpu >= other.cpu and self.memory >= other.memory

    def __add__(self, other):
        if self.__class__ != other.__class__:
            raise ValueError("Incompatible class %s and %s" %
                             (self.__class__, other.__class__))

        ret = copy.deepcopy(self)
        ret.cpu += other.cpu
        ret.memory += other.memory
        return ret

    def __iadd__(self, other):
        if self.__class__ != other.__class__:
            raise ValueError("Incompatible class %s and %s" %
                             (self.__class__, other.__class__))

        self.cpu += other.cpu
        self.memory += other.memory
        return self

    def __sub__(self, other):
        if self.__class__ != other.__class__:
            raise ValueError("Incompatible class %s and %s" %
                             (self.__class__, other.__class__))

        ret = copy.deepcopy(self)
        ret.cpu -= other.cpu
        ret.memory -= other.memory
        return ret

    def __isub__(self, other):
        if self.__class__ != other.__class__:
            raise ValueError("Incompatible class %s and %s" %
                             (self.__class__, other.__class__))

        self.cpu -= other.cpu
        self.memory -= other.memory
        return self

    def __mul__(self, other):
        if not isinstance(other, numbers.Number):
            raise ValueError("Multiplier is not a number")

        ret = copy.deepcopy(self)
        ret.cpu *= other
        ret.memory *= other
        return ret

    def __imul__(self, other):
        if not isinstance(other, numbers.Number):
            raise ValueError("Multiplier is not a number")

        self.cpu *= other
        self.memory *= other
        return self
