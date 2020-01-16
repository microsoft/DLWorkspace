#!/usr/bin/env python3

import copy


class ResourceStat(object):
    def __init__(self, res=None, unit=None):
        if res is None:
            res = {}
        elif isinstance(res, ResourceStat):
            res = res.resource
        elif not isinstance(res, dict):
            res = {}
        self.resource = {k: int(v) for k, v in res.items()}
        self.unit = unit

    def min_zero(self):
        """Zero all resources in this object with negative value.

        Returns:
            self after zeroing all resources with negative value.
        """
        for k, v in self.resource.items():
            self.resource[k] = max(0, v)
        return self

    def prune(self):
        """Remove all zero resources in this object

        Returns:
            self after removing all zero resources.
        """
        keys = list(self.resource.keys())
        for k in keys:
            if self.resource[k] == 0:
                self.resource.pop(k)
        return self

    def __repr__(self):
        unit = ""
        if self.unit is not None:
            unit = "(%s)" % self.unit
        return "%s %s" % (self.resource, unit)

    def __add__(self, other):
        if self.unit != other.unit:
            raise ValueError("Incompatible resource type %s and %s" %
                             (self.unit, other.unit))

        res = copy.deepcopy(self.resource)
        for k, v in other.resource.items():
            if k not in res:
                res[k] = 0
            res[k] += v
        return ResourceStat(res=res, unit=self.unit)

    def __sub__(self, other):
        if self.unit != other.unit:
            raise ValueError("Incompatible resource type %s and %s" %
                             (self.unit, other.unit))

        res = copy.deepcopy(self.resource)
        for k, v in other.resource.items():
            if k not in res:
                res[k] = 0
            res[k] -= v
        return ResourceStat(res=res, unit=self.unit)

    def __iadd__(self, other):
        if self.unit != other.unit:
            raise ValueError("Incompatible resource type %s and %s" %
                             (self.unit, other.unit))

        for k, v in other.resource.items():
            if k not in self.resource:
                self.resource[k] = 0
            self.resource[k] += v
        return self

    def __isub__(self, other):
        if self.unit != other.unit:
            raise ValueError("Incompatible resource type %s and %s" %
                             (self.unit, other.unit))

        for k, v in other.resource.items():
            if k not in self.resource:
                self.resource[k] = 0
            self.resource[k] -= v
        return self

    def __ge__(self, other):
        if isinstance(other, int):
            for k, v in self.resource.items():
                if v < other:
                    return False
            return True
        else:
            if self.unit != other.unit:
                raise ValueError("Incompatible resource type %s and %s" %
                                 (self.unit, other.unit))

            for k, v in other.resource.items():
                if k not in self.resource:
                    v_self = 0
                else:
                    v_self = self.resource[k]

                if v_self < v:
                    return False
            return True

    def __prune(self):
        res = {k: v for k, v in self.resource.items() if v != 0}
        unit = self.unit
        return ResourceStat(res=res, unit=unit)

    def __eq__(self, other):
        if not isinstance(other, ResourceStat):
            return False

        r_self = self.__prune()
        r_other = other.__prune()

        if r_self.unit != r_other.unit:
            return False

        return r_self.resource == r_other.resource

    def __ne__(self, other):
        return not self.__eq__(other)


class Gpu(ResourceStat):
    def __init__(self, res=None):
        if res is None:
            res = {}
        elif isinstance(res, Gpu):
            res = res.resource
        elif not isinstance(res, dict):
            res = {}

        # Disallow empty string for gpu type
        res_keys = list(res.keys())
        for k in res_keys:
            if k == "":
                res.pop(k)

        ResourceStat.__init__(self, res=res)


class Cpu(ResourceStat):
    def __init__(self, res=None):
        ResourceStat.__init__(self, res=res)


class Memory(ResourceStat):
    def __init__(self, res=None):
        ResourceStat.__init__(self, res=res, unit="Ki")
