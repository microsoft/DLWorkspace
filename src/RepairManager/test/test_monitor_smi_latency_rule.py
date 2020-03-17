import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import mock
from datetime import datetime, timedelta, timezone
from mock import call
from rules import monitor_smi_latency_rule
from rules.monitor_smi_latency_rule import MonitorSMILatencyRule
from utils import k8s_util, rule_alert_handler, test_util

def _mock_latency_config():
    mock_latency_config = {
            "prometheus": {
                "ip": "localhost",
                "port": 9091,
                "smi_latency_too_large_query":
                    "histogram_quantile(0.95, sum(rate(cmd_nvidia_smi_latency_seconds_bucket[5m])) " \
                    "BY (le, instance)) > 40"
            },
            "dri_email": "dri@email.com",
            "hours_until_alert_expiration": 4
        }
    return mock_latency_config

def _mock_prometheus_latency_data():
    mock_prometheus_latency_data = {
        "status": "success",
        "data": {
            "resultType": "vector", "result": [
                {
                    "metric": {
                        "instance": "192.168.0.1:9102"
                    },
                    "values": [[1584389568, "62.4"], 
                               [1584389868, "62.4"]]
                }
            ]
        }
    }
    return mock_prometheus_latency_data

class Testing(unittest.TestCase):

    @mock.patch('rules.ecc_detect_error_rule._create_email_for_dris')
    @mock.patch('utils.email_util.EmailHandler')
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler.load_config')
    @mock.patch('utils.k8s_util.list_node')
    @mock.patch('requests.get')
    @mock.patch('rules.monitor_smi_latency_rule.MonitorSMILatencyRule.load_latency_config')
    def test_check_status_large_latency_detected(self, 
            mock_load_latency_config,
            mock_request_get,
            mock_list_node,
            mock_rule_alert_handler_load_config,
            mock_email_handler,
            mock_create_email_for_dris):

        mock_rule_config = test_util.mock_rule_config()
        mock_rule_alert_handler_load_config.return_value = mock_rule_config
        mock_load_latency_config.return_value = _mock_latency_config()
        mock_rule_alert_handler = rule_alert_handler.RuleAlertHandler()
        mock_request_get.return_value.json.return_value = _mock_prometheus_latency_data()
        mock_list_node.return_value = test_util.mock_v1_node_list([
            {
                "instance": "192.168.0.1",
                "node_name": "mock-worker-one"
            },
            {
                "instance": "192.168.0.2",
                "node_name": "mock-worker-two"
            }
        ])

        latency_rule_instance = MonitorSMILatencyRule(mock_rule_alert_handler, mock_rule_config)
        check_status_response = latency_rule_instance.check_status()

        self.assertTrue(check_status_response)
        self.assertEqual(len(latency_rule_instance.impacted_nodes), 1)
        self.assertTrue("mock-worker-one" in latency_rule_instance.impacted_nodes)


    @mock.patch('rules.monitor_smi_latency_rule._create_email_for_dris')
    @mock.patch('utils.email_util.EmailHandler')
    @mock.patch('rules.monitor_smi_latency_rule.MonitorSMILatencyRule.load_latency_config')
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler.load_config')
    def test_take_action(self,
            mock_load_rule_config,
            mock_load_ecc_config,
            mock_email_handler,
            mock_create_email_for_dris):
        mock_rule_config = test_util.mock_rule_config()
        mock_load_rule_config.return_value = mock_rule_config
        mock_load_ecc_config.return_value = _mock_latency_config()

        alert = rule_alert_handler.RuleAlertHandler()
        latency_rule_instance = MonitorSMILatencyRule(alert, mock_rule_config)
        latency_rule_instance.impacted_nodes = {
            "mock-worker-one": "192.168.0.1",
            "mock-worker-two": "192.168.0.2"
        }

        latency_rule_instance.take_action()

        self.assertEqual(1, mock_create_email_for_dris.call_count)

        self.assertTrue("large_latency_rule" in alert.rule_cache)
        self.assertTrue("mock-worker-one" in alert.rule_cache["large_latency_rule"])
        self.assertEqual("192.168.0.1", alert.rule_cache["large_latency_rule"]["mock-worker-one"]["instance"])
        self.assertTrue("mock-worker-two" in alert.rule_cache["large_latency_rule"])
        self.assertEqual("192.168.0.2", alert.rule_cache["large_latency_rule"]["mock-worker-two"]["instance"])


    @mock.patch('requests.get')
    @mock.patch('rules.ecc_reboot_node_rule.ECCRebootNodeRule.load_ecc_config')
    @mock.patch('utils.email_util.EmailHandler')
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler.load_config')
    def test_clean_expired_items_in_rule_cache(self,
            mock_load_rule_config,
            mock_email_handler,
            mock_ecc_config,
            mock_request_get):

        rule_config = test_util.mock_rule_config()
        mock_load_rule_config.return_value = rule_config

        mock_ecc_config.return_value = _mock_latency_config()
        mock_ecc_config.return_value["hours_until_alert_expiration"] = 4

        time_one_hours_ago = datetime.utcnow() - timedelta(hours=1)
        time_four_hours_ago = datetime.utcnow() - timedelta(hours=4, minutes=1)

        #  large latency alert detected previously
        alert = rule_alert_handler.RuleAlertHandler()
        alert.rule_cache["large_latency_rule"] = {
            "node1": {
                "time_found": time_four_hours_ago.strftime(rule_config['date_time_format']),
                "instance": "192.168.0.1"
            },
            "node2": {
                "time_found": time_one_hours_ago.strftime(rule_config['date_time_format']),
                "instance": "192.168.0.2"
            }
        }

        large_latency_rule_instance = monitor_smi_latency_rule.MonitorSMILatencyRule(alert, rule_config)
        large_latency_rule_instance.clean_expired_items_in_rule_cache

        self.assertEqual(1, len(alert.rule_cache))
        self.assertTrue("node2" in alert.rule_cache["large_latency_rule"])

if __name__ == '__main__':
    unittest.main()