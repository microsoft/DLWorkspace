#!/usr/bin/env python3

import logging
import os
import sys
import unittest

sys.path.append(os.path.abspath("../src/"))

from util import State, Node, Job
from rule import Rule, K8sGpuRule, DcgmEccDBERule, instantiate_rules

logger = logging.getLogger(__name__)


class MockRestUtil(object):
    def __init__(self):
        self.data = []

    def get_job_status(self, job_id):
        try:
            return self.data.pop(0)
        except IndexError:
            return None


class MockPrometheusUtil(object):
    def __init__(self):
        self.data = []

    def query(self, query):
        try:
            return self.data.pop(0)
        except IndexError:
            return None


class TestRuleInstantiation(unittest.TestCase):
    def test_rule_instantiation(self):
        rules = instantiate_rules(None)
        self.assertEqual(0, len(rules))

        rules = instantiate_rules([])
        self.assertEqual(0, len(rules))

        # Sanity check on all rules
        rules = instantiate_rules(list(Rule.subclasses.keys()))
        for rule in rules:
            self.assertTrue(rule.__class__.__name__ in Rule.subclasses)


class TestRule(unittest.TestCase):
    def create_rule(self):
        self.rule = Rule("dummy_metric")

    def setUp(self):
        self.create_rule()
        self.rule.rest_util = MockRestUtil()
        self.rule.prometheus_util = MockPrometheusUtil()
        self.job = Job("job1", "user1", "vc1")
        self.node = Node("node1", "192.168.0.1", True, False, 4,
                         State.IN_SERVICE, None)
        self.node.jobs = {"job1": self.job}

    def update_data_and_validate(self, query_data):
        for q_data in query_data:
            self.rule.prometheus_util.data.append(q_data)

        self.rule.update_data()

        i = 0
        for metric in self.rule.metrics:
            self.assertEqual(query_data[i]["data"]["result"],
                             self.rule.data["current"][metric])
            i += 1
            self.assertEqual(query_data[i]["data"]["result"],
                             self.rule.data["interval"][metric])
            i += 1

    def test_check_health(self):
        pass

    def test_prepare(self):
        # Job is in scheduling state
        self.rule.rest_util.data.append({"jobStatus": "scheduling"})
        self.assertFalse(self.rule.prepare(self.node))

        # Job is in running state
        self.rule.rest_util.data.append({"jobStatus": "running"})
        self.assertFalse(self.rule.prepare(self.node))

        # Job is in finished
        self.rule.rest_util.data.append({"jobStatus": "finished"})
        self.assertTrue(self.rule.prepare(self.node))


class TestK8sGpuRule(TestRule):
    def create_rule(self):
        self.rule = K8sGpuRule()

    def test_check_health(self):
        # expected > total && total > allocatable
        k8s_node_gpu_total_data = {'status': 'success', 'data': {'resultType': 'vector', 'result': [{'metric': {'__name__': 'k8s_node_gpu_total', 'exporter_name': 'watchdog', 'host_ip': '192.168.0.1', 'instance': '192.168.255.1:9101', 'job': 'serivce_exporter', 'scraped_from': 'watchdog-664db8579f-69shf'}, 'value': [1591919499.601, '3']}]}}
        k8s_node_gpu_allocatable_data = {'status': 'success', 'data': {'resultType': 'vector', 'result': [{'metric': {'__name__': 'k8s_node_gpu_allocatable', 'exporter_name': 'watchdog', 'host_ip': '192.168.0.1', 'instance': '192.168.255.1:9101', 'job': 'serivce_exporter', 'scraped_from': 'watchdog-664db8579f-69shf'}, 'value': [1591919627.21, '0']}]}}

        self.update_data_and_validate(
            [k8s_node_gpu_total_data, k8s_node_gpu_total_data,
             k8s_node_gpu_allocatable_data, k8s_node_gpu_allocatable_data])

        self.assertFalse(self.rule.check_health(self.node))
        self.assertFalse(self.rule.check_health(self.node, stat="current"))

        # expected > total && total == allocatable
        k8s_node_gpu_total_data = {'status': 'success', 'data': {'resultType': 'vector', 'result': [{'metric': {'__name__': 'k8s_node_gpu_total', 'exporter_name': 'watchdog', 'host_ip': '192.168.0.1', 'instance': '192.168.255.1:9101', 'job': 'serivce_exporter', 'scraped_from': 'watchdog-664db8579f-69shf'}, 'value': [1591919499.601, '3']}]}}
        k8s_node_gpu_allocatable_data = {'status': 'success', 'data': {'resultType': 'vector', 'result': [{'metric': {'__name__': 'k8s_node_gpu_allocatable', 'exporter_name': 'watchdog', 'host_ip': '192.168.0.1', 'instance': '192.168.255.1:9101', 'job': 'serivce_exporter', 'scraped_from': 'watchdog-664db8579f-69shf'}, 'value': [1591919627.21, '3']}]}}

        self.update_data_and_validate(
            [k8s_node_gpu_total_data, k8s_node_gpu_total_data,
             k8s_node_gpu_allocatable_data, k8s_node_gpu_allocatable_data])

        self.assertFalse(self.rule.check_health(self.node))
        self.assertFalse(self.rule.check_health(self.node, stat="current"))

        # expected == total && total > allocatable
        k8s_node_gpu_total_data = {'status': 'success', 'data': {'resultType': 'vector', 'result': [{'metric': {'__name__': 'k8s_node_gpu_total', 'exporter_name': 'watchdog', 'host_ip': '192.168.0.1', 'instance': '192.168.255.1:9101', 'job': 'serivce_exporter', 'scraped_from': 'watchdog-664db8579f-69shf'}, 'value': [1591919499.601, '4']}]}}
        k8s_node_gpu_allocatable_data = {'status': 'success', 'data': {'resultType': 'vector', 'result': [{'metric': {'__name__': 'k8s_node_gpu_allocatable', 'exporter_name': 'watchdog', 'host_ip': '192.168.0.1', 'instance': '192.168.255.1:9101', 'job': 'serivce_exporter', 'scraped_from': 'watchdog-664db8579f-69shf'}, 'value': [1591919627.21, '1']}]}}

        self.update_data_and_validate(
            [k8s_node_gpu_total_data, k8s_node_gpu_total_data,
             k8s_node_gpu_allocatable_data, k8s_node_gpu_allocatable_data])

        self.assertFalse(self.rule.check_health(self.node))
        self.assertFalse(self.rule.check_health(self.node, stat="current"))

        # expected == total == allocatable
        k8s_node_gpu_total_data = {'status': 'success', 'data': {'resultType': 'vector', 'result': [{'metric': {'__name__': 'k8s_node_gpu_total', 'exporter_name': 'watchdog', 'host_ip': '192.168.0.1', 'instance': '192.168.255.1:9101', 'job': 'serivce_exporter', 'scraped_from': 'watchdog-664db8579f-69shf'}, 'value': [1591919499.601, '4']}]}}
        k8s_node_gpu_allocatable_data = {'status': 'success', 'data': {'resultType': 'vector', 'result': [{'metric': {'__name__': 'k8s_node_gpu_allocatable', 'exporter_name': 'watchdog', 'host_ip': '192.168.0.1', 'instance': '192.168.255.1:9101', 'job': 'serivce_exporter', 'scraped_from': 'watchdog-664db8579f-69shf'}, 'value': [1591919627.21, '4']}]}}

        self.update_data_and_validate(
            [k8s_node_gpu_total_data, k8s_node_gpu_total_data,
             k8s_node_gpu_allocatable_data, k8s_node_gpu_allocatable_data])

        self.assertTrue(self.rule.check_health(self.node))
        self.assertTrue(self.rule.check_health(self.node, stat="current"))

    def test_prepare(self):
        # No need to prepare anything
        pass


class TestDcgmEccDBERule(TestRule):
    def create_rule(self):
        self.rule = DcgmEccDBERule()

    def test_check_health(self):
        # node has a ECC DBE on a GPU
        dcgm_ecc_dbe_volatile_total = {'status': 'success', 'data': {'resultType': 'vector', 'result': [{'metric': {'__name__': 'dcgm_ecc_dbe_volatile_total', 'exporter_name': 'job-exporter', 'instance': '192.168.0.1:9102', 'job': 'serivce_exporter', 'minor_number': '0', 'scraped_from': 'job-exporter-zslkh', 'uuid': 'GPU-56d27439-dfc9-19d4-687b-ad6f2fdf0e9f'}, 'value': [1591920200.233, '0']}, {'metric': {'__name__': 'dcgm_ecc_dbe_volatile_total', 'exporter_name': 'job-exporter', 'instance': '192.168.0.1:9102', 'job': 'serivce_exporter', 'minor_number': '1', 'scraped_from': 'job-exporter-zslkh', 'uuid': 'GPU-776cf9b1-fc9c-34c2-573b-33cac6cb496f'}, 'value': [1591920200.233, '2']}, {'metric': {'__name__': 'dcgm_ecc_dbe_volatile_total', 'exporter_name': 'job-exporter', 'instance': '192.168.0.1:9102', 'job': 'serivce_exporter', 'minor_number': '2', 'scraped_from': 'job-exporter-zslkh', 'uuid': 'GPU-333595ba-3900-436e-9632-2e8d7b1577a3'}, 'value': [1591920200.233, '0']}, {'metric': {'__name__': 'dcgm_ecc_dbe_volatile_total', 'exporter_name': 'job-exporter', 'instance': '192.168.0.1:9102', 'job': 'serivce_exporter', 'minor_number': '3', 'scraped_from': 'job-exporter-zslkh', 'uuid': 'GPU-cb1843c2-a39f-6b8a-a613-85fe145b405c'}, 'value': [1591920200.233, '0']}]}}
        self.update_data_and_validate(
            [dcgm_ecc_dbe_volatile_total, dcgm_ecc_dbe_volatile_total])

        self.assertFalse(self.rule.check_health(self.node))
        self.assertFalse(self.rule.check_health(self.node, stat="current"))

        # node has no ECC DBE on any GPUs
        dcgm_ecc_dbe_volatile_total = {'status': 'success', 'data': {'resultType': 'vector', 'result': [{'metric': {'__name__': 'dcgm_ecc_dbe_volatile_total', 'exporter_name': 'job-exporter', 'instance': '192.168.0.1:9102', 'job': 'serivce_exporter', 'minor_number': '0', 'scraped_from': 'job-exporter-zslkh', 'uuid': 'GPU-56d27439-dfc9-19d4-687b-ad6f2fdf0e9f'}, 'value': [1591920200.233, '0']}, {'metric': {'__name__': 'dcgm_ecc_dbe_volatile_total', 'exporter_name': 'job-exporter', 'instance': '192.168.0.1:9102', 'job': 'serivce_exporter', 'minor_number': '1', 'scraped_from': 'job-exporter-zslkh', 'uuid': 'GPU-776cf9b1-fc9c-34c2-573b-33cac6cb496f'}, 'value': [1591920200.233, '0']}, {'metric': {'__name__': 'dcgm_ecc_dbe_volatile_total', 'exporter_name': 'job-exporter', 'instance': '192.168.0.1:9102', 'job': 'serivce_exporter', 'minor_number': '2', 'scraped_from': 'job-exporter-zslkh', 'uuid': 'GPU-333595ba-3900-436e-9632-2e8d7b1577a3'}, 'value': [1591920200.233, '0']}, {'metric': {'__name__': 'dcgm_ecc_dbe_volatile_total', 'exporter_name': 'job-exporter', 'instance': '192.168.0.1:9102', 'job': 'serivce_exporter', 'minor_number': '3', 'scraped_from': 'job-exporter-zslkh', 'uuid': 'GPU-cb1843c2-a39f-6b8a-a613-85fe145b405c'}, 'value': [1591920200.233, '0']}]}}
        self.update_data_and_validate(
            [dcgm_ecc_dbe_volatile_total, dcgm_ecc_dbe_volatile_total])

        self.assertTrue(self.rule.check_health(self.node))
        self.assertTrue(self.rule.check_health(self.node, stat="current"))
