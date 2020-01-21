import logging
import datetime
import yaml
from utils import email_util


class RuleAlertHandler():

    def __init__(self):
        self.email_handler = email_util.EmailHandler()
        self.config = {}
        self.rule_cache = {}


    def send_alert(self, message):
        self.email_handler.send(message)
    

    def update_rule_cache(self, rule, cache_key, cache_value):
        if rule not in self.rule_cache:
            self.rule_cache[rule] = {}
        
        self.rule_cache[rule][cache_key] = cache_value


    def remove_from_rule_cache(self, rule, cache_key):
        if rule in self.rule_cache:
            if cache_key in self.rule_cache[rule]:
                self.rule_cache[rule].pop(cache_key)


    def get_rule_cache(self, rule, cache_key):
        if rule in self.rule_cache:
            if cache_key in self.rule_cache[rule]:
                return self.rule_cache[rule][cache_key]
        return None


    def check_rule_cache(self, rule, cache_key):
        if rule in self.rule_cache:
            if cache_key in self.rule_cache[rule]:
                return True
        return False





