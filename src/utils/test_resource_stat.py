#!/usr/bin/env python3

from unittest import TestCase
from resource_stat import ResourceStat, Gpu, Cpu, Memory, GpuMemory


class TestResource(TestCase):
    def init_class(self):
        self.cls_name = ResourceStat

    def init_variables(self):
        self.a = self.cls_name(res={"r1": "3", "r2": "5", "r3": "0"})
        self.scalar = 0.5
        self.a_scalar_mul = self.cls_name(res={
            "r1": "1.5", "r2": "2.5", "r3": "0"
        })
        self.a_scalar_div = self.cls_name(res={
            "r1": "6", "r2": "10", "r3": "0"
        })
        self.b = self.cls_name(res={"r1": "3", "r2": "6"})
        self.c = self.cls_name(res={"r1": "-1"})
        self.d = self.cls_name(res={"r1": "3", "r2": "5"})
        self.e = ResourceStat(res={"r1": "3", "r2": "5"}, unit="u")

        self.a_b_sum = self.cls_name(res={"r1": "6", "r2": "11", "r3": "0"})
        self.a_b_diff = self.cls_name(res={"r1": "0", "r2": "-1", "r3": "0"})
        self.a_c_sum = self.cls_name(res={"r1": "2", "r2": "5", "r3": "0"})
        self.a_c_diff = self.cls_name(res={"r1": "4", "r2": "5", "r3": "0"})
        self.a_b_mul = self.cls_name(res={"r1": "9", "r2": "30"})
        self.b_d_div = self.cls_name(res={"r1": "1", "r2": "1.2"})
        self.a_zero_ge = True
        self.a_one_ge = False
        self.a_b_ge = False
        self.b_a_ge = True
        self.a_d_eq = True
        self.a_e_eq = False

    def mutate_variables(self):
        pass

    def setUp(self):
        self.init_class()
        self.init_variables()
        self.mutate_variables()

    def test_min_zero(self):
        self.assertEqual(self.cls_name(res={"r1": "0"}), self.c.min_zero())

    def test_prune(self):
        self.assertEqual({}, self.cls_name(res={"r1": "0"}).prune().resource)

    def test_repr(self):
        v = self.cls_name(res={"r1": "1"})
        unit = v.unit if v.unit is not None else ""
        t = "{'r1': '%s%s'}" % (float(1), unit)
        self.assertEqual(t, repr(v))

        v = ResourceStat(res={"r1": "1"}, unit="u")
        self.assertEqual("{'r1': '%su'}" % float(1), repr(v))

    def test_add(self):
        # a + b
        self.assertEqual(self.a_b_sum, self.a + self.b)
        self.assertTrue(isinstance(self.a + self.b, self.cls_name))

        # a + c
        self.assertEqual(self.a_c_sum, self.a + self.c)
        self.assertTrue(isinstance(self.a + self.c, self.cls_name))

    def test_iadd(self):
        # a += b
        v = self.cls_name(self.a)
        v += self.b
        self.assertEqual(self.a_b_sum, v)

        # a += c
        v = self.cls_name(self.a)
        v += self.c
        self.assertEqual(self.a_c_sum, v)

    def test_sub(self):
        # a - b
        self.assertEqual(self.a_b_diff, self.a - self.b)

        # a - c
        self.assertEqual(self.a_c_diff, self.a - self.c)

    def test_isub(self):
        # a -= b
        v = self.cls_name(self.a)
        v -= self.b
        self.assertEqual(self.a_b_diff, v)

        # a += c
        v = self.cls_name(self.a)
        v -= self.c
        self.assertEqual(self.a_c_diff, v)

    def test_mul(self):
        # a * scalar
        self.assertEqual(self.a_scalar_mul, self.a * self.scalar)

        # a * b
        self.assertEqual(self.a_b_mul, self.a * self.b)

    def test_imul(self):
        # a *= scalar
        v = self.cls_name(self.a)
        v *= self.scalar
        self.assertEqual(self.a_scalar_mul, v)

        # a *= b
        v = self.cls_name(self.a)
        v *= self.b
        self.assertEqual(self.a_b_mul, v)

    def test_truediv(self):
        # a / scalar
        self.assertEqual(self.a_scalar_div, self.a / self.scalar)

        # a / b => ValueError
        try:
            self.a / self.b
            self.fail("Should raise ValueError")
        except ValueError:
            self.assertTrue(True)
        except Exception:
            self.fail("Should raise ValueError")

        # b / d
        self.assertEqual(self.b_d_div, self.b / self.d)

    def test_idiv(self):
        # a /= scalar
        v = self.cls_name(self.a)
        v /= self.scalar
        self.assertEqual(self.a_scalar_div, v)

        # a /= b => ValueError
        try:
            v = self.cls_name(self.a)
            v /= self.b
            self.fail("Should raise ValueError")
        except ValueError:
            self.assertTrue(True)
        except Exception:
            self.fail("Should raise ValueError")

        # b /= d
        v = self.cls_name(self.b)
        v /= self.d
        self.assertEqual(self.b_d_div, v)

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
            self.fail("incompatible + should have crashed")
        except ValueError:
            self.assertTrue(True)

        try:
            r1 - r2
            self.fail("incompatible - should have crashed")
        except ValueError:
            self.assertTrue(True)

        try:
            r1 += r2
            self.fail("incompatible += should have crashed")
        except ValueError:
            self.assertTrue(True)

        try:
            r1 -= r2
            self.fail("incompatible -= should have crashed")
        except ValueError:
            self.assertTrue(True)

        try:
            _ = r1 >= r2
            self.fail("incompatible >= should have crashed")
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

    def test_millicpu2cpu(self):
        self.assertEqual(Cpu(res={"r1": "1"}), Cpu(res={"r1": "1000m"}))

    def test_repr(self):
        self.assertEqual("{'r1': '%s'}" % float(1), repr(Cpu(res={"r1": "1"})))


class TestMemory(TestResource):
    def init_class(self):
        self.cls_name = Memory

    def mutate_variables(self):
        self.a = Memory(res={"r1": "3Mi", "r2": "5Mi", "r3": "0Mi"})
        self.a_scalar_mul = Memory(res={
            "r1": "1.5Mi", "r2": "2.5Mi", "r3": "0"
        })
        self.a_scalar_div = self.cls_name(res={
            "r1": "6Mi", "r2": "10Mi", "r3": "0Mi"
        })
        self.b = Memory(res={"r1": "3Mi", "r2": "6Mi"})
        self.c = Memory(res={"r1": "-1Mi"})
        self.d = Memory(res={"r1": "3Mi", "r2": "5Mi"})

        self.a_b_sum = Memory(res={"r1": "6Mi", "r2": "11Mi", "r3": "0Mi"})
        self.a_b_diff = Memory(res={"r1": "0Mi", "r2": "-1Mi", "r3": "0Mi"})
        self.a_c_sum = Memory(res={"r1": "2Mi", "r2": "5Mi", "r3": "0Mi"})
        self.a_c_diff = Memory(res={"r1": "4Mi", "r2": "5Mi", "r3": "0Mi"})
        self.a_b_mul = self.cls_name(res={"r1": "9Ti", "r2": "30Ti"})
        self.b_d_div = self.cls_name(res={"r1": "1", "r2": "1.2"})

    def test_repr(self):
        self.assertEqual("{'r1': '%sB', 'r2': '%sB'}" % (float(104857600),
                                                         float(102400)),
                         repr(Memory(res={"r1": "100Mi", "r2": "100Ki"})))


class TestMemoryDifferentUnit(TestResource):
    def init_class(self):
        self.cls_name = Memory

    def mutate_variables(self):
        self.a = Memory(res={"r1": "3Gi", "r2": "5Mi", "r3": "0Gi"})
        self.a_scalar_mul = Memory(res={
            "r1": "1.5Gi", "r2": "2.5Mi", "r3": "0"
        })
        self.a_scalar_div = self.cls_name(res={
            "r1": "6Gi", "r2": "10Mi", "r3": "0Mi"
        })
        self.b = Memory(res={"r1": "3Mi", "r2": "6Mi"})
        self.c = Memory(res={"r1": "-1Gi"})
        self.d = Memory(res={"r1": "3Gi", "r2": "5Mi"})

        self.a_b_sum = Memory(res={"r1": "3075Mi", "r2": "11Mi", "r3": "0Mi"})
        self.a_b_diff = Memory(res={"r1": "3069Mi", "r2": "-1Mi", "r3": "0Mi"})
        self.a_c_sum = Memory(res={"r1": "2Gi", "r2": "5Mi", "r3": "0Mi"})
        self.a_c_diff = Memory(res={"r1": "4Gi", "r2": "5Mi", "r3": "0Mi"})
        self.a_b_mul = self.cls_name(res={"r1": "9Pi", "r2": "30Ti"})
        self.b_d_div = self.cls_name(res={"r1": "0.0009765625", "r2": "1.2"})

        self.b_a_ge = False
        self.a_f_ge = True

    def test_repr(self):
        self.assertEqual("{'r1': '%sB', 'r2': '%sB'}" % (float(104857600),
                                                         float(102400)),
                         repr(Memory(res={"r1": "100Mi", "r2": "100Ki"})))


class TestGpuMemory(TestResource):
    def init_class(self):
        self.cls_name = GpuMemory

    def mutate_variables(self):
        self.a = GpuMemory(res={"r1": "3Gi", "r2": "5Mi", "r3": "0Gi"})
        self.a_scalar_mul = GpuMemory(res={
            "r1": "1.5Gi", "r2": "2.5Mi", "r3": "0"
        })
        self.a_scalar_div = self.cls_name(res={
            "r1": "6Gi", "r2": "10Mi", "r3": "0Mi"
        })
        self.b = GpuMemory(res={"r1": "3Mi", "r2": "6Mi"})
        self.c = GpuMemory(res={"r1": "-1Gi"})
        self.d = GpuMemory(res={"r1": "3Gi", "r2": "5Mi"})

        self.a_b_sum = GpuMemory(res={
            "r1": "3075Mi",
            "r2": "11Mi",
            "r3": "0Mi"
        })
        self.a_b_diff = GpuMemory(res={
            "r1": "3069Mi",
            "r2": "-1Mi",
            "r3": "0Mi"
        })
        self.a_c_sum = GpuMemory(res={
            "r1": "2Gi",
            "r2": "5Mi",
            "r3": "0Mi"
        })
        self.a_c_diff = GpuMemory(res={
            "r1": "4Gi",
            "r2": "5Mi",
            "r3": "0Mi"
        })
        self.a_b_mul = self.cls_name(res={
            "r1": "9Pi",
            "r2": "30Ti"
        })
        self.b_d_div = self.cls_name(res={
            "r1": "0.0009765625",
            "r2": "1.2"
        })

        self.b_a_ge = False
        self.a_f_ge = True

    def test_repr(self):
        self.assertEqual("{'r1': '%sB', 'r2': '%sB'}" % (float(104857600),
                                                         float(102400)),
                         repr(GpuMemory(res={"r1": "100Mi", "r2": "100Ki"})))
