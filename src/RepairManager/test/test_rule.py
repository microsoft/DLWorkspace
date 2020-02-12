import logging
from rules_abc import Rule

# Reference for new Rule
class TestRule(Rule):

    def __init__(self, alert, config):
        self.alert = alert
        self.config = config

    def check_status(self):
        logging.debug("checking status!")
        return True

    def take_action(self):
        logging.debug("taking action!")
