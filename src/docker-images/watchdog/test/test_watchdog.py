# Copyright (c) Microsoft Corporation
# All rights reserved.
#
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and
# to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED *AS IS*, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING
# BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os
import sys
import unittest
import yaml
import json
import logging
import logging.config
import collections

import prometheus_client

sys.path.append(os.path.abspath("../src/"))

import watchdog

log = logging.getLogger(__name__)

class TestWatchdog(unittest.TestCase):
    """
    Test watchdog.py
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

    def tearDown(self):
        try:
            os.chdir(os.path.abspath(".."))
        except:
            pass

    def get_data_test_input(self, path):
        with open(path) as f:
            return f.read()

    def test_parse_pods_status(self):
        obj = json.loads(self.get_data_test_input("data/pods_list.json"))

        pod_gauge = watchdog.gen_pai_pod_gauge()
        container_gauge = watchdog.gen_pai_container_gauge()
        pod_info = collections.defaultdict(lambda : [])

        watchdog.process_pods_status(obj, pod_gauge, container_gauge, pod_info, [],
                watchdog.VcUsage())

        self.assertTrue(len(pod_gauge.samples) > 0)
        self.assertTrue(len(container_gauge.samples) > 0)

    def test_process_nodes_status(self):
        obj = json.loads(self.get_data_test_input("data/nodes_list.json"))

        gauges = watchdog.process_nodes_status(obj, {}, watchdog.ClusterGPUInfo())

        self.assertEqual(5, len(gauges))

        for gauge in gauges:
            self.assertTrue(len(gauge.samples) > 0)

    def test_process_pods_with_no_condition(self):
        obj = json.loads(self.get_data_test_input("data/no_condtion_pod.json"))

        pod_gauge = watchdog.gen_pai_pod_gauge()
        container_gauge = watchdog.gen_pai_container_gauge()
        pod_info = collections.defaultdict(lambda : [])

        watchdog.process_pods_status(obj, pod_gauge, container_gauge, pod_info, [],
                watchdog.VcUsage())

        self.assertTrue(len(pod_gauge.samples) > 0)
        self.assertEqual(0, len(container_gauge.samples))

    def test_process_pod_with_no_host_ip(self):
        obj = json.loads(self.get_data_test_input("data/no_condtion_pod.json"))

        class CustomCollector(object):
            def collect(self):
                pod_gauge = watchdog.gen_pai_pod_gauge()
                container_gauge = watchdog.gen_pai_container_gauge()
                pod_info = collections.defaultdict(lambda : [])

                watchdog.process_pods_status(obj,
                        pod_gauge, container_gauge, pod_info, [],
                        watchdog.VcUsage())

                yield pod_gauge
                yield container_gauge

        registry = CustomCollector()

        # expect no exception
        prometheus_client.write_to_textfile("/tmp/test_watchdog.prom", registry)

    def test_process_dlws_nodes_status(self):
        obj = json.loads(self.get_data_test_input("data/dlws_nodes_list.json"))

        pod_info = collections.defaultdict(lambda : [])
        pod_info["192.168.255.1"].append(watchdog.PodInfo("job1", False, 2))
        gauges = watchdog.process_nodes_status(obj, pod_info, watchdog.ClusterGPUInfo())

        self.assertEqual(5, len(gauges))

        self.assertEqual("k8s_node_gpu_available", gauges[1].name)
        self.assertEqual(1, len(gauges[1].samples))
        self.assertEqual(2, gauges[1].samples[0].value)
        self.assertEqual("k8s_node_preemptable_gpu_available", gauges[2].name)
        self.assertEqual(1, len(gauges[2].samples))
        self.assertEqual(2, gauges[2].samples[0].value)
        self.assertEqual("k8s_node_gpu_total", gauges[3].name)
        self.assertEqual(1, len(gauges[3].samples))
        self.assertEqual(4, gauges[3].samples[0].value)
        self.assertEqual("k8s_node_gpu_allocatable", gauges[4].name)
        self.assertEqual(1, len(gauges[4].samples))
        self.assertEqual(4, gauges[4].samples[0].value)

        for gauge in gauges:
            self.assertTrue(len(gauge.samples) > 0)

        for gauge in gauges[1:]:
            self.assertEqual("192.168.255.1", gauge.samples[0].labels["host_ip"])

    def test_process_dlws_nodes_status_with_unscheduable(self):
        obj = json.loads(self.get_data_test_input("data/dlws_nodes_list_with_unschedulable.json"))

        pod_info = collections.defaultdict(lambda : [])
        pod_info["192.168.255.1"].append(watchdog.PodInfo("job1", False, 2))
        gauges = watchdog.process_nodes_status(obj, pod_info, watchdog.ClusterGPUInfo())

        self.assertEqual(5, len(gauges))

        self.assertEqual("pai_node_count", gauges[0].name)
        self.assertEqual(1, len(gauges[0].samples))
        self.assertEqual("true", gauges[0].samples[0].labels["unschedulable"])
        self.assertEqual("k8s_node_gpu_available", gauges[1].name)
        self.assertEqual(1, len(gauges[1].samples))
        self.assertEqual(0, gauges[1].samples[0].value)
        self.assertEqual("k8s_node_preemptable_gpu_available", gauges[2].name)
        self.assertEqual(1, len(gauges[2].samples))
        self.assertEqual(0, gauges[2].samples[0].value)
        self.assertEqual("k8s_node_gpu_total", gauges[3].name)
        self.assertEqual(1, len(gauges[3].samples))
        self.assertEqual(4, gauges[3].samples[0].value)
        self.assertEqual("k8s_node_gpu_allocatable", gauges[4].name)
        self.assertEqual(1, len(gauges[4].samples))
        self.assertEqual(0, gauges[4].samples[0].value)

        for gauge in gauges:
            self.assertTrue(len(gauge.samples) > 0)

        for gauge in gauges[1:]:
            self.assertEqual("192.168.255.1", gauge.samples[0].labels["host_ip"])

    def test_process_vc_quota(self):
        obj = json.loads(self.get_data_test_input("data/vc_quota.json"))
        quota_info = watchdog.process_vc_quota(obj)

        target = {
                "platform": {"P40": 20},
                "vc1": {"P40": 6},
                "bert": {"P40": 0},
                "multimedia": {"P40": 0},
                "quantus": {"P40": 0},
                "relevance": {"P40": 0}
                }

        self.assertEqual(target, quota_info)

    def test_process_vc_info_real_case(self):
        vc_info = {
                "quantus": {"P40": 150},
                "relevance2": {"P40": 234},
                "relevance2-inf": {"P40": 40}
                }

        vc_usage = watchdog.VcUsage()

        vc_usage.add_preemptable_used("relevance2", "P40", 24)
        vc_usage.add_used("relevance2", "P40", 231)
        vc_usage.add_used("quantus", "P40", 125)

        cluster_gpu_info = watchdog.ClusterGPUInfo()
        cluster_gpu_info.capacity = 424
        cluster_gpu_info.available = 68
        cluster_gpu_info.allocatable = 423
        vc_total, vc_avail, vc_preemptive_avail, vc_unschedulable_gauge = \
                watchdog.gen_vc_metrics(vc_info, vc_usage, cluster_gpu_info)

        self.assertEqual(3, len(vc_total.samples))
        for sample in vc_total.samples:
            vc_name = sample.labels["vc_name"]
            gpu_type = sample.labels["gpu_type"]
            self.assertEqual(vc_info[vc_name][gpu_type], sample.value)

        target_vc_avail = {
                "quantus": {"P40": 25},
                "relevance2": {"P40": 2},
                "relevance2-inf": {"P40": 40}
                }

        self.assertEqual(3, len(vc_avail.samples))
        for sample in vc_avail.samples:
            vc_name = sample.labels["vc_name"]
            gpu_type = sample.labels["gpu_type"]
            self.assertEqual(target_vc_avail[vc_name][gpu_type],
                    sample.value, "vc " + vc_name + ", gpu " + gpu_type)

        target_vc_preemptive_avail = {
                "quantus": {"P40": 68},
                "relevance2": {"P40": 68},
                "relevance2-inf": {"P40": 68}
                }

        self.assertEqual(3, len(vc_preemptive_avail.samples))
        for sample in vc_preemptive_avail.samples:
            vc_name = sample.labels["vc_name"]
            gpu_type = sample.labels["gpu_type"]
            self.assertEqual(target_vc_preemptive_avail[vc_name][gpu_type],
                    sample.value, "vc " + vc_name)

        target_vc_unschedulable = {
                "quantus": {"P40": 0},
                "relevance2": {"P40": 1},
                "relevance2-inf": {"P40": 0}
                }
        self.assertEqual(3, len(vc_unschedulable_gauge.samples))
        for sample in vc_unschedulable_gauge.samples:
            vc_name = sample.labels["vc_name"]
            gpu_type = sample.labels["gpu_type"]
            self.assertEqual(target_vc_unschedulable[vc_name][gpu_type],
                    sample.value, "vc " + vc_name + ", gpu " + gpu_type)

    def test_process_vc_info(self):
        vc_info = {
                "default": {"P40": 10, "P80": 10},
                "platform": {"P40": 10},
                "relevance": {"P80": 4}
                }

        vc_usage = watchdog.VcUsage()

        vc_usage.add_preemptable_used("default", "P40", 8)
        vc_usage.add_preemptable_used("default", "P80", 2)
        vc_usage.add_used("default", "P40", 2)

        vc_usage.add_used("platform", "P40", 3)

        cluster_gpu_info = watchdog.ClusterGPUInfo()
        cluster_gpu_info.capacity = 34
        cluster_gpu_info.available = 29
        cluster_gpu_info.allocatable = 34
        vc_total, vc_avail, vc_preemptive_avail, vc_unschedulable_gauge = \
                watchdog.gen_vc_metrics(vc_info, vc_usage, cluster_gpu_info)

        self.assertEqual(4, len(vc_total.samples))
        for sample in vc_total.samples:
            vc_name = sample.labels["vc_name"]
            gpu_type = sample.labels["gpu_type"]
            self.assertEqual(vc_info[vc_name][gpu_type], sample.value)

        target_vc_avail = {
                "default": {"P40": 8, "P80": 10},
                "platform": {"P40": 7},
                "relevance": {"P80": 4}
                }

        self.assertEqual(4, len(vc_avail.samples))
        for sample in vc_avail.samples:
            vc_name = sample.labels["vc_name"]
            gpu_type = sample.labels["gpu_type"]
            self.assertEqual(target_vc_avail[vc_name][gpu_type],
                    sample.value, "vc " + vc_name + ", gpu " + gpu_type)

        target_vc_preemptive_avail = {
                "default": {"P40": 29, "P80": 29},
                "platform": {"P40": 29},
                "relevance": {"P80": 29}
                }

        self.assertEqual(4, len(vc_preemptive_avail.samples))
        for sample in vc_preemptive_avail.samples:
            vc_name = sample.labels["vc_name"]
            gpu_type = sample.labels["gpu_type"]
            self.assertEqual(target_vc_preemptive_avail[vc_name][gpu_type],
                    sample.value, "vc " + vc_name)

        target_vc_unschedulable = {
                "default": {"P40": 0, "P80": 0},
                "platform": {"P40": 0},
                "relevance": {"P80": 0}
                }
        for sample in vc_unschedulable_gauge.samples:
            vc_name = sample.labels["vc_name"]
            gpu_type = sample.labels["gpu_type"]
            self.assertEqual(target_vc_unschedulable[vc_name][gpu_type],
                    sample.value, "vc " + vc_name + ", gpu " + gpu_type)

    def test_gpu_accounting(self):
        vc_info = {
                "A": {"P40": 40},
                "B": {"P40": 40},
                "C": {"P40": 40}
                }

        vc_usage = watchdog.VcUsage()

        vc_usage.add_used("A", "P40", 40)
        vc_usage.add_used("B", "P40", 31)
        vc_usage.add_used("C", "P40", 0)

        cluster_gpu_info = watchdog.ClusterGPUInfo()
        cluster_gpu_info.capacity = 120
        cluster_gpu_info.available = 29
        cluster_gpu_info.allocatable = 100
        vc_total, vc_avail, vc_preemptive_avail, vc_unschedulable_gauge = \
                watchdog.gen_vc_metrics(vc_info, vc_usage, cluster_gpu_info)

        self.assertEqual(3, len(vc_total.samples))
        for sample in vc_total.samples:
            vc_name = sample.labels["vc_name"]
            gpu_type = sample.labels["gpu_type"]
            self.assertEqual(vc_info[vc_name][gpu_type], sample.value)

        target_vc_avail = {
                "A": {"P40": 0},
                "B": {"P40": 1},
                "C": {"P40": 27}
                }

        self.assertEqual(3, len(vc_avail.samples))
        for sample in vc_avail.samples:
            vc_name = sample.labels["vc_name"]
            gpu_type = sample.labels["gpu_type"]
            self.assertEqual(target_vc_avail[vc_name][gpu_type],
                    sample.value, "vc " + vc_name + ", gpu " + gpu_type)

        target_vc_preemptive_avail = {
                "A": {"P40": 29},
                "B": {"P40": 29},
                "C": {"P40": 29}
                }

        self.assertEqual(3, len(vc_preemptive_avail.samples))
        for sample in vc_preemptive_avail.samples:
            vc_name = sample.labels["vc_name"]
            gpu_type = sample.labels["gpu_type"]
            self.assertEqual(target_vc_preemptive_avail[vc_name][gpu_type],
                    sample.value, "vc " + vc_name)

        target_vc_unschedulable = {
                "A": {"P40": 0},
                "B": {"P40": 8},
                "C": {"P40": 13}
                }
        self.assertEqual(3, len(vc_unschedulable_gauge.samples))
        for sample in vc_unschedulable_gauge.samples:
            vc_name = sample.labels["vc_name"]
            gpu_type = sample.labels["gpu_type"]
            self.assertEqual(target_vc_unschedulable[vc_name][gpu_type],
                    sample.value, "vc " + vc_name)

    def test_process_pods_with_vc_usage(self):
        obj = json.loads(self.get_data_test_input("data/dlts_non_preemptable_pod.json"))

        pod_gauge = watchdog.gen_pai_pod_gauge()
        container_gauge = watchdog.gen_pai_container_gauge()
        pod_info = collections.defaultdict(lambda : [])

        vc_usage = watchdog.VcUsage()

        watchdog.parse_pod_item(obj, pod_gauge, container_gauge, pod_info, [],
                vc_usage)

        self.assertEqual(1, len(vc_usage.map))
        self.assertEqual(1, len(vc_usage.map["some_vc_name"]))
        self.assertEqual(1, vc_usage.map["some_vc_name"]["P40"][0])
        self.assertEqual(1, vc_usage.map["some_vc_name"]["P40"][1])

        obj = json.loads(self.get_data_test_input("data/dlts_preemptable_pod.json"))
        watchdog.parse_pod_item(obj, pod_gauge, container_gauge, pod_info, [],
                vc_usage)

        self.assertEqual(1, len(vc_usage.map))
        self.assertEqual(2, len(vc_usage.map["some_vc_name"]))
        # P40 do not change since preemptable pod using P80
        self.assertEqual(1, vc_usage.map["some_vc_name"]["P40"][0])
        self.assertEqual(1, vc_usage.map["some_vc_name"]["P40"][1])

        self.assertEqual(1, vc_usage.map["some_vc_name"]["P80"][0])
        self.assertEqual(0, vc_usage.map["some_vc_name"]["P80"][1])

    def test_parse_monitor_response_time(self):
        obj = json.loads(self.get_data_test_input("data/pods_with_response_time_monitor.json"))

        pod_gauge = watchdog.gen_pai_pod_gauge()
        container_gauge = watchdog.gen_pai_container_gauge()
        pod_info = collections.defaultdict(lambda : [])

        endpoints = []

        vc_usage = watchdog.VcUsage()

        watchdog.process_pods_status(obj, pod_gauge, container_gauge, pod_info, endpoints, vc_usage)

        self.assertEqual(2, len(endpoints))
        endpoint0 = endpoints[0]
        endpoint1 = endpoints[1]

        self.assertEqual("job-exporter", endpoint0.name)
        self.assertEqual("job-exporter", endpoint1.name)

        self.assertEqual("10.151.40.231", endpoint0.ip)
        self.assertEqual("10.151.40.227", endpoint1.ip)

        self.assertEqual(9102, endpoint0.port)
        self.assertEqual(9102, endpoint1.port)

        self.assertEqual("/healthz", endpoint0.path)
        self.assertEqual("/healthz", endpoint1.path)

        self.assertEqual(10, endpoint0.timeout)
        self.assertEqual(10, endpoint1.timeout)

if __name__ == '__main__':
    unittest.main()
