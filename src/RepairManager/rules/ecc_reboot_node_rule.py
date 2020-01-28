import logging
from rules_abc import Rule

class ECCRebootNodeRule(Rule):

    def __init__(self, alert):
        self.alert = alert

    def check_status(self):
        if "ecc_rule" in self.alert.rule_cache:
            for node in self.alert.rule_cache["ecc_rule"]:
                # if node already restarted
                    # remove from cache
                    # return false
                # if 5 days passed
                    # return true
        pass

    def take_action(self):
        logging.debug("taking action!")
        # reboot node
