#!/usr/bin/env python3

import copy

from unittest import TestCase
from cluster_resource import ClusterResource
from resource_stat import Cpu, Memory


class TestClusterResource(TestCase):
    def setUp(self):
        a_res = {
            "cpu": {
                "r1": "10",
                "r2": "100"
            },
            "memory": {
                "r1": "100Ki",
                "r2": "200Ki"
            }
        }
        self.a = ClusterResource(resource=a_res)

        b_res = {
            "cpu": {
                "r1": "100",
                "r2": "10"
            },
            "memory": {
                "r1": "300Ki",
                "r2": "100Ki"
            }
        }
        self.b = ClusterResource(resource=b_res)

        c_res = {
            "cpu": {
                "r1": "10",
                "": "100"
            },
            "memory": {
                "r1": "100Ki",
                "": "200Ki"
            }
        }

        self.scalar = 0.8

        d_res = {
            "cpu": {
                "r1": "0.5",
                "r2": "0.2"
            },
            "memory": {
                "r1": "0.8",
                "r2": "0.5"
            }
        }
        self.c = ClusterResource(resource=d_res)

    def test_init_from_params(self):
        regular_params = {
            "jobtrainingtype": "RegularJob",
            "sku": "r1"
        }
        r_res = ClusterResource(params=regular_params)
        self.assertEqual(Cpu({"r1": 1}), r_res.cpu)
        self.assertEqual(Memory(), r_res.memory)

        distributed_params = {
            "jobtrainingtype": "PSDistJob",
            "numps": 1,
            "numpsworker": 2,
            "cpurequest": 4,
            "memoryrequest": 102400
        }
        d_res = ClusterResource(params=distributed_params)
        self.assertEqual(Cpu({"": 9}), d_res.cpu)
        self.assertEqual(Memory({"": 204800}), d_res.memory)

        unrecognized_params = {
            "jobtrainingtype": "Unknown"
        }
        u_res = ClusterResource(params=unrecognized_params)
        self.assertEqual(Cpu(), u_res.cpu)
        self.assertEqual(Memory(), u_res.memory)

    def test_init_from_resource(self):
        res0 = {}
        ret0 = ClusterResource(resource=res0)
        self.assertEqual(Cpu(), ret0.cpu)
        self.assertEqual(Memory(), ret0.memory)

        res1 = {
            "cpu": {
                "r1": "1m"
            }
        }
        ret1 = ClusterResource(resource=res1)
        self.assertEqual(Cpu({"r1": "1m"}), ret1.cpu)
        self.assertEqual(Memory(), ret1.memory)

        res2 = {
            "memory": {
                "r1": "100Mi"
            }
        }
        ret2 = ClusterResource(resource=res2)
        self.assertEqual(Cpu(), ret2.cpu)
        self.assertEqual(Memory({"r1": "100Mi"}), ret2.memory)

        res3 = {
            "cpu": {
                "r1": "1m"
            },
            "memory": {
                "r1": "100Mi"
            }
        }
        ret3 = ClusterResource(resource=res3)
        self.assertEqual(Cpu({"r1": "1m"}), ret3.cpu)
        self.assertEqual(Memory({"r1": "100Mi"}), ret3.memory)

    def test_floor_ceil(self):
        res = {
            "cpu": {
                "r1": "10.4"
            },
            "memory": {
                "r1": "199.9"
            }
        }
        ret = ClusterResource(resource=res)
        ret_floor = ret.floor()
        self.assertEqual(Cpu({"r1": "10"}), ret_floor.cpu)
        self.assertEqual(Memory({"r1": "199"}), ret_floor.memory)

        ret_ceil = ret.ceil()
        self.assertEqual(Cpu({"r1": "11"}), ret_ceil.cpu)
        self.assertEqual(Memory({"r1": "200"}), ret_ceil.memory)

    def test_min_zero(self):
        res = {
            "cpu": {
                "r1": "-10m"
            },
            "memory": {
                "r1": "-100Ki"
            }
        }
        ret = ClusterResource(resource=res)
        ret_min_zero = ret.min_zero()
        self.assertEqual(Cpu(), ret_min_zero.cpu)
        self.assertEqual(Memory(), ret_min_zero.memory)

    def test_prune(self):
        res = {
            "cpu": {
                "r1": "0"
            },
            "memory": {
                "r1": "0"
            }
        }
        ret = ClusterResource(resource=res)
        ret_prune = ret.prune()
        self.assertEqual(Cpu(), ret_prune.cpu)
        self.assertEqual(Memory(), ret_prune.memory)

    def test_repr(self):
        res = {
            "cpu": {
                "r1": "1m"
            },
            "memory": {
                "r1": "100Ki"
            }
        }
        ret = ClusterResource(resource=res)
        self.assertEqual("cpu: {'r1': '%s'}. memory: {'r1': '%sB'}." %
                         (0.001, float(102400)), repr(ret))

    def test_eq(self):
        self.assertTrue(self.a == self.a)
        self.assertFalse(self.a == self.b)

    def test_ge(self):
        self.assertFalse(self.a >= self.b)

    def test_add(self):
        result = self.a + self.b
        expected = ClusterResource(resource={
            "cpu": {
                "r1": "110",
                "r2": "110"
            },
            "memory": {
                "r1": "400Ki",
                "r2": "300Ki"
            }
        })
        self.assertEqual(expected, result)

    def test_iadd(self):
        self.a += self.b
        expected = ClusterResource(resource={
            "cpu": {
                "r1": "110",
                "r2": "110"
            },
            "memory": {
                "r1": "400Ki",
                "r2": "300Ki"
            }
        })
        self.assertEqual(expected, self.a)

    def test_sub(self):
        result = self.a - self.b
        expected = ClusterResource(resource={
            "cpu": {
                "r1": "-90",
                "r2": "90"
            },
            "memory": {
                "r1": "-200Ki",
                "r2": "100Ki"
            }
        })
        self.assertEqual(expected, result)

    def test_isub(self):
        self.a -= self.b
        expected = ClusterResource(resource={
            "cpu": {
                "r1": "-90",
                "r2": "90"
            },
            "memory": {
                "r1": "-200Ki",
                "r2": "100Ki"
            }
        })
        self.assertEqual(expected, self.a)

    def test_mul(self):
        result = self.a * self.scalar
        expected = ClusterResource(resource={
            "cpu": {
                "r1": "8",
                "r2": "80"
            },
            "memory": {
                "r1": "80Ki",
                "r2": "160Ki"
            }
        })
        self.assertEqual(expected, result)

        result = self.a * self.c
        expected = ClusterResource(resource={
            "cpu": {
                "r1": "5",
                "r2": "20"
            },
            "memory": {
                "r1": "80Ki",
                "r2": "100Ki"
            }
        })
        self.assertEqual(expected, result)

    def test_imul(self):
        v = copy.deepcopy(self.a)
        v *= self.scalar
        expected = ClusterResource(resource={
            "cpu": {
                "r1": "8",
                "r2": "80"
            },
            "memory": {
                "r1": "80Ki",
                "r2": "160Ki"
            }
        })
        self.assertEqual(expected, v)

        v = copy.deepcopy(self.a)
        v *= self.c
        expected = ClusterResource(resource={
            "cpu": {
                "r1": "5",
                "r2": "20"
            },
            "memory": {
                "r1": "80Ki",
                "r2": "100Ki"
            }
        })
        self.assertEqual(expected, v)

    def test_truediv(self):
        result = self.a / self.scalar
        expected = ClusterResource(resource={
            "cpu": {
                "r1": "12.5",
                "r2": "125"
            },
            "memory": {
                "r1": "125Ki",
                "r2": "250Ki"
            }
        })
        self.assertEqual(expected, result)

        result = self.a / self.c
        expected = ClusterResource(resource={
            "cpu": {
                "r1": "20",
                "r2": "500"
            },
            "memory": {
                "r1": "125Ki",
                "r2": "400Ki"
            }
        })
        self.assertEqual(expected, result)

    def test_idiv(self):
        v = copy.deepcopy(self.a)
        v /= self.scalar
        expected = ClusterResource(resource={
            "cpu": {
                "r1": "12.5",
                "r2": "125"
            },
            "memory": {
                "r1": "125Ki",
                "r2": "250Ki"
            }
        })
        self.assertEqual(expected, v)

        v = copy.deepcopy(self.a)
        v /= self.c
        expected = ClusterResource(resource={
            "cpu": {
                "r1": "20",
                "r2": "500"
            },
            "memory": {
                "r1": "125Ki",
                "r2": "400Ki"
            }
        })
        self.assertEqual(expected, v)
