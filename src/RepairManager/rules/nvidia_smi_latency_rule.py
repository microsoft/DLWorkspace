import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rules_abc import Rule
from actions.cordon_action import CordonAction
from actions.send_alert_action import SendAlertAction
from kubernetes import client, config
from utils import k8s_util, email_util, prometheus_util
from datetime import datetime, timezone, timedelta
import requests
import json
import yaml
import logging
from cachetools import TTLCache
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

activity_log = logging.getLogger('activity')


def _create_email_for_dris(impacted_nodes, cluster_name):
    message = MIMEMultipart()
    message['Subject'] = f'Repair Manager Alert [NVIDIA SMI LATENCY TOO LARGE] [{cluster_name}]'
    body = '<p>95th nvidia-smi call latency is larger than 40s in the following nodes. ' \
    'Please check the GPU status.</p>'
    body += f'<table border="1"><tr><th>Node Name</th><th>Instance</th></tr>'
    for node in impacted_nodes:
        body += f'''<tr><td>{node}</td><td>{impacted_nodes[node]}</td></tr>'''
    body += '</table>'
    message.attach(MIMEText(body, 'html'))
    return message


class NvidiaSmiLatencyRule(Rule):

    def __init__(self, alert, config):
        self.rule = 'smi_latency_rule'
        self.config = config
        self.latency_config = self.load_latency_config()
        self.impacted_nodes = {}
        self.node_info = {}
        self.alert = alert


    def load_latency_config(self):
        with open('/etc/RepairManager/config/latency-config.yaml', 'r') as file:
            return yaml.safe_load(file)


    def update_rule_cache_with_impacted_nodes(self):
        for node_name in self.impacted_nodes:
            cache_value = {
                'time_found': datetime.utcnow().strftime(self.config['date_time_format']),
                'instance': self.impacted_nodes[node_name]
            }
            self.alert.update_rule_cache(self.rule, node_name, cache_value)
    
        logging.debug(f"rule_cache: {json.dumps(self.alert.rule_cache, default=str)}")


    def clean_expired_items_in_rule_cache(self):
        expired_nodes = []
        if self.rule in self.alert.rule_cache:
            for node in self.alert.rule_cache[self.rule]:
                time_found_string = self.alert.rule_cache[self.rule][node]["time_found"]
                time_found_datetime = datetime.strptime(time_found_string, self.config['date_time_format'])
                alert_delta = timedelta(hours=self.latency_config.get("alert_expiry", 4))
                now = datetime.utcnow()
                if now - time_found_datetime > alert_delta:
                    expired_nodes.append(node)
        for node in expired_nodes:
            self.alert.remove_from_rule_cache(self.rule, node)


    def check_status(self):
        self.clean_expired_items_in_rule_cache()

        url = f"http://{self.config['prometheus']['ip']}:{self.config['prometheus']['port']}"
        query = self.config['prometheus']['large_latency_query']
        latency_url = prometheus_util.format_url_query(url, query)

        try:
            response = requests.get(latency_url, timeout=10)
            if response:
                logging.info(f'NvidiaSmiLatencyTooLarge Response: {response}')
                node_ips = prometheus_util.extract_ips_from_response(response)
                if node_ips:
                    address_map = k8s_util.get_node_address_info()
                    for ip in node_ips:
                        node_name = address_map[ip]
                        if not self.alert.check_rule_cache(self.rule, node_name):
                            self.impacted_nodes[node_name] = ip
                    return len(self.impacted_nodes) > 0
                else:
                    logging.debug('No latency metrics found.')
            else:
                logging.warning(f'Response from {latency_url} was None.')
        except:
            logging.exception(f'Error retrieving data from {latency_url}')

        return False


    def take_action(self):
        dri_message = _create_email_for_dris(
            impacted_nodes=self.impacted_nodes,
            cluster_name=self.config['cluster_name']
        )
        alert_action = SendAlertAction(self.alert)
        alert_action.execute(dri_message, additional_log={"impacted_nodes": self.impacted_nodes})

        self.update_rule_cache_with_impacted_nodes()
