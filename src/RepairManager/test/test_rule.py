#!/usr/bin/env python3

import logging
import os
import sys
import unittest

sys.path.append(os.path.abspath("../src/"))

from util import State, Node, Job
from rule import Rule, UnschedulableRule, K8sGpuRule, \
    DcgmEccDBERule, InfinibandRule, IPoIBRule, NvPeerMemRule, NVSMRule, \
    instantiate_rules

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
        # Sanity check on all rules
        rules = instantiate_rules()
        for rule in rules:
            self.assertTrue(rule.name in Rule.subclasses)


class TestRule(unittest.TestCase):
    def create_rule(self):
        self.rule = Rule("dummy_metric")

    def setUp(self):
        self.create_rule()
        self.rule.rest_util = MockRestUtil()
        self.rule.prometheus_util = MockPrometheusUtil()
        self.job = Job("job1", "user1", "vc1")
        self.node = Node("node1",
                         "192.168.0.1",
                         True,
                         False,
                         "Standard_ND24rs",
                         4,
                         4,
                         4,
                         State.IN_SERVICE,
                         infiniband=["mlx4_0:1", "mlx4_1:1"],
                         ipoib=["ib0", "ib1"],
                         nv_peer_mem=1,
                         nvsm=True)
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
                             self.rule.data[self.rule.stat][metric])
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


class TestUnschedulableRule(TestRule):
    def create_rule(self):
        self.rule = UnschedulableRule()

    def test_check_health(self):
        # Node is marked as unschedulable
        self.node.unschedulable = True
        self.assertFalse(self.rule.check_health(self.node))
        self.assertFalse(self.rule.check_health(self.node, stat="current"))

        # Node is schedulable
        self.node.unschedulable = False
        self.assertTrue(self.rule.check_health(self.node))
        self.assertTrue(self.rule.check_health(self.node, stat="current"))


class TestK8sGpuRule(TestRule):
    def create_rule(self):
        self.rule = K8sGpuRule()

    def test_check_health(self):
        # expected > total && total > allocatable
        self.node.gpu_total = 3
        self.node.gpu_allocatable = 2

        self.assertFalse(self.rule.check_health(self.node))
        self.assertFalse(self.rule.check_health(self.node, stat="current"))

        # expected > total && total == allocatable
        self.node.gpu_total = 3
        self.node.gpu_allocatable = 3

        self.assertFalse(self.rule.check_health(self.node))
        self.assertFalse(self.rule.check_health(self.node, stat="current"))

        # expected == total && total > allocatable
        self.node.gpu_total = 4
        self.node.gpu_allocatable = 3

        self.assertFalse(self.rule.check_health(self.node))
        self.assertFalse(self.rule.check_health(self.node, stat="current"))

        # expected == total == allocatable
        self.node.gpu_total = 4
        self.node.gpu_allocatable = 4

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


class TestInfinibandRule(TestRule):
    def create_rule(self):
        self.rule = InfinibandRule()

    def test_check_health(self):
        # An infiniband device is down
        infiniband_up = {'status': 'success', 'data': {'resultType': 'vector', 'result': [{'metric': {'__name__': 'infiniband_up', 'device': 'mlx4_0', 'exporter_name': 'job-exporter', 'instance': '192.168.0.1:9102', 'job': 'serivce_exporter', 'link_layer': 'InfiniBand', 'phys_state': 'LinkUp', 'port': '1', 'rate': '40 Gb/sec (4X QDR)', 'scraped_from': 'job-exporter-zslkh', 'state': 'ACTIVE'}, 'value': [1592254588.528, '1']}, {'metric': {'__name__': 'infiniband_up', 'device': 'mlx4_1', 'exporter_name': 'job-exporter', 'instance': '192.168.0.1:9102', 'job': 'serivce_exporter', 'link_layer': 'InfiniBand', 'phys_state': 'LinkUp', 'port': '1', 'rate': '40 Gb/sec (4X QDR)', 'scraped_from': 'job-exporter-zslkh', 'state': 'ACTIVE'}, 'value': [1592254588.528, '0']}]}}
        self.update_data_and_validate([infiniband_up, infiniband_up])

        self.assertFalse(self.rule.check_health(self.node))
        self.assertFalse(self.rule.check_health(self.node, stat="current"))

        # Infinibands devices are up
        infiniband_up = {'status': 'success', 'data': {'resultType': 'vector', 'result': [{'metric': {'__name__': 'infiniband_up', 'device': 'mlx4_0', 'exporter_name': 'job-exporter', 'instance': '192.168.0.1:9102', 'job': 'serivce_exporter', 'link_layer': 'InfiniBand', 'phys_state': 'LinkUp', 'port': '1', 'rate': '40 Gb/sec (4X QDR)', 'scraped_from': 'job-exporter-zslkh', 'state': 'ACTIVE'}, 'value': [1592254588.528, '1']}, {'metric': {'__name__': 'infiniband_up', 'device': 'mlx4_1', 'exporter_name': 'job-exporter', 'instance': '192.168.0.1:9102', 'job': 'serivce_exporter', 'link_layer': 'InfiniBand', 'phys_state': 'LinkUp', 'port': '1', 'rate': '40 Gb/sec (4X QDR)', 'scraped_from': 'job-exporter-zslkh', 'state': 'ACTIVE'}, 'value': [1592254588.528, '1']}]}}
        self.update_data_and_validate([infiniband_up, infiniband_up])

        self.assertTrue(self.rule.check_health(self.node))
        self.assertTrue(self.rule.check_health(self.node, stat="current"))


class TestIPoIBRule(TestRule):
    def create_rule(self):
        self.rule = IPoIBRule()

    def test_check_health(self):
        # An IPoIB is down
        ipoib_up = {'status': 'success', 'data': {'resultType': 'vector', 'result': [{'metric': {'__name__': 'ipoib_up', 'device': 'ib0', 'exporter_name': 'job-exporter', 'instance': '192.168.0.1:9102', 'job': 'serivce_exporter', 'scraped_from': 'job-exporter-zslkh', 'state': 'UP'}, 'value': [1592255865.342, '1']}, {'metric': {'__name__': 'ipoib_up', 'device': 'ib1', 'exporter_name': 'job-exporter', 'instance': '192.168.0.1:9102', 'job': 'serivce_exporter', 'scraped_from': 'job-exporter-zslkh', 'state': 'DOWN'}, 'value': [1592255865.342, '0']}]}}
        self.update_data_and_validate([ipoib_up, ipoib_up])

        self.assertFalse(self.rule.check_health(self.node))
        self.assertFalse(self.rule.check_health(self.node, stat="current"))

        # All IPoIB interfaces are up
        ipoib_up = {'status': 'success', 'data': {'resultType': 'vector', 'result': [{'metric': {'__name__': 'ipoib_up', 'device': 'ib0', 'exporter_name': 'job-exporter', 'instance': '192.168.0.1:9102', 'job': 'serivce_exporter', 'scraped_from': 'job-exporter-zslkh', 'state': 'UP'}, 'value': [1592255865.342, '1']}, {'metric': {'__name__': 'ipoib_up', 'device': 'ib1', 'exporter_name': 'job-exporter', 'instance': '192.168.0.1:9102', 'job': 'serivce_exporter', 'scraped_from': 'job-exporter-zslkh', 'state': 'UP'}, 'value': [1592255865.342, '1']}]}}
        self.update_data_and_validate([ipoib_up, ipoib_up])

        self.assertTrue(self.rule.check_health(self.node))
        self.assertTrue(self.rule.check_health(self.node, stat="current"))

    def test_prepare(self):
        # Job is in scheduling state
        self.rule.rest_util.data.append({"jobStatus": "scheduling"})
        self.assertTrue(self.rule.prepare(self.node))

        # Job is in running state
        self.rule.rest_util.data.append({"jobStatus": "running"})
        self.assertTrue(self.rule.prepare(self.node))


class TestNvPeerMemRule(TestRule):
    def create_rule(self):
        self.rule = NvPeerMemRule()

    def test_check_health(self):
        # nv_peer_mem is down
        nv_peer_mem_count = {'status': 'success', 'data': {'resultType': 'vector', 'result': [{'metric': {'__name__': 'nv_peer_mem_count', 'exporter_name': 'job-exporter', 'instance': '192.168.0.1:9102', 'job': 'serivce_exporter', 'scraped_from': 'job-exporter-zslkh'}, 'value': [1592256663.895, '0']}]}}
        self.update_data_and_validate([nv_peer_mem_count, nv_peer_mem_count])

        self.assertFalse(self.rule.check_health(self.node))
        self.assertFalse(self.rule.check_health(self.node, stat="current"))

        # nv_peer_mem is up
        nv_peer_mem_count = {'status': 'success', 'data': {'resultType': 'vector', 'result': [{'metric': {'__name__': 'nv_peer_mem_count', 'exporter_name': 'job-exporter', 'instance': '192.168.0.1:9102', 'job': 'serivce_exporter', 'scraped_from': 'job-exporter-zslkh'}, 'value': [1592256663.895, '1']}]}}
        self.update_data_and_validate([nv_peer_mem_count, nv_peer_mem_count])

        self.assertTrue(self.rule.check_health(self.node))
        self.assertTrue(self.rule.check_health(self.node, stat="current"))

    def test_prepare(self):
        # Job is in scheduling state
        self.rule.rest_util.data.append({"jobStatus": "scheduling"})
        self.assertTrue(self.rule.prepare(self.node))

        # Job is in running state
        self.rule.rest_util.data.append({"jobStatus": "running"})
        self.assertTrue(self.rule.prepare(self.node))


class TestNVSMRule(TestRule):
    def create_rule(self):
        self.rule = NVSMRule()

    def test_check_health(self):
        # There is some failure in nvsm health check
        nvsm_health_total_count = {'status': 'success', 'data': {'resultType': 'vector', 'result': [{'metric': {'__name__': 'nvsm_health_total_count', 'exporter_name': 'job-exporter', 'instance': '192.168.0.1:9102', 'job': 'serivce_exporter', 'scraped_from': 'job-exporter-zslkh'}, 'value': [1592257205.813, '169']}]}}
        nvsm_health_good_count = {'status': 'success', 'data': {'resultType': 'vector', 'result': [{'metric': {'__name__': 'nvsm_health_good_count', 'exporter_name': 'job-exporter', 'instance': '192.168.0.1:9102', 'job': 'serivce_exporter', 'scraped_from': 'job-exporter-zslkh'}, 'value': [1592257205.813, '168']}]}}
        self.update_data_and_validate([
            nvsm_health_total_count, nvsm_health_total_count,
            nvsm_health_good_count, nvsm_health_good_count
        ])

        self.assertFalse(self.rule.check_health(self.node))
        self.assertFalse(self.rule.check_health(self.node, stat="current"))

        # All checks are good
        nvsm_health_total_count = {'status': 'success', 'data': {'resultType': 'vector', 'result': [{'metric': {'__name__': 'nvsm_health_total_count', 'exporter_name': 'job-exporter', 'instance': '192.168.0.1:9102', 'job': 'serivce_exporter', 'scraped_from': 'job-exporter-zslkh'}, 'value': [1592257205.813, '169']}]}}
        nvsm_health_good_count = {'status': 'success', 'data': {'resultType': 'vector', 'result': [{'metric': {'__name__': 'nvsm_health_good_count', 'exporter_name': 'job-exporter', 'instance': '192.168.0.1:9102', 'job': 'serivce_exporter', 'scraped_from': 'job-exporter-zslkh'}, 'value': [1592257205.813, '169']}]}}
        self.update_data_and_validate([
            nvsm_health_total_count, nvsm_health_total_count,
            nvsm_health_good_count, nvsm_health_good_count
        ])

        self.assertTrue(self.rule.check_health(self.node))
        self.assertTrue(self.rule.check_health(self.node, stat="current"))

        # Node is in exception list:
        self.node.nvsm = None
        self.assertTrue(self.rule.check_health(self.node))
        self.assertTrue(self.rule.check_health(self.node, stat="current"))


if __name__ == '__main__':
    unittest.main()
