#!/usr/bin/env python3

from unittest import TestCase
from resource_stat import make_resource, dictionarize, ResourceStat


class DummyResource(ResourceStat):
    pass


class TestResource(TestCase):
    def init_class(self):
        self.r_type = None

    def setUp(self):
        self.init_class()

    def test_repr(self):
        v = make_resource(self.r_type, {"r1": "1"})
        t = "{'r1': %s}" % (float(1))
        self.assertEqual(t, repr(v))

    def test_scalar(self):
        v = make_resource(self.r_type, {"r1": "1"})
        self.assertEqual(1, v.scalar("r1"))
        self.assertIsNone(v.scalar("r2"))

    def test_normalize(self):
        v = make_resource(self.r_type, None)
        v.res = {"r1": 1.0, "r2": -1.0}
        v.normalize()
        self.assertEqual({"r1": 1.0, "r2": 0}, v.res)

    def test_floor(self):
        v = make_resource(self.r_type, {"r1": "1.5"})
        expected = make_resource(self.r_type, {"r1": "1"})
        self.assertEqual(expected, v.floor)

    def test_ceil(self):
        v = make_resource(self.r_type, {"r1": "1.5"})
        expected = make_resource(self.r_type, {"r1": "2"})
        self.assertEqual(expected, v.ceil)

    def test_add(self):
        v1 = make_resource(self.r_type, {"r1": "1", "r2": "2"})
        v2 = make_resource(self.r_type, {"r1": "2"})
        result = v1 + v2
        expected = make_resource(self.r_type, {"r1": "3", "r2": "2"})
        self.assertEqual(expected, result)

    def test_iadd(self):
        v1 = make_resource(self.r_type, {"r1": "1", "r2": "2"})
        v2 = make_resource(self.r_type, {"r1": "2"})
        v1 += v2
        expected = make_resource(self.r_type, {"r1": "3", "r2": "2"})
        self.assertEqual(expected, v1)

    def test_sub(self):
        v1 = make_resource(self.r_type, {"r1": "1", "r2": "2"})
        v2 = make_resource(self.r_type, {"r1": "2"})
        result = v1 - v2
        expected = make_resource(self.r_type, {"r1": "0", "r2": "2"})
        self.assertEqual(expected, result)

    def test_isub(self):
        v1 = make_resource(self.r_type, {"r1": "1", "r2": "2"})
        v2 = make_resource(self.r_type, {"r1": "2"})
        v1 -= v2
        expected = make_resource(self.r_type, {"r1": "0", "r2": "2"})
        self.assertEqual(expected, v1)

    def test_mul(self):
        # scalar
        v1 = make_resource(self.r_type, {"r1": "1", "r2": "2"})
        result = v1 * 2
        expected = make_resource(self.r_type, {"r1": "2", "r2": "4"})
        self.assertEqual(expected, result)

        # v1 * v2
        v1 = make_resource(self.r_type, {"r1": "1", "r2": "2"})
        v2 = make_resource(self.r_type, {"r1": "3", "r2": "0.5"})
        result = v1 * v2
        expected = make_resource(self.r_type, {"r1": "3", "r2": "1"})
        self.assertEqual(expected, result)

    def test_imul(self):
        # scalar
        v1 = make_resource(self.r_type, {"r1": "1", "r2": "2"})
        v1 *= 2
        expected = make_resource(self.r_type, {"r1": "2", "r2": "4"})
        self.assertEqual(expected, v1)

        # v1 * v2
        v1 = make_resource(self.r_type, {"r1": "1", "r2": "2"})
        v2 = make_resource(self.r_type, {"r1": "4", "r2": "0.5"})
        v1 *= v2
        expected = make_resource(self.r_type, {"r1": "4", "r2": "1"})
        self.assertEqual(expected, v1)

    def test_truediv(self):
        # scalar
        v1 = make_resource(self.r_type, {"r1": "1", "r2": "2"})
        result = v1 / 2
        expected = make_resource(self.r_type, {"r1": "0.5", "r2": "1"})
        self.assertEqual(expected, result)

        # v1 * v2
        v1 = make_resource(self.r_type, {"r1": "1", "r2": "2"})
        v2 = make_resource(self.r_type, {"r1": "4", "r2": "0.5"})
        result = v1 / v2
        expected = make_resource(self.r_type, {"r1": "0.25", "r2": "4"})
        self.assertEqual(expected, result)

    def test_idiv(self):
        # scalar
        v1 = make_resource(self.r_type, {"r1": "1", "r2": "2"})
        v1 /= 2
        expected = make_resource(self.r_type, {"r1": "0.5", "r2": "1"})
        self.assertEqual(expected, v1)

        # v1 * v2
        v1 = make_resource(self.r_type, {"r1": "1", "r2": "2"})
        v2 = make_resource(self.r_type, {"r1": "4", "r2": "0.5"})
        v1 /= v2
        expected = make_resource(self.r_type, {"r1": "0.25", "r2": "4"})
        self.assertEqual(expected, v1)

    def test_div_by_zero(self):
        # scalar
        v1 = make_resource(self.r_type, {"r1": "1", "r2": "2"})
        result = v1 / 0
        expected = make_resource(self.r_type, {"r1": "0", "r2": "0"})
        self.assertEqual(expected, result)

        # v1 * v2
        v1 = make_resource(self.r_type, {"r1": "1", "r2": "2"})
        v2 = make_resource(self.r_type, {"r1": "4", "r2": "0"})
        result = v1 / v2
        expected = make_resource(self.r_type, {"r1": "0.25", "r2": "0"})
        self.assertEqual(expected, result)

    def test_ge(self):
        v = make_resource(self.r_type, {"r1": "1", "r2": "0"})
        self.assertTrue(v >= 0)
        self.assertFalse(v >= 1)

        v1 = make_resource(self.r_type, {"r1": "1", "r2": "2"})
        v2 = make_resource(self.r_type, {"r1": "1"})
        self.assertTrue(v1 >= v2)

        v1 = make_resource(self.r_type, {"r1": "1", "r2": "2"})
        v2 = make_resource(self.r_type, {"r1": "2", "r2": "1"})
        self.assertFalse(v1 >= v2)

    def test_eq(self):
        v1 = make_resource(self.r_type, {"r1": "1", "r2": "0"})
        v2 = make_resource(self.r_type, {"r1": "1"})
        self.assertTrue(v1 == v2)

        v1 = make_resource(self.r_type, {"r1": "1", "r2": "0"})
        v2 = make_resource(self.r_type, {"r1": "1", "r2": "1"})
        self.assertFalse(v1 == v2)

    def test_ne(self):
        v1 = make_resource(self.r_type, {"r1": "1", "r2": "0"})
        v2 = make_resource(self.r_type, {"r1": "1"})
        self.assertFalse(v1 != v2)

        v1 = make_resource(self.r_type, {"r1": "1", "r2": "0"})
        v2 = make_resource(self.r_type, {"r1": "1", "r2": "1"})
        self.assertTrue(v1 != v2)

    def test_incompatible_type(self):
        v1 = make_resource(self.r_type, {"r1": "1", "r2": "0"})
        v2 = DummyResource(params={"r1": "1"})

        try:
            v1 + v2
            self.fail("incompatible + should have crashed")
        except ValueError:
            self.assertTrue(True)

        try:
            v1 - v2
            self.fail("incompatible - should have crashed")
        except ValueError:
            self.assertTrue(True)

        try:
            v1 += v2
            self.fail("incompatible += should have crashed")
        except ValueError:
            self.assertTrue(True)

        try:
            v1 -= v2
            self.fail("incompatible -= should have crashed")
        except ValueError:
            self.assertTrue(True)

        try:
            _ = v1 >= v2
            self.fail("incompatible >= should have crashed")
        except ValueError:
            self.assertTrue(True)


class TestCpu(TestResource):
    def init_class(self):
        self.r_type = "cpu"

    def test_convert(self):
        v = make_resource(self.r_type, {"r1": "100m"})
        expected = make_resource(self.r_type, {"r1": "0.1"})
        self.assertEqual(expected, v)

    def test_scalar(self):
        v = make_resource(self.r_type, {"r1": "1"})
        self.assertEqual("1000m", v.scalar("r1"))
        self.assertIsNone(v.scalar("r2"))


class TestMemory(TestResource):
    def init_class(self):
        self.r_type = "memory"

    def test_convert(self):
        v = make_resource(self.r_type, {"r1": "1Gi"})
        expected = make_resource(self.r_type, {"r1": "1073741824"})
        self.assertEqual(expected, v)

    def test_scalar(self):
        v = make_resource(self.r_type, {"r1": 1048576})
        self.assertEqual("1Mi", v.scalar("r1"))
        self.assertIsNone(v.scalar("r2"))


class TestGpu(TestResource):
    def init_class(self):
        self.r_type = "gpu"


class TestGpuMemory(TestResource):
    def init_class(self):
        self.r_type = "gpu_memory"

    def test_convert(self):
        v = make_resource(self.r_type, {"r1": "16Gi"})
        expected = make_resource(self.r_type, {"r1": "17179869184"})
        self.assertEqual(expected, v)

    def test_scalar(self):
        v = make_resource(self.r_type, {"r1": 1048576})
        self.assertEqual("1Mi", v.scalar("r1"))
        self.assertIsNone(v.scalar("r2"))


class TestDictionarize(TestCase):
    def test_dictionarize(self):
        v = {
            "gpu_capacity": make_resource("gpu", {"r1": "8"}),
            "user_status": {
                "username": "user1",
                "user_gpu": make_resource("gpu", {"r1": "4"}),
            },
            "node_status": [{
                "gpu_used": make_resource("gpu", {"r1": "6"}),
            }],
            "none_field": None,
        }
        expected = {
            "gpu_capacity": {
                "r1": 8.0
            },
            "user_status": {
                "username": "user1",
                "user_gpu": {
                    "r1": 4.0
                },
            },
            "node_status": [{
                "gpu_used": {
                    "r1": 6.0
                }
            }],
            "none_field": None,
        }

        result = dictionarize(v)
        self.assertEqual(expected, result)
