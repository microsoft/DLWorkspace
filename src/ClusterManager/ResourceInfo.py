#!/usr/bin/env python3

import math


class ResourceInfo:
    def __init__(self, res={}):
        self.CategoryToCountMap = {}
        for key in res:
            self.CategoryToCountMap[key] = int(res[key])

    def ToSerializable(self):
        return self.CategoryToCountMap

    @staticmethod
    def Difference(resInfo1, resInfo2):
        diff = ResourceInfo()
        diff.Add(resInfo1)
        diff.Subtract(resInfo2)
        return diff

    @staticmethod
    def DifferenceMinZero(resInfo1, resInfo2):
        diff = ResourceInfo()
        diff.Add(resInfo1)
        diff.SubtractMinZero(resInfo2)
        return diff

    def GetFraction(self, numeratorResInfo, denominatorResInfo):
        fraction = ResourceInfo()
        for key in self.CategoryToCountMap:
            if key in numeratorResInfo.CategoryToCountMap and key in denominatorResInfo.CategoryToCountMap:
                fraction.Add(
                    ResourceInfo({
                        key:
                            int(
                                math.ceil(
                                    float(self.CategoryToCountMap[key]) *
                                    numeratorResInfo.CategoryToCountMap[key] /
                                    denominatorResInfo.CategoryToCountMap[key]))
                    }))
        return fraction

    def Add(self, otherResourceInfo):
        for key in otherResourceInfo.CategoryToCountMap:
            if key not in self.CategoryToCountMap:
                self.CategoryToCountMap[key] = 0
            self.CategoryToCountMap[
                key] += otherResourceInfo.CategoryToCountMap[key]
        return self

    def CanSatisfy(self, otherResourceInfo):
        for key in otherResourceInfo.CategoryToCountMap:
            if (otherResourceInfo.CategoryToCountMap[key] > 0) and (
                (key not in self.CategoryToCountMap) or
                (self.CategoryToCountMap[key] <
                 otherResourceInfo.CategoryToCountMap[key])):
                return False
        return True

    def Subtract(self, otherResourceInfo):
        for key in otherResourceInfo.CategoryToCountMap:
            if otherResourceInfo.CategoryToCountMap[key] > 0:
                self.CategoryToCountMap[
                    key] -= otherResourceInfo.CategoryToCountMap[key]
        return self

    def SubtractMinZero(self, otherResourceInfo):
        for key in otherResourceInfo.CategoryToCountMap:
            if otherResourceInfo.CategoryToCountMap[key] > 0:
                self.CategoryToCountMap[
                    key] -= otherResourceInfo.CategoryToCountMap[key]
            if key in self.CategoryToCountMap and self.CategoryToCountMap[
                    key] < 0:
                self.CategoryToCountMap[key] = 0
        return self

    def __repr__(self):
        return str(self.CategoryToCountMap)
