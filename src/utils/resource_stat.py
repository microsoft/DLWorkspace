#!/usr/bin/env python3

import copy
import logging
import logging.config
import numbers
import re
import math

logger = logging.getLogger(__name__)


def override(func):
    return func


def to_cpu(data):
    data = str(data).lower()
    number = float(re.findall(r"[-+]?[0-9]*[.]?[0-9]+", data)[0])
    if "m" in data:
        return number / 1000.0
    else:
        return number


def millicpu(cpu):
    return "%sm" % (int(cpu) * 1000)


def to_byte(data):
    data = str(data).lower()
    number = float(re.findall(r"[-+]?[0-9]*[.]?[0-9]+", data)[0])
    if "ki" in data:
        return number * 2**10
    elif "mi" in data:
        return number * 2**20
    elif "gi" in data:
        return number * 2**30
    elif "ti" in data:
        return number * 2**40
    elif "pi" in data:
        return number * 2**50
    elif "ei" in data:
        return number * 2**60
    elif "k" in data:
        return number * 10**3
    elif "m" in data:
        return number * 10**6
    elif "g" in data:
        return number * 10**9
    elif "t" in data:
        return number * 10**12
    elif "p" in data:
        return number * 10**15
    elif "e" in data:
        return number * 10**18
    else:
        return number


def mbyte(byte):
    return "%sMi" % int(byte / 2**20)


class ResourceStat(object):
    subclasses = {}

    @classmethod
    def register_subclass(cls, resource_type):
        def decorator(subclass):
            cls.subclasses[resource_type] = subclass
            return subclass

        return decorator

    @classmethod
    def create(cls, resource_type, params):
        if resource_type not in cls.subclasses:
            raise ValueError("Bad resource type %s" % resource_type)
        return cls.subclasses[resource_type](params)

    def __init__(self, params=None):
        """Constructor for ResourceStat.

        Args:
            params: A dictionary or ResourceStat.
        """
        if isinstance(params, ResourceStat):
            params = params.res
        elif not isinstance(params, dict):
            params = {}

        self.res = {k: float(self.convert(v)) for k, v in params.items()}
        self.normalize()

    def to_dict(self):
        return copy.deepcopy(self.res)

    @property
    def floor(self):
        return self.__class__(
            params={k: math.floor(v) for k, v in self.res.items()})

    @property
    def ceil(self):
        return self.__class__(
            params={k: math.ceil(v) for k, v in self.res.items()})

    @override
    def convert(self, data):
        return data

    @override
    def scalar(self, key):
        """Returns resource for the key in human readable format"""
        return self.res.get(key)

    def normalize(self):
        """All resource values should be >= 0."""
        # Lower bound with 0
        for k, v in self.res.items():
            self.res[k] = max(0, v)

    def __repr__(self):
        return str(self.to_dict())

    def __add__(self, other):
        if self.__class__ != other.__class__:
            raise ValueError("Incompatible class %s and %s" %
                             (self.__class__, other.__class__))

        result = copy.deepcopy(self)
        for k, v in other.res.items():
            if k not in result.res:
                result.res[k] = 0
            result.res[k] += v

        result.normalize()
        return result

    def __iadd__(self, other):
        if self.__class__ != other.__class__:
            raise ValueError("Incompatible class %s and %s" %
                             (self.__class__, other.__class__))

        for k, v in other.res.items():
            if k not in self.res:
                self.res[k] = 0
            self.res[k] += v

        self.normalize()
        return self

    def __sub__(self, other):
        if self.__class__ != other.__class__:
            raise ValueError("Incompatible class %s and %s" %
                             (self.__class__, other.__class__))

        result = copy.deepcopy(self)
        for k, v in other.res.items():
            if k not in result.res:
                result.res[k] = 0
            result.res[k] -= v

        result.normalize()
        return result

    def __isub__(self, other):
        if self.__class__ != other.__class__:
            raise ValueError("Incompatible class %s and %s" %
                             (self.__class__, other.__class__))

        for k, v in other.res.items():
            if k not in self.res:
                self.res[k] = 0
            self.res[k] -= v

        self.normalize()
        return self

    def __mul__(self, other):
        if isinstance(other, numbers.Number):
            result = copy.deepcopy(self)
            for k, v in result.res.items():
                result.res[k] = v * other

            result.normalize()
            return result
        else:
            if self.__class__ != other.__class__:
                raise ValueError("Incompatible class %s and %s" %
                                 (self.__class__, other.__class__))

            # Pairwise multiplication
            self_keys = set(self.res.keys())
            other_keys = set(other.res.keys())
            all_keys = self_keys.union(other_keys)

            result = self.__class__(params=None)
            for k in all_keys:
                self_v = self.res.get(k, 0)
                other_v = other.res.get(k, 0)
                result.res[k] = self_v * other_v

            result.normalize()
            return result

    def __imul__(self, other):
        if isinstance(other, numbers.Number):
            for k, v in self.res.items():
                self.res[k] = v * other

            self.normalize()
            return self
        else:
            if self.__class__ != other.__class__:
                raise ValueError("Incompatible class %s and %s" %
                                 (self.__class__, other.__class__))

            # Pairwise multiplication
            self_keys = set(self.res.keys())
            other_keys = set(other.res.keys())
            all_keys = self_keys.union(other_keys)

            for k in all_keys:
                self_v = self.res.get(k, 0)
                other_v = other.res.get(k, 0)
                self.res[k] = self_v * other_v

            self.normalize()
            return self

    def __truediv__(self, other):
        if isinstance(other, numbers.Number):
            result = copy.deepcopy(self)
            for k, v in self.res.items():
                # Division by zero gives zero
                if other == 0:
                    logger.warning("Div by 0 by other %s. Set to 0.", other)
                    result.res[k] = 0
                else:
                    result.res[k] = v / other

            result.normalize()
            return result
        else:
            if self.__class__ != other.__class__:
                raise ValueError("Incompatible class %s and %s" %
                                 (self.__class__, other.__class__))

            # Pairwise division
            self_keys = set(self.res.keys())
            other_keys = set(other.res.keys())
            all_keys = self_keys.union(other_keys)

            result = self.__class__()
            for k in all_keys:
                self_v = self.res.get(k, 0)
                other_v = other.res.get(k, 0)
                # Division by zero gives zero
                if other_v == 0:
                    logger.warning(
                        "Div by 0 at key %s by value %s in other "
                        "%s. Set to 0.", k, other_v, other)
                    result.res[k] = 0
                else:
                    result.res[k] = self_v / other_v

            result.normalize()
            return result

    def __idiv__(self, other):
        if isinstance(other, numbers.Number):
            for k, v in self.res.items():
                # Division by zero gives zero
                if other == 0:
                    logger.warning("Div by 0 by other %s. Set to 0.", other)
                    self.res[k] = 0
                else:
                    self.res[k] = v / other

            self.normalize()
            return self
        else:
            if self.__class__ != other.__class__:
                raise ValueError("Incompatible class %s and %s" %
                                 (self.__class__, other.__class__))

            # Pairwise division
            self_keys = set(self.res.keys())
            other_keys = set(other.res.keys())
            all_keys = self_keys.union(other_keys)

            for k in all_keys:
                self_v = self.res.get(k, 0)
                other_v = other.res.get(k, 0)
                if other_v == 0:
                    logger.warning(
                        "Div by 0 at key %s by value %s in other "
                        "%s. Set to 0.", k, other_v, other)
                    self.res[k] = 0
                else:
                    self.res[k] = self_v / other_v

            self.normalize()
            return self

    def __ge__(self, other):
        if isinstance(other, numbers.Number):
            for _, v in self.res.items():
                if v < other:
                    return False
            return True
        else:
            if self.__class__ != other.__class__:
                raise ValueError("Incompatible class %s and %s" %
                                 (self.__class__, other.__class__))

            # Pairwise compare
            self_keys = set(self.res.keys())
            other_keys = set(other.res.keys())
            all_keys = self_keys.union(other_keys)

            for k in all_keys:
                self_v = self.res.get(k, 0)
                other_v = other.res.get(k, 0)
                if self_v < other_v:
                    return False
            return True

    def __le__(self, other):
        if isinstance(other, numbers.Number):
            for _, v in self.res.items():
                if v > other:
                    return False
            return True
        else:
            if self.__class__ != other.__class__:
                raise ValueError("Incompatible class %s and %s" %
                                 (self.__class__, other.__class__))

            # Pairwise compare
            self_keys = set(self.res.keys())
            other_keys = set(other.res.keys())
            all_keys = self_keys.union(other_keys)

            for k in all_keys:
                self_v = self.res.get(k, 0)
                other_v = other.res.get(k, 0)
                if self_v > other_v:
                    return False
            return True

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False

        r_self = copy.deepcopy(self)
        r_self.normalize()
        r_other = copy.deepcopy(other)
        r_other.normalize()

        # Pairwise compare
        self_keys = set(self.res.keys())
        other_keys = set(other.res.keys())
        all_keys = self_keys.union(other_keys)

        for k in all_keys:
            self_v = self.res.get(k, 0)
            other_v = other.res.get(k, 0)
            if self_v != other_v:
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)


@ResourceStat.register_subclass("cpu")
class Cpu(ResourceStat):
    def convert(self, data):
        return to_cpu(data)

    @override
    def scalar(self, key):
        val = self.res.get(key)
        if val is None:
            return None
        return millicpu(val)


@ResourceStat.register_subclass("memory")
class Memory(ResourceStat):
    def convert(self, data):
        return to_byte(data)

    @override
    def scalar(self, key):
        val = self.res.get(key)
        if val is None:
            return None
        return mbyte(val)


@ResourceStat.register_subclass("gpu")
class Gpu(ResourceStat):
    pass


@ResourceStat.register_subclass("gpu_memory")
class GpuMemory(ResourceStat):
    def convert(self, data):
        return to_byte(data)

    @override
    def scalar(self, key):
        val = self.res.get(key)
        if val is None:
            return None
        return mbyte(val)


def make_resource(resource_type, params=None):
    resource = None
    try:
        if resource_type is None:
            resource = ResourceStat(params=params)
        else:
            resource = ResourceStat.create(resource_type, params)
    except ValueError:
        logger.exception("Bad resource type %s", params, exc_info=True)
    except Exception:
        logger.exception(
            "Exception in creating resource of type %s with "
            "params %s",
            resource_type,
            params,
            exc_info=True)
    return resource


def dictionarize(d):
    if isinstance(d, ResourceStat):
        return d.to_dict()
    elif isinstance(d, list):
        new_d = []
        for item in d:
            new_d.append(dictionarize(item))
        return new_d
    elif isinstance(d, dict):
        for k in d:
            d[k] = dictionarize(d[k])
        return d
    else:
        return d
