import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest import mock
import datetime
from rules import ecc_detect_error_rule
from rules.ecc_detect_error_rule import EccDetectErrorRule
from utils import k8s_util, rule_alert_handler, test_util


def _mock_prometheus_ecc_data():
    mock_prometheus_ecc_data = {
        "status": "success",
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
                "values": [[1578453042, "2"], [1578453042, "2"]]
            }, {
                "metric": {
                    "__name__": "nvidiasmi_ecc_error_count",
                    "exporter_name": "job-exporter",
                    "instance": "192.168.0.2:9102",
                    "job": "serivce_exporter",
                    "minor_number": "1",
                    "scraped_from": "job-exporter-jmgn4",
                    "type": "volatile_double"
                },
                "values": [[1578453042, "2"], [1578453042, "2"],
                           [1578453042, "2"]]
            }]
        }
    }
    return mock_prometheus_ecc_data


class TestEccDetectErrorRule(unittest.TestCase):
    @mock.patch('utils.email_util.EmailHandler')
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler.load_config')
    @mock.patch('utils.k8s_util.list_node')
    @mock.patch('requests.get')
    @mock.patch('rules.ecc_detect_error_rule.EccDetectErrorRule.load_ecc_config'
               )
    def test_check_status_ecc_error_detected(
        self, mock_load_ecc_config, mock_request_get, mock_list_node,
        mock_rule_alert_handler_load_config, mock_email_handler):

        mock_rule_config = test_util.mock_rule_config()
        mock_rule_alert_handler_load_config.return_value = mock_rule_config
        mock_load_ecc_config.return_value = test_util.mock_ecc_config()
        mock_rule_alert_handler = rule_alert_handler.RuleAlertHandler()
        mock_request_get.return_value.json.return_value = _mock_prometheus_ecc_data(
        )
        mock_list_node.return_value = test_util.mock_v1_node_list([{
            "instance": "192.168.0.1",
            "node_name": "mock-worker-one"
        }, {
            "instance": "192.168.0.2",
            "node_name": "mock-worker-two"
        }])

        ecc_rule_instance = EccDetectErrorRule(mock_rule_alert_handler,
                                               mock_rule_config)
        check_status_response = ecc_rule_instance.check_status()

        self.assertTrue(check_status_response)
        self.assertEqual(len(ecc_rule_instance.new_bad_nodes), 2)
        self.assertTrue("mock-worker-one" in ecc_rule_instance.new_bad_nodes)
        self.assertTrue("mock-worker-two" in ecc_rule_instance.new_bad_nodes)

    @mock.patch('utils.email_util.EmailHandler')
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler.load_config')
    @mock.patch('utils.k8s_util.list_node')
    @mock.patch('requests.get')
    @mock.patch('rules.ecc_detect_error_rule.EccDetectErrorRule.load_ecc_config'
               )
    def test_check_status_ecc_error_node_already_detected(
        self, mock_load_ecc_config, mock_request_get, mock_list_node,
        mock_rule_alert_handler_load_config, mock_email_handler):

        mock_rule_config = test_util.mock_rule_config()
        mock_rule_alert_handler_load_config.return_value = mock_rule_config
        mock_load_ecc_config.return_value = test_util.mock_ecc_config()
        mock_rule_alert_handler = rule_alert_handler.RuleAlertHandler()
        # nodes already detected in previous run
        mock_rule_alert_handler.rule_cache = {
            "ecc_rule": {
                "mock-worker-one": {
                    "time_found": "2020-02-18 21:14:20.351019",
                    "instance": "192.168.0.1"
                }
            }
        }
        mock_request_get.return_value.json.return_value = _mock_prometheus_ecc_data(
        )
        mock_list_node.return_value = test_util.mock_v1_node_list([{
            "instance": "192.168.0.1",
            "node_name": "mock-worker-one"
        }, {
            "instance": "192.168.0.2",
            "node_name": "mock-worker-two"
        }])

        ecc_rule_instance = EccDetectErrorRule(mock_rule_alert_handler,
                                               mock_rule_config)
        check_status_response = ecc_rule_instance.check_status()

        self.assertTrue(check_status_response)
        self.assertEqual(len(ecc_rule_instance.new_bad_nodes), 1)
        self.assertTrue("mock-worker-two" in ecc_rule_instance.new_bad_nodes)

    @mock.patch('utils.k8s_util.get_node_address_info')
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler')
    @mock.patch('utils.k8s_util.list_node')
    @mock.patch('requests.get')
    @mock.patch('rules.ecc_detect_error_rule.EccDetectErrorRule.load_ecc_config'
               )
    def test_check_status_ecc_error_not_found(self, mock_load_ecc_config,
                                              mock_request_get, mock_list_node,
                                              mock_rule_alert_handler,
                                              mock_get_node_address_info):
        mock_load_ecc_config.return_value = test_util.mock_ecc_config()

        mock_request_get.return_value.json.return_value = test_util.mock_empty_prometheus_metric_data(
        )

        ecc_rule_instance = EccDetectErrorRule(mock_rule_alert_handler,
                                               test_util.mock_rule_config())
        check_status_response = ecc_rule_instance.check_status()

        self.assertFalse(check_status_response)
        self.assertEqual(len(ecc_rule_instance.new_bad_nodes), 0)

    @mock.patch('rules.ecc_detect_error_rule._create_email_for_job_owner')
    @mock.patch('rules.ecc_detect_error_rule._create_email_for_dris')
    @mock.patch('rules.ecc_detect_error_rule.k8s_util.cordon_node')
    @mock.patch('utils.k8s_util.list_namespaced_pod')
    @mock.patch('utils.email_util.EmailHandler')
    @mock.patch('rules.ecc_detect_error_rule.EccDetectErrorRule.load_ecc_config'
               )
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler.load_config')
    def test_take_action(self, mock_load_rule_config, mock_load_ecc_config,
                         mock_email_handler, mock_pod_list, mock_cordon_node,
                         mock_create_email_for_dris,
                         mock_create_email_for_job_owner):
        mock_rule_config = test_util.mock_rule_config()
        mock_load_rule_config.return_value = mock_rule_config
        mock_load_ecc_config.return_value = test_util.mock_ecc_config()

        alert = rule_alert_handler.RuleAlertHandler()
        ecc_rule_instance = EccDetectErrorRule(alert, mock_rule_config)
        ecc_rule_instance.new_bad_nodes = {
            "mock-worker-one": "192.168.0.1",
            "mock-worker-two": "192.168.0.2"
        }

        mock_pod_list.return_value = test_util.mock_v1_pod_list([{
            "job_name": "87654321-wxyz",
            "user_name": "user1",
            "vc_name": "vc1",
            "node_name": "mock-worker-one"
        }, {
            "job_name": "12345678-abcd",
            "user_name": "user2",
            "vc_name": "vc2",
            "node_name": "mock-worker-one"
        }, {
            "job_name": "12345678-abcd",
            "user_name": "user2",
            "vc_name": "vc2",
            "node_name": "mock-worker-two"
        }, {
            "job_name": "99999999-efgh",
            "user_name": "user3",
            "vc_name": "vc3",
            "node_name": "mock-worker-three"
        }])

        ecc_rule_instance.take_action()

        self.assertEqual(2, mock_cordon_node.call_count)
        self.assertEqual(1, mock_create_email_for_dris.call_count)
        self.assertEqual(2, mock_create_email_for_job_owner.call_count)

        self.assertTrue("ecc_rule" in alert.rule_cache)
        self.assertTrue("mock-worker-one" in alert.rule_cache["ecc_rule"])
        self.assertEqual(
            "192.168.0.1",
            alert.rule_cache["ecc_rule"]["mock-worker-one"]["instance"])
        self.assertTrue("mock-worker-two" in alert.rule_cache["ecc_rule"])
        self.assertEqual(
            "192.168.0.2",
            alert.rule_cache["ecc_rule"]["mock-worker-two"]["instance"])


if __name__ == '__main__':
    unittest.main()
