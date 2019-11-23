import os
import sys
import unittest
import yaml
import json
import logging
import logging.config
import collections

import quota

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

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s',
            level=logging.INFO)
    unittest.main()
