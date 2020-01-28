#!/usr/bin/env python3

import unittest
import logging
import logging.config

import quota

from cluster_resource import ClusterResource

log = logging.getLogger(__name__)


class TestQuota(unittest.TestCase):
    """
    Test quota.py
    """

    def test_gpu_accounting_idle_gpus_become_unscheduable(self):
        vc_info = {
            "A": {"P40": 40},
            "B": {"P40": 40},
            "C": {"P40": 40},
        }

        vc_usage = {
            "A": {"P40": 40},
            "B": {"P40": 31},
            "C": {"P40": 0},
        }

        cluster_total = {"P40": 120}
        cluster_available = {"P40": 29}
        cluster_unschedulable = {"P40": 20}

        result = quota.calculate_vc_gpu_counts(
            cluster_total,
            cluster_available,
            cluster_unschedulable,
            vc_info,
            vc_usage)

        vc_total, vc_used, vc_available, vc_unschedulable = result

        self.assertEqual(vc_info, vc_total)
        self.assertEqual(vc_usage, vc_used)

        target_vc_available = {
            "A": {"P40": 0},
            "B": {"P40": 1},
            "C": {"P40": 27},
        }

        self.assertEqual(target_vc_available, vc_available)

        target_vc_unschedulable = {
            "A": {"P40": 0},
            "B": {"P40": 8},
            "C": {"P40": 13},
        }

        self.assertEqual(target_vc_unschedulable, vc_unschedulable)

    def test_gpu_accounting_move_quota_from_one_vc_to_another(self):
        vc_info = {
            "A": {"P40": 20},
            "B": {"P40": 20},
        }

        # previous A has quota of 30, and A used them all, later admin moved
        # 10 to B
        vc_usage = {
            "A": {"P40": 30},
            "B": {"P40": 5},
        }

        cluster_total = {"P40": 40}
        cluster_available = {"P40": 5}
        cluster_unschedulable = {}

        result = quota.calculate_vc_gpu_counts(
            cluster_total,
            cluster_available,
            cluster_unschedulable,
            vc_info,
            vc_usage)

        vc_total, vc_used, vc_available, vc_unschedulable = result

        self.assertEqual(vc_info, vc_total)
        self.assertEqual(vc_usage, vc_used)

        target_vc_available = {
            "A": {"P40": 0},
            "B": {"P40": 5},
        }

        self.assertEqual(target_vc_available, vc_available)

        target_vc_unschedulable = {
            "A": {"P40": 0},
            "B": {"P40": 10},
        }

        self.assertEqual(target_vc_unschedulable, vc_unschedulable)

    def test_gpu_accounting_real_case(self):
        vc_info = {
            "platform": {"P40": 48},
            "relevance": {"P40": 200},
            "quantus": {"P40": 100},
            "AU": {"P40": 20},
        }

        vc_usage = {
            "platform": {"P40": 57},
            "relevance": {"P40": 164},
            "quantus": {"P40": 93},
            "AU": {"P40": 0},
        }

        cluster_total = {"P40": 368}
        cluster_available = {"P40": 54}
        cluster_unschedulable = {}

        result = quota.calculate_vc_gpu_counts(
            cluster_total,
            cluster_available,
            cluster_unschedulable,
            vc_info,
            vc_usage)

        vc_total, vc_used, vc_available, vc_unschedulable = result

        self.assertEqual(vc_info, vc_total)
        self.assertEqual(vc_usage, vc_used)

        target_vc_available = {
            "platform": {"P40": 0},
            "relevance": {"P40": 30},
            "quantus": {"P40": 6},
            "AU": {"P40": 17},
        }

        self.assertEqual(target_vc_available, vc_available)

        target_vc_unschedulable = {
            "platform": {"P40": 0},
            "relevance": {"P40": 6},
            "quantus": {"P40": 1},
            "AU": {"P40": 3},
        }

        self.assertEqual(target_vc_unschedulable, vc_unschedulable)

    def test_gpu_accounting_real_case2(self):
        vc_info = {
            "quantus": {"P40": 150},
            "relevance2": {"P40": 234},
            "relevance2-inf": {"P40": 40},
        }

        vc_usage = {
            "quantus": {"P40": 125},
            "relevance2": {"P40": 231},
            "relevance2-inf": {"P40": 0},
        }

        cluster_total = {"P40": 424}
        cluster_available = {"P40": 68}
        cluster_unschedulable = {"P40": 1}

        result = quota.calculate_vc_gpu_counts(
            cluster_total,
            cluster_available,
            cluster_unschedulable,
            vc_info,
            vc_usage)

        vc_total, vc_used, vc_available, vc_unschedulable = result

        self.assertEqual(vc_info, vc_total)
        self.assertEqual(vc_usage, vc_used)

        target_vc_available = {
            "quantus": {"P40": 25},
            "relevance2": {"P40": 2},
            "relevance2-inf": {"P40": 40},
        }

        self.assertEqual(target_vc_available, vc_available)

        target_vc_unschedulable = {
            "quantus": {"P40": 0},
            "relevance2": {"P40": 1},
            "relevance2-inf": {"P40": 0},
        }

        self.assertEqual(target_vc_unschedulable, vc_unschedulable)

    def test_calculate_vc_resources(self):
        cluster_capacity = ClusterResource(resource={
            "cpu": {
                "r1": 30,
                "r2": 40,
                "": 4
            },
            "memory": {
                "r1": "300Gi",
                "r2": "400Gi",
                "": "16Gi"
            }
        })
        cluster_avail = ClusterResource(resource={
            "cpu": {
                "r1": 17,
                "r2": 2,
                "": 2
            },
            "memory": {
                "r1": "230Gi",
                "r2": "100Gi",
                "": "8Gi"
            }
        })
        cluster_reserved = ClusterResource(resource={
            "cpu": {
                "r1": 4
            },
            "memory": {
                "r1": "20Gi"
            }
        })
        vc_info = {
            "vc1": ClusterResource(resource={
                "cpu": {
                    "r1": 10,
                    "r2": 40
                },
                "memory": {
                    "r1": "100Gi",
                    "r2": "400Gi"
                }
            }),
            "vc2": ClusterResource(resource={
                "cpu": {
                    "r1": 20,
                    "": 4
                },
                "memory": {
                    "r1": "200Gi",
                    "": "16Gi"
                }
            })
        }
        vc_usage = {
            "vc1": ClusterResource(resource={
                "cpu": {
                    "r1": 9,
                    "r2": 38
                },
                "memory": {
                    "r1": "50Gi",
                    "r2": "300Gi"
                }
            }),
            "vc2": ClusterResource(resource={
                "cpu": {
                    "": 2
                },
                "memory": {
                    "": "8Gi"
                }
            })
        }

        result = quota.calculate_vc_resources(cluster_capacity, cluster_avail,
                                              cluster_reserved, vc_info,
                                              vc_usage)
        vc_total, vc_used, vc_avail, vc_unschedulable = result

        self.assertEqual(vc_info, vc_total)
        self.assertEqual(vc_usage, vc_used)

        expected_vc_avail = {
            "vc1": ClusterResource(resource={
                "cpu": {
                    "r1": 0,
                    "r2": 2
                },
                "memory": {
                    "r1": "46528812373",
                    "r2": "100Gi"
                }
            }),
            "vc2": ClusterResource(resource={
                "cpu": {
                    "r1": 17,
                    "": 2
                },
                "memory": {
                    "r1": "200431807146",
                    "": "8Gi"
                }
            })
        }
        self.assertEqual(expected_vc_avail, vc_avail)

        expected_vc_unschedulable = {
            "vc1": ClusterResource(resource={
                "cpu": {
                    "r1": 1,
                    "r2": 0
                },
                "memory": {
                    "r1": "7158278827",
                    "r2": "0"
                }
            }),
            "vc2": ClusterResource(resource={
                "cpu": {
                    "r1": 3,
                    "": 0
                },
                "memory": {
                    "r1": "14316557654",
                    "": "0"
                }
            })
        }
        self.assertEqual(expected_vc_unschedulable, vc_unschedulable)


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s',
                        level=logging.INFO)
    unittest.main()
