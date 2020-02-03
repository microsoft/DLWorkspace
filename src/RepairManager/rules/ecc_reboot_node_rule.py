import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import yaml
import requests
from datetime import datetime, timedelta
from rules_abc import Rule
from utils import prometheus_url

def _extract_node_boot_time_info(response):
    node_boot_times = {}

    if response is not None and "data" in response:
        if "result" in response["data"]:
            for m in response["data"]["result"]:
                instance = m["metric"]["instance"]
                boot_datetime = datetime.utcfromtimestamp(float(m["value"][1]))
                node_boot_times[instance] = boot_datetime
    
    return node_boot_times

    
class ECCRebootNodeRule(Rule):

    def __init__(self, alert, config):
        self.alert = alert
        self.config = config
        self.ecc_config = self.load_ecc_config()
        self.nodes_ready_for_action = []

    def load_ecc_config(self):
        with open('./config/ecc-config.yaml', 'r') as file:
            return yaml.safe_load(file)

    def check_status(self):
        url = f"http://{self.ecc_config['prometheus']['ip']}:{self.ecc_config['prometheus']['port']}"
        query = self.ecc_config['prometheus']['node_boot_time_query']
        reboot_url = prometheus_url.format_prometheus_url_query(url, query)

        try:
            response = requests.get(reboot_url, timeout=10)
            if response:
                reboot_data = response.json()
                reboot_times = _extract_node_boot_time_info(reboot_data)
                
                # if node has been rebooted since ecc error first detected,
                # remove from rule_cache
                remove_from_cache = []
                for node in self.alert.rule_cache["ecc_rule"]:
                    instance = self.alert.rule_cache["ecc_rule"][node]["instance"]
                    time_found = self.alert.rule_cache["ecc_rule"][node]["time_found"]
                    last_reboot_time = reboot_times[instance]
                    if last_reboot_time > time_found:
                        remove_from_cache.append(node)

                for node in remove_from_cache:
                    self.alert.remove_from_rule_cache("ecc_rule", node)
        except:
            logging.exception(f'Error retrieving data from {reboot_url}')

        # if configured time has elapsed since first detection
        for node in self.alert.rule_cache["ecc_rule"]:
            time_found = self.alert.rule_cache["ecc_rule"][node]["time_found"]
            delta = timedelta(days=self.ecc_config["days_until_node_reboot"])
            if datetime.now() - time_found > delta:
                self.nodes_ready_for_action.append(node)

        return self.nodes_ready_for_action

    def take_action(self):
        logging.debug("taking action!")
        # TODO: pause/resume job

        # TODO: reboot node
