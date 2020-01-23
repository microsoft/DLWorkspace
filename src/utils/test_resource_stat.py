#!/usr/bin/env python3

from unittest import TestCase
from resource_stat import ResourceStat, Gpu, Cpu, Memory


class TestResource(TestCase):
    def init_class(self):
        self.cls_name = ResourceStat

    def init_variables(self):
        self.a = self.cls_name(res={"r1": "3", "r2": "5", "r3": "0"})
        self.b = self.cls_name(res={"r1": "3", "r2": "6"})
        self.c = self.cls_name(res={"r1": "-1"})
        self.d = self.cls_name(res={"r1": "3", "r2": "5"})
        self.e = ResourceStat(res={"r1": "3", "r2": "5"}, unit="u")

        self.a_b_sum = self.cls_name(res={"r1": "6", "r2": "11", "r3": "0"})
        self.a_b_diff = self.cls_name(res={"r1": "0", "r2": "-1", "r3": "0"})
        self.a_c_sum = self.cls_name(res={"r1": "2", "r2": "5", "r3": "0"})
        self.a_c_diff = self.cls_name(res={"r1": "4", "r2": "5", "r3": "0"})
        self.a_zero_ge = True
        self.a_one_ge = False
        self.a_b_ge = False
        self.b_a_ge = True
        self.a_d_eq = True
        self.a_e_eq = False

    def setUp(self):
        self.init_class()
        self.init_variables()

    def test_min_zero(self):
        self.assertEqual(self.cls_name(res={"r1": "0"}), self.c.min_zero())

    def test_prune(self):
        self.assertEqual({}, self.cls_name(res={"r1": "0"}).prune().resource)

    def test_repr(self):
        v = self.cls_name(res={"r1": "1"})
        unit = v.unit if v.unit is not None else ""
        t = "{'r1': '1%s'}" % unit
        self.assertEqual(t, repr(v))

        v = ResourceStat(res={"r1": "1"}, unit="u")
        self.assertEqual("{'r1': '1u'}", repr(v))

    def test_add(self):
        # a + b
        self.assertEqual(self.a_b_sum, self.a + self.b)
        self.assertTrue(isinstance(self.a + self.b, self.cls_name))

        # a + c
        self.assertEqual(self.a_c_sum, self.a + self.c)
        self.assertTrue(isinstance(self.a + self.c, self.cls_name))

    def test_sub(self):
        # a - b
        self.assertEqual(self.a_b_diff, self.a - self.b)

        # a - c
        self.assertEqual(self.a_c_diff, self.a - self.c)

    def test_iadd(self):
        # a += b
        v = self.cls_name(self.a)
        v += self.b
        self.assertEqual(self.a_b_sum, v)

        # a += c
        v = self.cls_name(self.a)
        v += self.c
        self.assertEqual(self.a_c_sum, v)

    def test_isub(self):
        # a -= b
        v = self.cls_name(self.a)
        v -= self.b
        self.assertEqual(self.a_b_diff, v)

        # a += c
        v = self.cls_name(self.a)
        v -= self.c
        self.assertEqual(self.a_c_diff, v)

    def test_ge(self):
        # >= a number
        self.assertEqual(self.a_zero_ge, self.a >= 0)
        self.assertEqual(self.a_one_ge, self.a >= 1)

        # >= a Resource
        self.assertTrue(self.a >= self.a)
        self.assertEqual(self.a_b_ge, self.a >= self.b)
        self.assertEqual(self.b_a_ge, self.b >= self.a)

    def test_eq(self):
        self.assertEqual(self.a_d_eq, self.a == self.d)
        self.assertEqual(self.a_e_eq, self.a == self.e)

    def test_ne(self):
        self.assertEqual(not self.a_d_eq, self.a != self.d)
        self.assertEqual(not self.a_e_eq, self.a != self.e)

    def test_incompatible_type(self):
        r1 = self.cls_name(res={"r1": 1})
        r2 = ResourceStat(res={"r1": 1}, unit="u")

        try:
            r1 + r2
            self.assertTrue(False, "incompatible + should have crashed")
        except ValueError:
            self.assertTrue(True)

        try:
            r1 - r2
            self.assertTrue(False, "incompatible - should have crashed")
        except ValueError:
            self.assertTrue(True)

        try:
            r1 += r2
            self.assertTrue(False, "incompatible += should have crashed")
        except ValueError:
            self.assertTrue(True)

        try:
            r1 -= r2
            self.assertTrue(False, "incompatible -= should have crashed")
        except ValueError:
            self.assertTrue(True)

        try:
            _ = r1 >= r2
            self.assertTrue(False, "incompatible >= should have crashed")
        except ValueError:
            self.assertTrue(True)


class TestGpu(TestResource):
    def init_class(self):
        self.cls_name = Gpu

    def test_empty_gpu_type(self):
        self.assertEqual(Gpu(), Gpu({"": 1}))


class TestCpu(TestResource):
    def init_class(self):
        self.cls_name = Cpu

    def init_variables(self):
        self.a = Cpu(res={"r1": "3m", "r2": "5m", "r3": "0m"})
        self.b = Cpu(res={"r1": "3m", "r2": "6m"})
        self.c = Cpu(res={"r1": "-1m"})
        self.d = Cpu(res={"r1": "3m", "r2": "5m"})
        self.e = ResourceStat(res={"r1": "3", "r2": "5"}, unit="u")

        self.a_b_sum = Cpu(res={"r1": "6m", "r2": "11m", "r3": "0m"})
        self.a_b_diff = Cpu(res={"r1": "0m", "r2": "-1m", "r3": "0m"})
        self.a_c_sum = Cpu(res={"r1": "2m", "r2": "5m", "r3": "0m"})
        self.a_c_diff = Cpu(res={"r1": "4m", "r2": "5m", "r3": "0m"})
        self.a_zero_ge = True
        self.a_one_ge = False
        self.a_b_ge = False
        self.b_a_ge = True
        self.a_d_eq = True
        self.a_e_eq = False

    def test_repr(self):
        self.assertEqual("{'r1': '1000m'}", repr(Cpu(res={"r1": "1"})))


class TestMemory(TestResource):
    def init_class(self):
        self.cls_name = Memory

    def init_variables(self):
        self.a = Memory(res={"r1": "3Mi", "r2": "5Mi", "r3": "0Mi"})
        self.b = Memory(res={"r1": "3Mi", "r2": "6Mi"})
        self.c = Memory(res={"r1": "-1Mi"})
        self.d = Memory(res={"r1": "3Mi", "r2": "5Mi"})
        self.e = ResourceStat(res={"r1": "3", "r2": "5"}, unit="u")

        self.a_b_sum = Memory(res={"r1": "6Mi", "r2": "11Mi", "r3": "0Mi"})
        self.a_b_diff = Memory(res={"r1": "0Mi", "r2": "-1Mi", "r3": "0Mi"})
        self.a_c_sum = Memory(res={"r1": "2Mi", "r2": "5Mi", "r3": "0Mi"})
        self.a_c_diff = Memory(res={"r1": "4Mi", "r2": "5Mi", "r3": "0Mi"})
        self.a_zero_ge = True
        self.a_one_ge = False
        self.a_b_ge = False
        self.b_a_ge = True
        self.a_d_eq = True
        self.a_e_eq = False

    def test_repr(self):
        self.assertEqual("{'r1': '104857600B', 'r2': '102400B'}",
                         repr(Memory(res={"r1": "100Mi", "r2": "100Ki"})))


class TestMemoryDifferentUnit(TestResource):
    def init_class(self):
        self.cls_name = Memory

    def init_variables(self):
        self.a = Memory(res={"r1": "3Gi", "r2": "5Mi", "r3": "0Gi"})
        self.b = Memory(res={"r1": "3Mi", "r2": "6Mi"})
        self.c = Memory(res={"r1": "-1Gi"})
        self.d = Memory(res={"r1": "3Gi", "r2": "5Mi"})
        self.e = ResourceStat(res={"r1": "3", "r2": "5"}, unit="u")

        self.a_b_sum = Memory(res={"r1": "3075Mi", "r2": "11Mi", "r3": "0Mi"})
        self.a_b_diff = Memory(res={"r1": "3069Mi", "r2": "-1Mi", "r3": "0Mi"})
        self.a_c_sum = Memory(res={"r1": "2Gi", "r2": "5Mi", "r3": "0Mi"})
        self.a_c_diff = Memory(res={"r1": "4Gi", "r2": "5Mi", "r3": "0Mi"})
        self.a_zero_ge = True
        self.a_one_ge = False
        self.a_b_ge = False
        self.b_a_ge = False
        self.a_d_eq = True
        self.a_e_eq = False

    def test_repr(self):
        self.assertEqual("{'r1': '104857600B', 'r2': '102400B'}",
                         repr(Memory(res={"r1": "100Mi", "r2": "100Ki"})))
