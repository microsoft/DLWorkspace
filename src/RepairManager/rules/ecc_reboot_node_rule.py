import logging
from datetime import datetime, timedelta
from rules_abc import Rule

class ECCRebootNodeRule(Rule):

    def __init__(self, alert, config):
        self.alert = alert
        self.config = config
        self.nodes_ready_for_action = []

    def check_status(self):
        if "ecc_rule" in self.alert.rule_cache:
            for node in self.alert.rule_cache["ecc_rule"]:
                # TODO: if node already restarted
                    # remove from cache
                    # return false
                now = datetime.now()
                time_found = self.alert.rule_cache["ecc_rule"][node]["time_found"]
                delta = timedelta(days=self.config["days_until_node_reboot"])
                if now - time_found > delta:
                    self.nodes_ready_for_action.append(node)

        return self.nodes_ready_for_action

    def take_action(self):
        logging.debug("taking action!")
        # TODO: pause/resume job

        # TODO: reboot node
