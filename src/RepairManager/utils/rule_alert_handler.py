import logging
import datetime
import yaml
from utils import email
from cachetools import TTLCache

def load_rule_config():
    with open('./config/rule-alerts.yaml', 'r') as file:
        return yaml.safe_load(file)

class RuleAlertHandler():

    def __init__(self):
        self.email_handler = email.EmailHandler()
        self.config = {}
        self.rule_cache = {}
        self.next_reminder = {}

    def _reminders_are_enabled(self, rule):
        return rule in self.config \
                and 'reminders_enabled' in self.config[rule] \
                and self.config[rule]['reminders_enabled']

    def _is_time_to_send_reminder(self, rule):
        return self._reminders_are_enabled(rule) \
                and self.rule_cache[rule] \
                and self.next_reminder[rule] is not None \
                and self.next_reminder[rule] < datetime.datetime.now()


    def _update_next_reminder(self, rule):
        reminder_wait_time = self.config[rule]['reminder_wait_time']
        self.next_reminder[rule] = datetime.datetime.now() + datetime.timedelta(seconds=reminder_wait_time)
        logging.debug(f"next reminder will be sent at {self.next_reminder[rule]}")


    # send alert if items not cached or reminder is due
    def handle_alert(self, rule, subject, body, cache_items):
        self.config = load_rule_config() # refresh config

        if rule not in self.rule_cache:
            self.rule_cache[rule] = TTLCache(maxsize=1000, ttl=self.config['cache-ttl'])
        if rule not in self.next_reminder:
            self.next_reminder[rule] = None

        new_item_found = False
        for item in cache_items:
            if item not in self.rule_cache[rule]:
                new_item_found = True
            self.rule_cache[rule][item] = 1 # update cache

        if self.config[rule]['alerts_enabled']:
            if new_item_found or self._is_time_to_send_reminder(rule):
                self.email_handler.send(subject, body)
                if self._reminders_are_enabled(rule):
                    self._update_next_reminder(rule)


    def send_alert(self, rule, subject, body, cache_items):
        self.config = load_rule_config()

        if rule not in self.rule_cache:
            self.rule_cache[rule] = TTLCache(maxsize=1000, ttl=self.config['cache-ttl'])
        if rule not in self.next_reminder:
            self.next_reminder[rule] = None

        # update cache
        for item in cache_items:
            self.rule_cache[rule][item] = 1

        if self.config[rule]['alerts_enabled']:
            self.email_handler.send(subject, body)
            if self._reminders_are_enabled(rule):
                self._update_next_reminder(rule)





