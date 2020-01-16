#!/usr/bin/env python3

from unittest import TestCase
from resource_stat import ResourceStat, Gpu, Cpu, Memory


class TestResource(TestCase):
    def init_with_class(self):
        self.cls_name = ResourceStat

    def setUp(self):
        self.init_with_class()
        self.a = self.cls_name(res={"r1": 3, "r2": 5, "r3": 0})
        self.b = self.cls_name(res={"r1": 3, "r2": 6})
        self.c = self.cls_name(res={"r2": 9})
        self.d = self.cls_name(res={"r4": 1})

        self.neg = self.cls_name(res={"r1": -1})
        self.zero = self.cls_name()
        self.r_with_unit = ResourceStat(res={"r1": 1}, unit="u")

    def test_min_zero_and_prune(self):
        t1 = self.cls_name(res={"r1": 0})
        self.neg.min_zero()
        self.assertEqual(t1, self.neg)

        t2 = self.cls_name()
        self.neg.prune()
        self.assertEqual(t2, self.neg)

    def test_repr(self):
        t = "{'r2': 9} "
        if self.c.unit is not None:
            t += "(%s)" % self.c.unit
        self.assertEqual(t, repr(self.c))

        t = "{'r1': 1} (u)"
        self.assertEqual(t, repr(self.r_with_unit))

    def test_add(self):
        # a + b + c + d + neg
        t1 = self.cls_name(res={"r1": 6, "r2": 11, "r3": 0})
        o1 = self.a + self.b
        self.assertEqual(t1, o1)

        t2 = self.cls_name(res={"r1": 6, "r2": 20, "r3": 0})
        o2 = o1 + self.c
        self.assertEqual(t2, o2)

        t3 = self.cls_name(res={"r1": 6, "r2": 20, "r3": 0, "r4": 1})
        o3 = o2 + self.d
        self.assertEqual(t3, o3)

        t4 = self.cls_name(res={"r1": 5, "r2": 20, "r3": 0, "r4": 1})
        o4 = o3 + self.neg
        self.assertEqual(t4, o4)

        # incompatible type
        try:
            o4 + self.r_with_unit
            self.assertTrue(False, "Should've crashed")
        except ValueError:
            self.assertTrue(True)

    def test_sub(self):
        # a - b - c - d - neg
        t1 = self.cls_name(res={"r1": 0, "r2": -1, "r3": 0})
        o1 = self.a - self.b
        self.assertEqual(t1, o1)

        t2 = self.cls_name(res={"r1": 0, "r2": -10, "r3": 0})
        o2 = o1 - self.c
        self.assertEqual(t2, o2)

        t3 = self.cls_name(res={"r1": 0, "r2": -10, "r3": 0, "r4": -1})
        o3 = o2 - self.d
        self.assertEqual(t3, o3)

        t4 = self.cls_name(res={"r1": 1, "r2": -10, "r3": 0, "r4": -1})
        o4 = o3 - self.neg
        self.assertEqual(t4, o4)

        # incompatible type
        try:
            o4 - self.r_with_unit
            self.assertTrue(False, "Should've crashed")
        except ValueError:
            self.assertTrue(True)

    def test_iadd(self):
        # a += b
        # a += c
        # a += d
        # a += d
        # a += neg
        t1 = self.cls_name(res={"r1": 6, "r2": 11, "r3": 0})
        self.a += self.b
        self.assertEqual(t1, self.a)

        t2 = self.cls_name(res={"r1": 6, "r2": 20, "r3": 0})
        self.a += self.c
        self.assertEqual(t2, self.a)

        t3 = self.cls_name(res={"r1": 6, "r2": 20, "r3": 0, "r4": 1})
        self.a += self.d
        self.assertEqual(t3, self.a)

        t4 = self.cls_name(res={"r1": 5, "r2": 20, "r3": 0, "r4": 1})
        self.a += self.neg
        self.assertEqual(t4, self.a)

        # incompatible type
        try:
            self.a += self.r_with_unit
            self.assertTrue(False, "Should've crashed")
        except ValueError:
            self.assertTrue(True)

    def test_isub(self):
        # a -= b
        # a -= c
        # a -= d
        # a -= d
        # a -= neg
        t1 = self.cls_name(res={"r1": 0, "r2": -1, "r3": 0})
        self.a -= self.b
        self.assertEqual(t1, self.a)

        t2 = self.cls_name(res={"r1": 0, "r2": -10, "r3": 0})
        self.a -= self.c
        self.assertEqual(t2, self.a)

        t3 = self.cls_name(res={"r1": 0, "r2": -10, "r3": 0, "r4": -1})
        self.a -= self.d
        self.assertEqual(t3, self.a)

        t4 = self.cls_name(res={"r1": 1, "r2": -10, "r3": 0, "r4": -1})
        self.a -= self.neg
        self.assertEqual(t4, self.a)

        # incompatible type
        try:
            self.a += self.r_with_unit
            self.assertTrue(False, "Should've crashed")
        except ValueError:
            self.assertTrue(True)

    def test_ge(self):
        # >= a number
        self.assertTrue(self.a >= 0)
        self.assertFalse(self.a >= 1)

        # >= a Resource
        self.assertTrue(self.a >= self.a)
        self.assertFalse(self.a >= self.b)
        self.assertTrue(self.b >= self.a)

        # incompatible type
        try:
            _ = self.a >= self.r_with_unit
            self.assertTrue(False, "Should've crashed")
        except ValueError:
            self.assertTrue(True)

    def test_eq(self):
        t1 = self.cls_name(res={"r1": 3, "r2": 5})
        self.assertTrue(t1 == self.a)

        t2 = ResourceStat(res={"r1": 3, "r2": 5}, unit="dummy")
        self.assertFalse(t2 == self.a)

    def test_ne(self):
        t1 = self.cls_name(res={"r1": 3, "r2": 5})
        self.assertFalse(t1 != self.a)

        t2 = ResourceStat(res={"r1": 3, "r2": 5}, unit="dummy")
        self.assertTrue(t2 != self.a)


class TestGpu(TestResource):
    def init_with_class(self):
        self.cls_name = Gpu


class TestCpu(TestResource):
    def init_with_class(self):
        self.cls_name = Cpu


class TestMemory(TestResource):
    def init_with_class(self):
        self.cls_name = Memory
