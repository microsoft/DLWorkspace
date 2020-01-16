import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import mock
from mock import call
from rules import ecc_rule
from utils import k8s_util, rule_alert_handler
from kubernetes.client.models.v1_node_list import V1NodeList
from kubernetes.client.models.v1_node import V1Node
from kubernetes.client.models.v1_node_status import V1NodeStatus
from kubernetes.client.models.v1_node_address import V1NodeAddress

def _mock_v1_node(internal_ip, hostname):
    node = V1Node()
    address_ip = V1NodeAddress(internal_ip, "InternalIP")
    address_hostname = V1NodeAddress(hostname, "Hostname")
    node.status = V1NodeStatus(addresses=[address_ip, address_hostname])
    return node

class Testing(unittest.TestCase):

    def test_get_node_address_info(self):
        node_one = _mock_v1_node("192.168.0.1", "mock-worker-one")
        node_two = _mock_v1_node("192.168.0.2", "mock-worker-two")
        mock_node_list = V1NodeList(items=[node_one, node_two])

        address_info = ecc_rule.get_node_address_info(mock_node_list)

        self.assertEqual(len(address_info), 2)
        self.assertTrue('192.168.0.1' in address_info)
        self.assertEqual(address_info['192.168.0.1'], "mock-worker-one")
        self.assertTrue('192.168.0.2' in address_info)
        self.assertEqual(address_info['192.168.0.2'], "mock-worker-two")


    def test_get_node_address_info_empty(self):
        mock_node_list = V1NodeList(items=[])
        address_info = ecc_rule.get_node_address_info(mock_node_list)
        self.assertEqual(len(address_info), 0)

    
    def test_extract_ips_from_ecc_data(self):
        prometheus_error_data = {
            "status":
                "success",
                "data": {
                    "result": [{
                        "metric": {
                            "__name__": "nvidiasmi_ecc_error_count",
                            "exporter_name": "job-exporter",
                            "instance": "192.168.0.1:9102",
                            "job": "serivce_exporter",
                            "minor_number": "1",
                            "scraped_from": "job-exporter-jmgn4",
                            "type": "volatile_double"
                        },
                        "values": [
                            [1578453042, "2"], [1578453042, "2"],
                            [1578453042, "2"], [1578453042, "2"],
                            [1578453042, "2"], [1578453042, "2"],
                            [1578453042, "2"], [1578453042, "2"],
                            [1578453042, "2"]   
                        ]
                    },
                    {
                        "metric": {
                            "__name__": "nvidiasmi_ecc_error_count",
                            "exporter_name": "job-exporter",
                            "instance": "192.168.0.2:9102",
                            "job": "serivce_exporter",
                            "minor_number": "1",
                            "scraped_from": "job-exporter-jmgn4",
                            "type": "volatile_double"
                        },
                        "values": [
                            [1578453042, "2"], [1578453042, "2"], [1578453042, "2"]
                        ]
                    }]
                }
        }

        percent_threshold = 90
        interval = 9
        # of the total 10 data points (interval+1), at least 9 data points (90%) must show ecc eccor
        # in order to be considered a "bad node"
        ecc_node_ips = ecc_rule.extract_ips_from_ecc_data(prometheus_error_data, percent_threshold, interval)

        self.assertEqual(len(ecc_node_ips), 1)
        self.assertTrue('192.168.0.1' in ecc_node_ips)

    @mock.patch('rules.ecc_rule.get_node_address_info')
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler')
    @mock.patch('rules.ecc_rule.k8s_util.list_node')
    @mock.patch('rules.ecc_rule.requests.get')
    @mock.patch('rules.ecc_rule.ECCRule.load_ecc_config')
    def test_check_status_ecc_error_found(self, 
            mock_load_ecc_config,
            mock_request_get,
            mock_list_node,
            mock_rule_alert_handler,
            mock_get_node_address_info):

        rule_config = {}

        mock_load_ecc_config.return_value = {
            "prometheus": {
                "ip": "localhost",
                "port": 9091,
                "ecc_error_query": 'nvidiasmi_ecc_error_count{type="volatile_double"}>0',
                "step": "1m",
                "interval": 9,
                "percent_threshold": 90
            }
        }


        mock_request_get.return_value.json.return_value = {
            "status":
                "success",
                "data": {
                    "result": [{
                        "metric": {
                            "__name__": "nvidiasmi_ecc_error_count",
                            "exporter_name": "job-exporter",
                            "instance": "192.168.0.2:9102",
                            "job": "serivce_exporter",
                            "minor_number": "1",
                            "scraped_from": "job-exporter-jmgn4",
                            "type": "volatile_double"
                        },
                        "values": [
                            [1578453042, "2"], [1578453042, "2"],
                            [1578453042, "2"], [1578453042, "2"],
                            [1578453042, "2"], [1578453042, "2"],
                            [1578453042, "2"], [1578453042, "2"],
                            [1578453042, "2"]   
                        ]
                    }]
                }
        }

        mock_get_node_address_info.return_value = {
            "192.168.0.1": "mock-worker-one",
            "192.168.0.2": "mock-worker-two"
        }

        ecc_rule_instance = ecc_rule.ECCRule(mock_rule_alert_handler, rule_config)
        check_status_response = ecc_rule_instance.check_status()

        self.assertTrue(check_status_response)
        self.assertEqual(len(ecc_rule_instance.ecc_node_hostnames), 1)
        self.assertEqual(ecc_rule_instance.ecc_node_hostnames[0], "mock-worker-two")


    
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler')
    @mock.patch('rules.ecc_rule.requests.get')
    @mock.patch('rules.ecc_rule.ECCRule.load_ecc_config')
    def test_check_status_ecc_error_not_found(self,
            mock_load_ecc_config,
            mock_request_get,
            mock_rule_alert_handler):

        rule_config = {}

        mock_load_ecc_config.return_value = {
            "prometheus": {
                "ip": "localhost",
                "port": 9091,
                "ecc_error_query": 'nvidiasmi_ecc_error_count{type="volatile_double"}>0',
                "step": "1m",
                "interval": 9,
                "percent_threshold": 90
            }
        }


        mock_request_get.return_value.json.return_value = {
            "status":
                "success",
                "data": {
                    "result": [{
                        "metric": {
                            "__name__": "nvidiasmi_ecc_error_count",
                            "exporter_name": "job-exporter",
                            "instance": "192.168.0.2:9102",
                            "job": "serivce_exporter",
                            "minor_number": "1",
                            "scraped_from": "job-exporter-jmgn4",
                            "type": "volatile_double"
                        },
                        "values": [
                            [1578453042, "2"], [1578453042, "2"]
                        ]
                    }]
                }
        }


        ecc_rule_instance = ecc_rule.ECCRule(mock_rule_alert_handler, rule_config)
        check_status_response = ecc_rule_instance.check_status()

        self.assertFalse(check_status_response)
        self.assertEqual(len(ecc_rule_instance.ecc_node_hostnames), 0)


    @mock.patch('rules.ecc_rule.get_job_info_from_nodes')
    @mock.patch('rules.ecc_rule.k8s_util.cordon_node')
    @mock.patch('rules.ecc_rule.k8s_util.is_node_cordoned')
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler')
    @mock.patch('rules.ecc_rule.ECCRule.load_ecc_config')
    def test_take_action(self,
            mock_load_ecc_config,
            mock_rule_alert_handler,
            mock_is_node_cordoned,
            mock_cordon_node,
            mock_get_job_info_from_nodes):

        rule_config = {
            "cluster_name": "mock_cluster"
        }

        mock_load_ecc_config.return_value = {
            "cordon_dry_run": False,
            "prometheus": {
                "ip": "localhost",
                "port": 9091,
                "ecc_error_query": 'nvidiasmi_ecc_error_count{type="volatile_double"}>0',
                "step": "1m",
                "interval": 9,
                "percent_threshold": 90
            }
        }

        mock_is_node_cordoned.return_value = False
        
        ecc_rule_instance = ecc_rule.ECCRule(mock_rule_alert_handler, rule_config)
        ecc_rule_instance.ecc_node_hostnames = {"mock_worker_one", "mock_worker_two"}

        ecc_rule_instance.take_action()

        calls = [call("mock_worker_one", dry_run=False), call("mock_worker_two", dry_run=False)]
        mock_cordon_node.assert_has_calls(calls, any_order=True)

if __name__ == '__main__':
    unittest.main()
