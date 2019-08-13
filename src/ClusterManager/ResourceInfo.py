import math

class ResourceInfo:
    def __init__(self, res={}):
        self.CategoryToCountMap = {}
        self.BlockedCategories = set()  # not included in serialized form
        for key in res:
            self.CategoryToCountMap[key] = int(res[key])

    def ToSerializable(self):
        return self.CategoryToCountMap

    def TotalCount(self):
        count = 0
        for key in self.CategoryToCountMap:
            count += self.CategoryToCountMap[key]
        return count

    @staticmethod
    def Difference(resInfo1, resInfo2):
        diff = ResourceInfo()
        diff.Add(resInfo1)
        diff.Subtract(resInfo2)
        return diff

    def GetFraction(self, numeratorResInfo, denominatorResInfo):
        fraction = ResourceInfo()
        for key in self.CategoryToCountMap:
            if key in numeratorResInfo.CategoryToCountMap and key in denominatorResInfo.CategoryToCountMap:
                fraction.Add(ResourceInfo({key : \
                    int(math.ceil(float(self.CategoryToCountMap[key]) * numeratorResInfo.CategoryToCountMap[key] / denominatorResInfo.CategoryToCountMap[key]))}))
        return fraction

    def Add(self, otherResourceInfo):
        for key in otherResourceInfo.CategoryToCountMap:
            if key not in self.CategoryToCountMap:
                self.CategoryToCountMap[key] = 0
            self.CategoryToCountMap[key] += otherResourceInfo.CategoryToCountMap[key]
        return self

    def CanSatisfy(self, otherResourceInfo):
        for key in otherResourceInfo.CategoryToCountMap:
            if (otherResourceInfo.CategoryToCountMap[key] > 0) and ((key in self.BlockedCategories) or (key not in self.CategoryToCountMap) \
                or (self.CategoryToCountMap[key] < otherResourceInfo.CategoryToCountMap[key])):
                return False
        return True

    def Subtract(self, otherResourceInfo):
        for key in otherResourceInfo.CategoryToCountMap:
            if otherResourceInfo.CategoryToCountMap[key] > 0:
                self.CategoryToCountMap[key] -= otherResourceInfo.CategoryToCountMap[key]
        return self

    def BlockResourceCategory(self, resourceInfo):
        for key in resourceInfo.CategoryToCountMap:
            self.BlockedCategories.add(key)
        return self

    def UnblockResourceCategory(self, resourceInfo):
        for key in resourceInfo.CategoryToCountMap:
            if key in self.BlockedCategories:
                self.BlockedCategories.remove(key)
        return self


