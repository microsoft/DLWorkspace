#!/usr/bin/env python3

import copy
import logging
import numbers

from resource_stat import make_resource, dictionarize

logger = logging.getLogger(__name__)


class ClusterResource(object):
    def __init__(self, params=None):
        """Class for job resource requirement.

        Args:
            params: A dictionary containing "cpu", "memory", "gpu",
                "gpu_memory", i.e.
                paras = {
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
        self.cpu = None
        self.memory = None
        self.gpu = None
        self.gpu_memory = None

        if params is None:
            params = {}

        for r_type in self.__dict__:
            self.__dict__[r_type] = make_resource(r_type, params.get(r_type))

    def to_dict(self):
        return dictionarize(copy.deepcopy(self.__dict__))

    def has_empty_gpu_or_cpu(self):
        for r_type in self.__dict__:
            if r_type == "gpu" or r_type == "cpu":
                param = self.__dict__[r_type]
                for k, v in param.res.items():
                    if v == 0:
                        return True

        return False

    @property
    def floor(self):
        params = {
            r_type: self.__dict__[r_type].floor.to_dict()
            for r_type in self.__dict__
        }
        return self.__class__(params=params)

    @property
    def ceil(self):
        params = {
            r_type: self.__dict__[r_type].ceil.to_dict()
            for r_type in self.__dict__
        }
        return self.__class__(params=params)

    def __repr__(self):
        return str(self.to_dict())

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False

        for r_type in self.__dict__:
            if self.__dict__[r_type] != other.__dict__[r_type]:
                return False

        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __ge__(self, other):
        if self.__class__ != other.__class__:
            raise ValueError("Incompatible class %s and %s" %
                             (self.__class__, other.__class__))

        for r_type in self.__dict__:
            if not (self.__dict__[r_type] >= other.__dict__[r_type]):
                return False

        return True

    def __add__(self, other):
        if self.__class__ != other.__class__:
            raise ValueError("Incompatible class %s and %s" %
                             (self.__class__, other.__class__))

        result = copy.deepcopy(self)
        for r_type in result.__dict__:
            result.__dict__[r_type] += other.__dict__[r_type]
        return result

    def __iadd__(self, other):
        if self.__class__ != other.__class__:
            raise ValueError("Incompatible class %s and %s" %
                             (self.__class__, other.__class__))

        for r_type in self.__dict__:
            self.__dict__[r_type] += other.__dict__[r_type]
        return self

    def __sub__(self, other):
        if self.__class__ != other.__class__:
            raise ValueError("Incompatible class %s and %s" %
                             (self.__class__, other.__class__))

        result = copy.deepcopy(self)
        for r_type in result.__dict__:
            result.__dict__[r_type] -= other.__dict__[r_type]
        return result

    def __isub__(self, other):
        if self.__class__ != other.__class__:
            raise ValueError("Incompatible class %s and %s" %
                             (self.__class__, other.__class__))

        for r_type in self.__dict__:
            self.__dict__[r_type] -= other.__dict__[r_type]
        return self

    def __mul__(self, other):
        result = copy.deepcopy(self)
        if isinstance(other, numbers.Number):
            for r_type in result.__dict__:
                result.__dict__[r_type] *= other
        elif isinstance(other, ClusterResource):
            for r_type in result.__dict__:
                result.__dict__[r_type] *= other.__dict__[r_type]
        else:
            raise TypeError("Incompatible type %s and %s" %
                            (self.__class__, other.__class__))
        return result

    def __imul__(self, other):
        if isinstance(other, numbers.Number):
            for r_type in self.__dict__:
                self.__dict__[r_type] *= other
        elif isinstance(other, ClusterResource):
            for r_type in self.__dict__:
                self.__dict__[r_type] *= other.__dict__[r_type]
        else:
            raise TypeError("Incompatible type %s and %s" %
                            (self.__class__, other.__class__))
        return self

    def __truediv__(self, other):
        result = copy.deepcopy(self)
        if isinstance(other, numbers.Number):
            for r_type in result.__dict__:
                result.__dict__[r_type] /= other
        elif isinstance(other, ClusterResource):
            for r_type in result.__dict__:
                result.__dict__[r_type] /= other.__dict__[r_type]
        else:
            raise TypeError("Incompatible type %s and %s" %
                            (self.__class__, other.__class__))
        return result

    def __idiv__(self, other):
        if isinstance(other, numbers.Number):
            for r_type in self.__dict__:
                self.__dict__[r_type] /= other
        elif isinstance(other, ClusterResource):
            for r_type in self.__dict__:
                self.__dict__[r_type] /= other.__dict__[r_type]
        else:
            raise TypeError("Incompatible type %s and %s" %
                            (self.__class__, other.__class__))
        return self
