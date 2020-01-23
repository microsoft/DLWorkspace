#!/usr/bin/env python3

import copy
import numbers
import re


class ResourceStat(object):
    def __init__(self, res=None, unit=None):
        """Constructor for ResourceStat.

        Args:
            res: A dictionary or ResourceStat.
            unit: Unit of the ResourceStat.
        """
        if isinstance(res, ResourceStat):
            res = res.resource
        elif not isinstance(res, dict):
            res = {}

        self.resource_num = {k: int(v) for k, v in res.items()}
        self.unit = unit

    @property
    def resource(self):
        return self.resource_num

    def min_zero(self):
        """Zero all resources in this object with negative value.

        Returns:
            self after zeroing all resources with negative value.
        """
        for k, v in self.resource_num.items():
            self.resource_num[k] = max(0, v)
        return self

    def prune(self):
        """Remove all zero resources in this object

        Returns:
            self after removing all zero resources.
        """
        keys = list(self.resource_num.keys())
        for k in keys:
            if self.resource_num[k] == 0:
                self.resource_num.pop(k)
        return self

    def __repr__(self):
        unit = self.unit if self.unit is not None else ""
        return str({
            k: "%s%s" % (v, unit) for k, v in self.resource_num.items()
        })

    def __add__(self, other):
        if self.__class__ != other.__class__:
            raise ValueError("Incompatible class %s and %s" %
                             (self.__class__, other.__class__))

        if self.unit != other.unit:
            raise ValueError("Incompatible resource type %s and %s" %
                             (self.unit, other.unit))

        tmp = copy.deepcopy(self)
        for k, v in other.resource_num.items():
            if k not in tmp.resource_num:
                tmp.resource_num[k] = 0
            tmp.resource_num[k] += v
        return self.__class__(res=tmp.resource, unit=self.unit)

    def __sub__(self, other):
        if self.__class__ != other.__class__:
            raise ValueError("Incompatible class %s and %s" %
                             (self.__class__, other.__class__))

        if self.unit != other.unit:
            raise ValueError("Incompatible resource type %s and %s" %
                             (self.unit, other.unit))

        tmp = copy.deepcopy(self)
        for k, v in other.resource_num.items():
            if k not in tmp.resource_num:
                tmp.resource_num[k] = 0
            tmp.resource_num[k] -= v
        return self.__class__(res=tmp.resource, unit=self.unit)

    def __iadd__(self, other):
        if self.__class__ != other.__class__:
            raise ValueError("Incompatible class %s and %s" %
                             (self.__class__, other.__class__))

        if self.unit != other.unit:
            raise ValueError("Incompatible resource type %s and %s" %
                             (self.unit, other.unit))

        for k, v in other.resource_num.items():
            if k not in self.resource_num:
                self.resource_num[k] = 0
            self.resource_num[k] += v
        return self

    def __isub__(self, other):
        if self.__class__ != other.__class__:
            raise ValueError("Incompatible class %s and %s" %
                             (self.__class__, other.__class__))

        if self.unit != other.unit:
            raise ValueError("Incompatible resource type %s and %s" %
                             (self.unit, other.unit))

        for k, v in other.resource_num.items():
            if k not in self.resource_num:
                self.resource_num[k] = 0
            self.resource_num[k] -= v
        return self

    def __mul__(self, other):
        if not isinstance(other, numbers.Number):
            raise ValueError("Multiplier is not a number")

        tmp = copy.deepcopy(self)
        for k, v in self.resource_num.items():
            new_v = int(v * float(other))
            tmp.resource_num[k] = new_v
        return self.__class__(res=tmp.resource, unit=self.unit)

    def __imul__(self, other):
        if not isinstance(other, numbers.Number):
            raise ValueError("Multiplier is not a number")

        for k, v in self.resource_num.items():
            new_v = int(v * float(other))
            self.resource_num[k] = new_v

        return self

    def __ge__(self, other):
        if isinstance(other, int):
            for _, v in self.resource_num.items():
                if v < other:
                    return False
            return True
        else:
            if self.__class__ != other.__class__:
                raise ValueError("Incompatible class %s and %s" %
                                 (self.__class__, other.__class__))

            if self.unit != other.unit:
                raise ValueError("Incompatible resource type %s and %s" %
                                 (self.unit, other.unit))

            d1 = self - other
            if d1 >= 0:
                return True

            d1 = d1.min_zero().prune()
            d2 = (other - self).min_zero().prune()

            # Unlabeled resource can be satisfied by any type of resource
            if len(d2.resource_num) == 1 and "" in d2.resource_num:
                remaining_res = 0
                for _, v in d1.resource_num.items():
                    remaining_res += v
                if remaining_res >= d2.resource_num[""]:
                    return True

            return False

    def __prune(self):
        res = {k: v for k, v in self.resource_num.items() if v != 0}
        return self.__class__(res=res, unit=self.unit)

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False

        r_self = self.__prune()
        r_other = other.__prune()

        if r_self.unit != r_other.unit:
            return False

        return r_self.resource_num == r_other.resource_num

    def __ne__(self, other):
        return not self.__eq__(other)


class Gpu(ResourceStat):
    def __init__(self, res=None, unit=None):
        if isinstance(res, Gpu):
            res = res.resource
        elif not isinstance(res, dict):
            res = {}

        # Disallow empty string for gpu type
        res_keys = list(res.keys())
        for k in res_keys:
            if k == "":
                res.pop(k)

        super().__init__(res=res, unit=unit)


class Cpu(ResourceStat):
    def __init__(self, res=None, unit="m"):
        if isinstance(res, Cpu):
            res = res.resource
        elif not isinstance(res, dict):
            res = {}

        for k, v in res.items():
            res[k] = Cpu.to_millicpu(v)

        super().__init__(res=res, unit=unit)

    @staticmethod
    def to_millicpu(data):
        data = str(data).lower()
        number = float(re.findall(r"[-+]?[0-9]*[.]?[0-9]+", data)[0])
        if "m" not in data:
            return number * 1000
        else:
            return number

    @property
    def resource(self):
        return {k: "%sm" % v for k, v in self.resource_num.items()}


class Memory(ResourceStat):
    def __init__(self, res=None, unit="B"):
        if not isinstance(res, Memory):
            if not isinstance(res, dict):
                res = {}
            for k, v in res.items():
                res[k] = Memory.to_byte(v)

        super().__init__(res=res, unit=unit)

    @staticmethod
    def to_byte(data):
        data = str(data).lower()
        number = float(re.findall(r"[-+]?[0-9]*[.]?[0-9]+", data)[0])
        if "ki" in data:
            return number * 2 ** 10
        elif "mi" in data:
            return number * 2 ** 20
        elif "gi" in data:
            return number * 2 ** 30
        elif "ti" in data:
            return number * 2 ** 40
        elif "pi" in data:
            return number * 2 ** 50
        elif "ei" in data:
            return number * 2 ** 60
        elif "k" in data:
            return number * 10 ** 3
        elif "m" in data:
            return number * 10 ** 6
        elif "g" in data:
            return number * 10 ** 9
        elif "t" in data:
            return number * 10 ** 12
        elif "p" in data:
            return number * 10 ** 15
        elif "e" in data:
            return number * 10 ** 18
        else:
            return number
