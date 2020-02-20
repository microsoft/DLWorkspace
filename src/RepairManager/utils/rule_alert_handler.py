import logging
import datetime
import yaml
import json
from pathlib import Path
from utils import email_util


class RuleAlertHandler():

    def __init__(self):
        self.email_handler = email_util.EmailHandler()
        self.config = self.load_config()
        self.rule_cache = self.load_rule_cache()


    def load_config(self):
        with open('/etc/RepairManager/config/rule-config.yaml', 'r') as file:
            return yaml.safe_load(file)


    def send_alert(self, message):
        self.email_handler.send(message)


    def update_rule_cache(self, rule, cache_key, cache_value):
        if rule not in self.rule_cache:
            self.rule_cache[rule] = {}
        
        self.rule_cache[rule][cache_key] = cache_value

        if 'rule_cache_dump' in self.config:
            self.dump_rule_cache()


    def remove_from_rule_cache(self, rule, cache_key):
        if rule in self.rule_cache:
            if cache_key in self.rule_cache[rule]:
                self.rule_cache[rule].pop(cache_key)

                if 'rule_cache_dump' in self.config:
                    self.dump_rule_cache()


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


    def dump_rule_cache(self):
        with open(self.config['rule_cache_dump'], 'w') as fp:
            json.dump(self.rule_cache, fp)


    def load_rule_cache(self):
        rule_cache = {}
        if self.config['restore_from_rule_cache_dump']:
            dump_file_path = self.config["rule_cache_dump"]
            dump_file = Path(dump_file_path)

            if dump_file.is_file():
                with open(dump_file_path) as fh:
                    rule_cache = json.load(fh)
        return rule_cache


