import logging
import datetime
from utils import email
from cachetools import TTLCache

class RuleAlertHandler():

    def __init__(self):
        self.email_handler=email.EmailHandler()
        self.rule_cache={}
        self.reminders={}


    def handle_email_alert(self, rule, subject, body, cache_items, ttl_window, reminder_wait_time):
        if cache_items is None:
            cache_items = []

        if rule not in self.rule_cache:
            self.rule_cache[rule] = TTLCache(maxsize=1000, ttl=ttl_window)
            self.reminders[rule] = datetime.datetime.now() + datetime.timedelta(seconds=reminder_wait_time)

        new_item_found = False
        for item in cache_items:
            if item not in self.rule_cache[rule]:
                new_item_found = True
            self.rule_cache[rule][item] = 1

        # if alert wait time has passed and there are still items in the cache, send reminder email
        alert_wait_time_passed = self.reminders[rule] < datetime.datetime.now() and self.rule_cache[rule]

        if new_item_found or alert_wait_time_passed:
            self.email_handler.send(subject, body)
            self.reminders[rule] = datetime.datetime.now() + datetime.timedelta(seconds=reminder_wait_time)
            logging.debug(f"next reminder time: {self.reminders[rule]}")

    # send email regardless of cache or reminder settings and update cache
    def send_email_alert(self, rule, subject, body, cache_items, ttl_window, reminder_wait_time):
            if rule not in self.rule_cache:
                self.rule_cache[rule] = TTLCache(maxsize=1000, ttl=ttl_window)

            for item in cache_items:
                self.rule_cache[rule][item] = 1

            self.email_handler.send(subject, body)
            self.reminders[rule] = datetime.datetime.now() + datetime.timedelta(seconds=reminder_wait_time)
            logging.debug(f"next reminder time: {self.reminders[rule]}")

