import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import mock
from pathlib import Path
from utils import rule_alert_handler

def _clean_up_dump_file(rule_cache_dump_file):
    dump_file = Path(rule_cache_dump_file)
    if dump_file.is_file():
        os.remove(rule_cache_dump_file)

def _mock_rule_config():
    mock_rule_config = {
        "restore_from_rule_cache_dump": False
    }
    return mock_rule_config

class TestRuleAlertHandler(unittest.TestCase):

    @mock.patch('utils.rule_alert_handler.RuleAlertHandler.load_config')
    @mock.patch('utils.email_util.EmailHandler')
    def test_update_rule_cache(self, mock_email_handler, mock_config):
        mock_config.return_value = _mock_rule_config()

        rule_alert_handler_instance = rule_alert_handler.RuleAlertHandler()

        rule = "TestRule"
        cache_key = "test_key"
        cache_value = "test_value"

        rule_alert_handler_instance.update_rule_cache(rule, cache_key, cache_value)

        self.assertTrue(rule in rule_alert_handler_instance.rule_cache)
        self.assertTrue(cache_key in rule_alert_handler_instance.rule_cache[rule])
        self.assertEqual(cache_value, rule_alert_handler_instance.rule_cache[rule][cache_key])


    @mock.patch('utils.rule_alert_handler.RuleAlertHandler.load_config')
    @mock.patch('utils.email_util.EmailHandler')
    def test_remove_from_rule_cache(self, mock_email_handler, mock_config):
        mock_config.return_value = _mock_rule_config()

        rule_alert_handler_instance = rule_alert_handler.RuleAlertHandler()

        rule = "TestRule"
        cache_key = "test_key"
        cache_value = "test_value"
        rule_alert_handler_instance.rule_cache[rule] = {cache_key: cache_value}

        rule_alert_handler_instance.remove_from_rule_cache(rule, cache_key)

        self.assertTrue(rule in rule_alert_handler_instance.rule_cache)
        self.assertEqual(0, len(rule_alert_handler_instance.rule_cache[rule]))


    @mock.patch('utils.rule_alert_handler.RuleAlertHandler.load_config')
    @mock.patch('utils.email_util.EmailHandler')
    def test_get_rule_cache(self, mock_email_handler, mock_config):
        mock_config.return_value = _mock_rule_config()

        rule_alert_handler_instance = rule_alert_handler.RuleAlertHandler()

        rule = "TestRule"
        cache_key = "test_key"
        cache_value = "test_value"
        rule_alert_handler_instance.rule_cache[rule] = {cache_key: cache_value}

        result = rule_alert_handler_instance.get_rule_cache(rule, cache_key)
        self.assertEqual(result, cache_value)

        result = rule_alert_handler_instance.get_rule_cache(rule, "should not exist")
        self.assertEqual(result, None)


    @mock.patch('utils.rule_alert_handler.RuleAlertHandler.load_config')
    @mock.patch('utils.email_util.EmailHandler')
    def test_check_rule_cache(self, mock_email_handler, mock_config):
        mock_config.return_value = _mock_rule_config()

        rule_alert_handler_instance = rule_alert_handler.RuleAlertHandler()

        rule = "TestRule"
        cache_key = "test_key"
        cache_value = "test_value"
        rule_alert_handler_instance.rule_cache[rule] = {cache_key: cache_value}

        result = rule_alert_handler_instance.check_rule_cache(rule, cache_key)
        self.assertTrue(result)

        result = rule_alert_handler_instance.check_rule_cache(rule, "should not exist")
        self.assertFalse(result)


    @mock.patch('utils.rule_alert_handler.RuleAlertHandler.load_config')
    @mock.patch('utils.email_util.EmailHandler')
    def test_get_rule_cache_keys(self, mock_email_handler, mock_config):
        mock_config.return_value = _mock_rule_config()
        rule = "TestRule"

        rule_alert_handler_instance = rule_alert_handler.RuleAlertHandler()

        keys = rule_alert_handler_instance.get_rule_cache_keys(rule)
        self.assertEqual(len(keys), 0)

        rule_alert_handler_instance.update_rule_cache(rule, "test_key1", "test_value1")
        rule_alert_handler_instance.update_rule_cache(rule, "test_key2", "test_value2")
        rule_alert_handler_instance.update_rule_cache(rule, "test_key3", "test_value3")

        keys = rule_alert_handler_instance.get_rule_cache_keys(rule)
        self.assertEqual(len(keys), 3)
        self.assertTrue("test_key1" in keys)
        self.assertTrue("test_key2" in keys)
        self.assertTrue("test_key3" in keys)



if __name__ == '__main__':
    unittest.main()
