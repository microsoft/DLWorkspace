import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import mock
from utils import rule_alert_handler

class Testing(unittest.TestCase):

    @mock.patch('utils.email_util.EmailHandler')
    def test_update_rule_cache(self, mock_email_handler):
        rule_alert_handler_instance = rule_alert_handler.RuleAlertHandler()

        rule = "TestRule"
        cache_key = "test_key"
        cache_value = "test_value"

        rule_alert_handler_instance.update_rule_cache(rule, cache_key, cache_value)

        self.assertTrue(rule in rule_alert_handler_instance.rule_cache)
        self.assertTrue(cache_key in rule_alert_handler_instance.rule_cache[rule])
        self.assertEqual(cache_value, rule_alert_handler_instance.rule_cache[rule][cache_key])


    @mock.patch('utils.email_util.EmailHandler')
    def test_remove_from_rule_cache(self, mock_email_handler):
        rule_alert_handler_instance = rule_alert_handler.RuleAlertHandler()

        rule = "TestRule"
        cache_key = "test_key"
        cache_value = "test_value"
        rule_alert_handler_instance.rule_cache[rule] = {cache_key: cache_value}

        rule_alert_handler_instance.remove_from_rule_cache(rule, cache_key)

        self.assertTrue(rule in rule_alert_handler_instance.rule_cache)
        self.assertEqual(0, len(rule_alert_handler_instance.rule_cache[rule]))


    @mock.patch('utils.email_util.EmailHandler')
    def test_get_rule_cache(self, mock_email_handler):
        rule_alert_handler_instance = rule_alert_handler.RuleAlertHandler()

        rule = "TestRule"
        cache_key = "test_key"
        cache_value = "test_value"
        rule_alert_handler_instance.rule_cache[rule] = {cache_key: cache_value}

        result = rule_alert_handler_instance.get_rule_cache(rule, cache_key)
        self.assertEqual(result, cache_value)

        result = rule_alert_handler_instance.get_rule_cache(rule, "should not exist")
        self.assertEqual(result, None)


    @mock.patch('utils.email_util.EmailHandler')
    def test_check_rule_cache(self, mock_email_handler):
        rule_alert_handler_instance = rule_alert_handler.RuleAlertHandler()

        rule = "TestRule"
        cache_key = "test_key"
        cache_value = "test_value"
        rule_alert_handler_instance.rule_cache[rule] = {cache_key: cache_value}

        result = rule_alert_handler_instance.check_rule_cache(rule, cache_key)
        self.assertTrue(result)

        result = rule_alert_handler_instance.check_rule_cache(rule, "should not exist")
        self.assertFalse(result)
