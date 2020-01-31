import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import mock
from datetime import datetime, timedelta
from rules import ecc_reboot_node_rule
from utils import rule_alert_handler

class Testing(unittest.TestCase):

    @mock.patch('utils.email_util.EmailHandler')
    def test_check_status_true(self, mock_email_handler):

        time_five_days_ago = datetime.now() - timedelta(days=5, minutes=1)

        time_three_days_ago = datetime.now() - timedelta(days=3)

        rule_alert_handler_instance = rule_alert_handler.RuleAlertHandler()
        rule_alert_handler_instance.rule_cache["ecc_rule"] = {
            "node1": {
                "time_found": time_five_days_ago
            },
            "node2": {
                "time_found": time_three_days_ago
            }
        }

        config = {"days_until_node_reboot": 5}

        ecc_reboot_node_rule_instance = ecc_reboot_node_rule.ECCRebootNodeRule(rule_alert_handler_instance, config)

        response = ecc_reboot_node_rule_instance.check_status()

        self.assertTrue(response)
        self.assertEqual(1, len(ecc_reboot_node_rule_instance.nodes_ready_for_action))
        self.assertEqual("node1", ecc_reboot_node_rule_instance.nodes_ready_for_action[0])

    @mock.patch('utils.email_util.EmailHandler')
    def test_check_status_false(self, mock_email_handler):

        time_three_days_ago = datetime.now() - timedelta(days=3)

        rule_alert_handler_instance = rule_alert_handler.RuleAlertHandler()
        rule_alert_handler_instance.rule_cache["ecc_rule"] = {
            "node1": {
                "time_found": time_three_days_ago
            }
        }

        config = {"days_until_node_reboot": 5}

        ecc_reboot_node_rule_instance = ecc_reboot_node_rule.ECCRebootNodeRule(rule_alert_handler_instance, config)

        response = ecc_reboot_node_rule_instance.check_status()

        self.assertFalse(response)
        self.assertEqual(0, len(ecc_reboot_node_rule_instance.nodes_ready_for_action))

if __name__ == '__main__':
    unittest.main()
