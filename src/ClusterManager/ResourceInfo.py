class ResourceInfo:
    def __init__(self, tag = "", res = {}):
        self.CategoryToCountMap = {}
        self.BlockedCategories = set()
        for key in res:
            self.CategoryToCountMap[tag + "_" + key] = int(res[key])

    @classmethod
    def FromTypeAndCount(cls, tag, gpuType, gpucount):
        resources = {}
        resources[gpuType] = gpucount
        return cls(tag, resources)

    def Add(self, otherResourceInfo):
        for key in otherResourceInfo.CategoryToCountMap:
            if key not in self.CategoryToCountMap:
                self.CategoryToCountMap[key] = 0
            self.CategoryToCountMap[key] += otherResourceInfo.CategoryToCountMap[key]

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

    def BlockResourceCategory(self, resourceInfo):
        for key in resourceInfo.CategoryToCountMap:
            self.BlockedCategories.add(key)

    def UnblockResourceCategory(self, resourceInfo):
        for key in resourceInfo.CategoryToCountMap:
            if key in self.BlockedCategories:
                self.BlockedCategories.remove(key)