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
    def test_gpu_accounting(self):
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


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s',
            level=logging.INFO)
    unittest.main()
