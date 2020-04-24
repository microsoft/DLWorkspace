#!/usr/bin/env python3

import os
import sys
import unittest
import yaml
import json
import logging
import logging.config
import datetime

sys.path.append(os.path.abspath(".."))

import reporter

logger = logging.getLogger(__name__)


class TestReporter(unittest.TestCase):
    """
    Test reporter.py
    """
    def setUp(self):
        try:
            os.chdir(os.path.abspath("test"))
        except:
            pass

        configuration_path = "logging.yaml"

        if os.path.exists(configuration_path):
            with open(configuration_path, 'rt') as f:
                logging_configuration = yaml.safe_load(f.read())
            logging.config.dictConfig(logging_configuration)
            logging.getLogger()

    def load_data(self, path):
        with open(path) as f:
            return f.read()

    def get_samples(self, metrics, target_name, labels):
        result = []

        for m in metrics:
            if m.name != target_name:
                continue
            for sample in m.samples:
                add = True
                for k, v in labels.items():
                    if sample.labels.get(k) != v:
                        add = False
                        break
                if add:
                    result.append(sample)
        return result

    def test_calculate(self):
        step_seconds = 300
        idleness_threshold = 0
        end = datetime.datetime.fromtimestamp(1587768375)

        calculator = reporter.IdlenessCalculator(step_seconds,
                                                 idleness_threshold, end)
        raw = json.loads(self.load_data("data/raw.json"))
        result = reporter.calculate(raw, calculator)
        self.assertTrue(result["31d"]["booked"] >= result["14d"]["booked"])
        self.assertTrue(result["14d"]["booked"] >= result["7d"]["booked"])

        self.assertTrue(result["31d"]["idle"] >= result["14d"]["idle"])
        self.assertTrue(result["14d"]["idle"] >= result["7d"]["idle"])

        self.assertEqual(50.0, result["31d"]["next"]["vvv"]["assigned_util"])
        self.assertEqual(100.0, result["31d"]["next"]["vvv"]["nonidle_util"])
        self.assertEqual(600, result["31d"]["next"]["vvv"]["booked"])
        self.assertEqual(300, result["31d"]["next"]["vvv"]["idle"])

        self.assertEqual(20.0,
                         result["31d"]["next"]["platform"]["assigned_util"])
        self.assertEqual(20.0,
                         result["31d"]["next"]["platform"]["nonidle_util"])
        self.assertEqual(300, result["31d"]["next"]["platform"]["booked"])
        self.assertEqual(0, result["31d"]["next"]["platform"]["idle"])

    def assert_metric_value(self, metrics, target_name, labels, value):
        target = self.get_samples(metrics, target_name, labels)
        self.assertEqual(1, len(target), "zero/multiple target %s" % (target))
        self.assertEqual(value, target[0].value)

    def test_walk_exported_regiter(self):
        obj = json.loads(self.load_data("data/exported.json"))

        collector = reporter.CustomCollector(None)
        metrics = collector.walk_exported_register(obj)
        self.assert_metric_value(metrics, "cluster_booked_gpu_second",
                                 {"since": "31d"}, 900)
        self.assert_metric_value(metrics, "cluster_idle_gpu_second",
                                 {"since": "31d"}, 300)
        self.assert_metric_value(metrics, "cluster_non_idle_utils",
                                 {"since": "31d"}, 60)
        self.assert_metric_value(metrics, "cluster_assigned_utils",
                                 {"since": "31d"}, 40)

        self.assert_metric_value(metrics, "cluster_booked_gpu_second",
                                 {"since": "14d"}, 900)
        self.assert_metric_value(metrics, "cluster_idle_gpu_second",
                                 {"since": "14d"}, 300)
        self.assert_metric_value(metrics, "cluster_non_idle_utils",
                                 {"since": "14d"}, 60)
        self.assert_metric_value(metrics, "cluster_assigned_utils",
                                 {"since": "14d"}, 40)

        self.assert_metric_value(metrics, "cluster_booked_gpu_second",
                                 {"since": "7d"}, 0)
        self.assert_metric_value(metrics, "cluster_idle_gpu_second",
                                 {"since": "7d"}, 0)
        self.assert_metric_value(metrics, "cluster_non_idle_utils",
                                 {"since": "7d"}, 0)
        self.assert_metric_value(metrics, "cluster_assigned_utils",
                                 {"since": "7d"}, 0)

        self.assert_metric_value(metrics, "vc_booked_gpu_second", {
            "since": "31d",
            "vc": "platform"
        }, 300)
        self.assert_metric_value(metrics, "vc_booked_gpu_second", {
            "since": "31d",
            "vc": "vvv"
        }, 600)
        self.assert_metric_value(metrics, "vc_booked_gpu_second", {
            "since": "14d",
            "vc": "platform"
        }, 300)
        self.assert_metric_value(metrics, "vc_booked_gpu_second", {
            "since": "14d",
            "vc": "vvv"
        }, 600)
        self.assert_metric_value(metrics, "vc_idle_gpu_second", {
            "since": "31d",
            "vc": "platform"
        }, 0)
        self.assert_metric_value(metrics, "vc_idle_gpu_second", {
            "since": "31d",
            "vc": "vvv"
        }, 300)
        self.assert_metric_value(metrics, "vc_idle_gpu_second", {
            "since": "14d",
            "vc": "platform"
        }, 0)
        self.assert_metric_value(metrics, "vc_idle_gpu_second", {
            "since": "14d",
            "vc": "vvv"
        }, 300)
        self.assert_metric_value(metrics, "vc_non_idle_utils", {
            "since": "31d",
            "vc": "platform"
        }, 20)
        self.assert_metric_value(metrics, "vc_non_idle_utils", {
            "since": "31d",
            "vc": "vvv"
        }, 100)
        self.assert_metric_value(metrics, "vc_non_idle_utils", {
            "since": "14d",
            "vc": "platform"
        }, 20)
        self.assert_metric_value(metrics, "vc_non_idle_utils", {
            "since": "14d",
            "vc": "vvv"
        }, 100)
        self.assert_metric_value(metrics, "vc_assigned_utils", {
            "since": "31d",
            "vc": "platform"
        }, 20)
        self.assert_metric_value(metrics, "vc_assigned_utils", {
            "since": "31d",
            "vc": "vvv"
        }, 50)
        self.assert_metric_value(metrics, "vc_assigned_utils", {
            "since": "14d",
            "vc": "platform"
        }, 20)
        self.assert_metric_value(metrics, "vc_assigned_utils", {
            "since": "14d",
            "vc": "vvv"
        }, 50)
        self.assert_metric_value(metrics, "user_booked_gpu_second", {
            "since": "31d",
            "vc": "platform",
            "user": "bbb"
        }, 300)
        self.assert_metric_value(metrics, "user_booked_gpu_second", {
            "since": "31d",
            "vc": "vvv",
            "user": "aaa"
        }, 600)
        self.assert_metric_value(metrics, "user_booked_gpu_second", {
            "since": "14d",
            "vc": "platform",
            "user": "bbb"
        }, 300)
        self.assert_metric_value(metrics, "user_booked_gpu_second", {
            "since": "14d",
            "vc": "vvv",
            "user": "aaa"
        }, 600)
        self.assert_metric_value(metrics, "user_idle_gpu_second", {
            "since": "31d",
            "vc": "platform",
            "user": "bbb"
        }, 0)
        self.assert_metric_value(metrics, "user_idle_gpu_second", {
            "since": "31d",
            "vc": "vvv",
            "user": "aaa"
        }, 300)
        self.assert_metric_value(metrics, "user_idle_gpu_second", {
            "since": "14d",
            "vc": "platform",
            "user": "bbb"
        }, 0)
        self.assert_metric_value(metrics, "user_idle_gpu_second", {
            "since": "14d",
            "vc": "vvv",
            "user": "aaa"
        }, 300)
        self.assert_metric_value(metrics, "user_non_idle_utils", {
            "since": "31d",
            "vc": "platform",
            "user": "bbb"
        }, 20)
        self.assert_metric_value(metrics, "user_non_idle_utils", {
            "since": "31d",
            "vc": "vvv",
            "user": "aaa"
        }, 100)
        self.assert_metric_value(metrics, "user_non_idle_utils", {
            "since": "14d",
            "vc": "platform",
            "user": "bbb"
        }, 20)
        self.assert_metric_value(metrics, "user_non_idle_utils", {
            "since": "14d",
            "vc": "vvv",
            "user": "aaa"
        }, 100)
        self.assert_metric_value(metrics, "user_assigned_utils", {
            "since": "31d",
            "vc": "platform",
            "user": "bbb"
        }, 20)
        self.assert_metric_value(metrics, "user_assigned_utils", {
            "since": "31d",
            "vc": "vvv",
            "user": "aaa"
        }, 50)
        self.assert_metric_value(metrics, "user_assigned_utils", {
            "since": "14d",
            "vc": "platform",
            "user": "bbb"
        }, 20)
        self.assert_metric_value(metrics, "user_assigned_utils", {
            "since": "14d",
            "vc": "vvv",
            "user": "aaa"
        }, 50)
        self.assert_metric_value(
            metrics, "job_booked_gpu_second", {
                "since": "31d",
                "vc": "platform",
                "user": "bbb",
                "job_id": "89ba301e-58d0-4ce5-ba6b-5781a7926f63"
            }, 300)
        self.assert_metric_value(
            metrics, "job_booked_gpu_second", {
                "since": "31d",
                "vc": "vvv",
                "user": "aaa",
                "job_id": "f29f07ab-8510-4ad9-ac24-363bd7271571"
            }, 600)
        self.assert_metric_value(
            metrics, "job_booked_gpu_second", {
                "since": "14d",
                "vc": "platform",
                "user": "bbb",
                "job_id": "89ba301e-58d0-4ce5-ba6b-5781a7926f63"
            }, 300)
        self.assert_metric_value(
            metrics, "job_booked_gpu_second", {
                "since": "14d",
                "vc": "vvv",
                "user": "aaa",
                "job_id": "f29f07ab-8510-4ad9-ac24-363bd7271571"
            }, 600)
        self.assert_metric_value(
            metrics, "job_idle_gpu_second", {
                "since": "31d",
                "vc": "platform",
                "user": "bbb",
                "job_id": "89ba301e-58d0-4ce5-ba6b-5781a7926f63"
            }, 0)
        self.assert_metric_value(
            metrics, "job_idle_gpu_second", {
                "since": "31d",
                "vc": "vvv",
                "user": "aaa",
                "job_id": "f29f07ab-8510-4ad9-ac24-363bd7271571"
            }, 300)
        self.assert_metric_value(
            metrics, "job_idle_gpu_second", {
                "since": "14d",
                "vc": "platform",
                "user": "bbb",
                "job_id": "89ba301e-58d0-4ce5-ba6b-5781a7926f63"
            }, 0)
        self.assert_metric_value(
            metrics, "job_idle_gpu_second", {
                "since": "14d",
                "vc": "vvv",
                "user": "aaa",
                "job_id": "f29f07ab-8510-4ad9-ac24-363bd7271571"
            }, 300)
        self.assert_metric_value(
            metrics, "job_non_idle_utils", {
                "since": "31d",
                "vc": "platform",
                "user": "bbb",
                "job_id": "89ba301e-58d0-4ce5-ba6b-5781a7926f63"
            }, 20)
        self.assert_metric_value(
            metrics, "job_non_idle_utils", {
                "since": "31d",
                "vc": "vvv",
                "user": "aaa",
                "job_id": "f29f07ab-8510-4ad9-ac24-363bd7271571"
            }, 100)
        self.assert_metric_value(
            metrics, "job_non_idle_utils", {
                "since": "14d",
                "vc": "platform",
                "user": "bbb",
                "job_id": "89ba301e-58d0-4ce5-ba6b-5781a7926f63"
            }, 20)
        self.assert_metric_value(
            metrics, "job_non_idle_utils", {
                "since": "14d",
                "vc": "vvv",
                "user": "aaa",
                "job_id": "f29f07ab-8510-4ad9-ac24-363bd7271571"
            }, 100)
        self.assert_metric_value(
            metrics, "job_assigned_utils", {
                "since": "31d",
                "vc": "platform",
                "user": "bbb",
                "job_id": "89ba301e-58d0-4ce5-ba6b-5781a7926f63"
            }, 20)
        self.assert_metric_value(
            metrics, "job_assigned_utils", {
                "since": "31d",
                "vc": "vvv",
                "user": "aaa",
                "job_id": "f29f07ab-8510-4ad9-ac24-363bd7271571"
            }, 50)
        self.assert_metric_value(
            metrics, "job_assigned_utils", {
                "since": "14d",
                "vc": "platform",
                "user": "bbb",
                "job_id": "89ba301e-58d0-4ce5-ba6b-5781a7926f63"
            }, 20)
        self.assert_metric_value(
            metrics, "job_assigned_utils", {
                "since": "14d",
                "vc": "vvv",
                "user": "aaa",
                "job_id": "f29f07ab-8510-4ad9-ac24-363bd7271571"
            }, 50)


if __name__ == '__main__':
    unittest.main()
