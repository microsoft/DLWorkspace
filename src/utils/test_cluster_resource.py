#!/usr/bin/env python3

import copy

from unittest import TestCase
from cluster_resource import ClusterResource


class TestClusterResource(TestCase):
    def setUp(self):
        v1_params = {
            "cpu": {
                "r1": "2",
                "r2": "4",
            },
            "memory": {
                "r1": "100Ki",
                "r2": "200Ki",
            },
            "gpu": {
                "r1": "1",
                "r2": "2",
            },
            "gpu_memory": {
                "r1": "100Ki",
                "r2": "200Ki",
            },
        }
        self.v1 = ClusterResource(params=v1_params)

        v2_params = {
            "cpu": {
                "r1": "2",
                "r2": "2",
            },
            "memory": {
                "r1": "400Ki",
                "r2": "100Ki",
            },
            "gpu": {
                "r1": "4",
                "r2": "4",
            },
            "gpu_memory": {
                "r1": "400Ki",
                "r2": "400Ki",
            },
        }
        self.v2 = ClusterResource(params=v2_params)

        v3_params = {
            "cpu": {
                "r1": "0.5",
            },
            "memory": {
                "r1": "0.5",
            },
            "gpu": {
                "r1": "1",
            },
            "gpu_memory": {
                "r1": "1",
            },
        }
        self.v3 = ClusterResource(params=v3_params)

        self.scalar = 0.5

    def test_floor(self):
        v = ClusterResource(
            params={
                "cpu": {
                    "r1": "1.5",
                },
                "memory": {
                    "r1": "100.2",
                },
                "gpu": {
                    "r1": "10.4",
                },
                "gpu_memory": {
                    "r1": "199.9",
                },
            }).floor
        expected = ClusterResource(
            params={
                "cpu": {
                    "r1": "1",
                },
                "memory": {
                    "r1": "100",
                },
                "gpu": {
                    "r1": "10",
                },
                "gpu_memory": {
                    "r1": "199",
                },
            })
        self.assertEqual(expected, v)

    def test_ceil(self):
        v = ClusterResource(
            params={
                "cpu": {
                    "r1": "1.5",
                },
                "memory": {
                    "r1": "100.2",
                },
                "gpu": {
                    "r1": "10.4",
                },
                "gpu_memory": {
                    "r1": "199.9",
                },
            }).ceil
        expected = ClusterResource(
            params={
                "cpu": {
                    "r1": "2",
                },
                "memory": {
                    "r1": "101",
                },
                "gpu": {
                    "r1": "11",
                },
                "gpu_memory": {
                    "r1": "200",
                },
            })
        self.assertEqual(expected, v)

    def test_repr(self):
        v = ClusterResource(
            params={
                "cpu": {
                    "r1": "1m",
                },
                "memory": {
                    "r1": "100Ki",
                },
                "gpu": {
                    "r1": "4",
                },
                "gpu_memory": {
                    "r1": "200Ki"
                }
            })
        self.assertEqual(
            "{'cpu': {'r1': %s}, 'memory': {'r1': %s}, "
            "'gpu': {'r1': %s}, 'gpu_memory': {'r1': %s}}" %
            (0.001, float(102400), float(4), float(204800)), repr(v))

    def test_eq(self):
        self.assertTrue(self.v1 == self.v1)
        self.assertFalse(self.v1 == self.v2)

    def test_ne(self):
        self.assertFalse(self.v1 != self.v1)
        self.assertTrue(self.v1 != self.v2)

    def test_ge(self):
        self.assertFalse(self.v1 >= self.v2)

    def test_add(self):
        result = self.v1 + self.v2
        expected = ClusterResource(
            params={
                "cpu": {
                    "r1": "4",
                    "r2": "6",
                },
                "memory": {
                    "r1": "500Ki",
                    "r2": "300Ki",
                },
                "gpu": {
                    "r1": "5",
                    "r2": "6",
                },
                "gpu_memory": {
                    "r1": "500Ki",
                    "r2": "600Ki",
                },
            })
        self.assertEqual(expected, result)

    def test_iadd(self):
        self.v1 += self.v2
        expected = ClusterResource(
            params={
                "cpu": {
                    "r1": "4",
                    "r2": "6",
                },
                "memory": {
                    "r1": "500Ki",
                    "r2": "300Ki",
                },
                "gpu": {
                    "r1": "5",
                    "r2": "6",
                },
                "gpu_memory": {
                    "r1": "500Ki",
                    "r2": "600Ki",
                },
            })
        self.assertEqual(expected, self.v1)

    def test_sub(self):
        result = self.v1 - self.v2
        expected = ClusterResource(
            params={
                "cpu": {
                    "r1": "0",
                    "r2": "2",
                },
                "memory": {
                    "r1": "0",
                    "r2": "100Ki",
                },
                "gpu": {
                    "r1": "0",
                    "r2": "0",
                },
                "gpu_memory": {
                    "r1": "0",
                    "r2": "0",
                },
            })
        self.assertEqual(expected, result)

    def test_isub(self):
        self.v1 -= self.v2
        expected = ClusterResource(
            params={
                "cpu": {
                    "r1": "0",
                    "r2": "2",
                },
                "memory": {
                    "r1": "0",
                    "r2": "100Ki",
                },
                "gpu": {
                    "r1": "0",
                    "r2": "0",
                },
                "gpu_memory": {
                    "r1": "0",
                    "r2": "0",
                },
            })
        self.assertEqual(expected, self.v1)

    def test_mul(self):
        result = self.v1 * self.scalar
        expected = ClusterResource(
            params={
                "cpu": {
                    "r1": "1",
                    "r2": "2",
                },
                "memory": {
                    "r1": "50Ki",
                    "r2": "100Ki",
                },
                "gpu": {
                    "r1": "0.5",
                    "r2": "1",
                },
                "gpu_memory": {
                    "r1": "50Ki",
                    "r2": "100Ki",
                },
            })
        self.assertEqual(expected, result)

        result = self.v1 * self.v3
        expected = ClusterResource(
            params={
                "cpu": {
                    "r1": "1",
                },
                "memory": {
                    "r1": "50Ki",
                },
                "gpu": {
                    "r1": "1",
                },
                "gpu_memory": {
                    "r1": "100Ki",
                },
            })
        self.assertEqual(expected, result)

    def test_imul(self):
        v = copy.deepcopy(self.v1)
        v *= self.scalar
        expected = ClusterResource(
            params={
                "cpu": {
                    "r1": "1",
                    "r2": "2",
                },
                "memory": {
                    "r1": "50Ki",
                    "r2": "100Ki",
                },
                "gpu": {
                    "r1": "0.5",
                    "r2": "1",
                },
                "gpu_memory": {
                    "r1": "50Ki",
                    "r2": "100Ki",
                },
            })
        self.assertEqual(expected, v)

        v = copy.deepcopy(self.v1)
        v *= self.v3
        expected = ClusterResource(
            params={
                "cpu": {
                    "r1": "1",
                },
                "memory": {
                    "r1": "50Ki",
                },
                "gpu": {
                    "r1": "1",
                },
                "gpu_memory": {
                    "r1": "100Ki",
                },
            })
        self.assertEqual(expected, v)

    def test_truediv(self):
        result = self.v1 / self.scalar
        expected = ClusterResource(
            params={
                "cpu": {
                    "r1": "4",
                    "r2": "8",
                },
                "memory": {
                    "r1": "200Ki",
                    "r2": "400Ki",
                },
                "gpu": {
                    "r1": "2",
                    "r2": "4",
                },
                "gpu_memory": {
                    "r1": "200Ki",
                    "r2": "400Ki",
                },
            })
        self.assertEqual(expected, result)

        result = self.v1 / self.v3
        expected = ClusterResource(
            params={
                "cpu": {
                    "r1": "4",
                },
                "memory": {
                    "r1": "200Ki",
                },
                "gpu": {
                    "r1": "1",
                },
                "gpu_memory": {
                    "r1": "100Ki",
                },
            })
        self.assertEqual(expected, result)

    def test_idiv(self):
        v = copy.deepcopy(self.v1)
        v /= self.scalar
        expected = ClusterResource(
            params={
                "cpu": {
                    "r1": "4",
                    "r2": "8",
                },
                "memory": {
                    "r1": "200Ki",
                    "r2": "400Ki",
                },
                "gpu": {
                    "r1": "2",
                    "r2": "4",
                },
                "gpu_memory": {
                    "r1": "200Ki",
                    "r2": "400Ki",
                },
            })
        self.assertEqual(expected, v)

        v = copy.deepcopy(self.v1)
        v /= self.v3
        expected = ClusterResource(
            params={
                "cpu": {
                    "r1": "4",
                },
                "memory": {
                    "r1": "200Ki",
                },
                "gpu": {
                    "r1": "1",
                },
                "gpu_memory": {
                    "r1": "100Ki",
                },
            })
        self.assertEqual(expected, v)
