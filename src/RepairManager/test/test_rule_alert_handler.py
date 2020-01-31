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


    @mock.patch('utils.email_util.EmailHandler')
    def test_dump_and_load_rule_cache(self, mock_email_handler):
        rule_alert_handler_instance = rule_alert_handler.RuleAlertHandler()
        rule_cache_dump_file = "./test-rule-cache.json"
        rule_alert_handler_instance.config = {"rule_cache_dump": rule_cache_dump_file}

        rule = "TestRule"
        cache_key = "test_key"
        cache_value = "test_value"
        rule_alert_handler_instance.rule_cache[rule] = {cache_key: cache_value}

        # make sure file does not exist already
        _clean_up_dump_file(rule_cache_dump_file)

        rule_alert_handler_instance.dump_rule_cache()

        # assert dump file exists
        dump_file = Path(rule_cache_dump_file)
        self.assertTrue(dump_file.is_file())

        # reset rule cache
        rule_alert_handler_instance.rule_cache = {}

        rule_alert_handler_instance.load_rule_cache()

        self.assertTrue(rule in rule_alert_handler_instance.rule_cache)
        self.assertTrue(cache_key in rule_alert_handler_instance.rule_cache[rule])
        self.assertEqual(cache_value, rule_alert_handler_instance.rule_cache[rule][cache_key])

        _clean_up_dump_file(rule_cache_dump_file)
