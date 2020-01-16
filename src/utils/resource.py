#!/usr/bin/env python3


class Resource(object):
    def __init__(self, res=None):
        self.CategoryToCountMap = {}
        if res is None:
            res = {}

    def __repr__(self):
        return str(self.CategoryToCountMap)

    def __add__(self, other):
        return self.CategoryToCountMap


class Gpu(Resource):
    def __init__(self):
        Resource.__init__(self)


class Cpu(Resource):
    def __init__(self):
        Resource.__init__(self)


class Memory(Resource):
    def __init__(self):
        Resource.__init__(self)
