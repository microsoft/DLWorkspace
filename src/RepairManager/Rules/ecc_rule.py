from Rules.rules_abc import Rule
from kubernetes import client, config
from utils import k8s_util, email
import requests
import json
import os
import time
import yaml
import logging

def get_node_address_info(node_info):
    # map InternalIP to Hostname
    address_map = {}
    
    if node_info:

        for node in node_info.items:
            internal_ip = None
            hostname = None

            for address in node.status.addresses:
                if address.type == 'InternalIP':
                    internal_ip = address.address

                if address.type == 'Hostname':
                    hostname = address.address
            
                address_map[internal_ip] = hostname

    logging.debug('node address map: %s ' %  address_map)

    return address_map



def get_ECC_error_data(ecc_url):

    response = requests.get(ecc_url)
    data = json.loads(response.text)

    if data:
        ecc_metrics = data['data']['result']
        logging.info('ECC error metrics from prometheus: ' + json.dumps(ecc_metrics))

        return ecc_metrics



class ECCRule(Rule):

    def __init__(self, alert):
        self.config = self.load_rule_config()
        self.ecc_hostnames = []
        self.node_info = {}
        self.alert = alert

    def load_rule_config(self):
        with open('./config/rule-config.yaml', 'r') as file:
            return yaml.safe_load(file)

    def check_status(self):
        # save node_info to reduce the number of API calls
        self.node_info = k8s_util.list_node()

        address_map = get_node_address_info(self.node_info)

        ecc_url = os.environ['PROMETHEUS_HOST'] + self.config['rules']['ecc_rule']['ecc_error_url']
        ecc_metrics = get_ECC_error_data(ecc_url)

        if ecc_metrics:
            for m in ecc_metrics:
                offending_node_ip = m['metric']['instance'].split(':')[0]
                self.ecc_hostnames.append(address_map[offending_node_ip])

            logging.info(f'Uncorrectable ECC metrics found: {self.ecc_hostnames}')
            return True
        else:
            logging.debug('No uncorrectable ECC metrics found.')
            return False

    def take_action(self):
        status = {}

        for node_name in self.ecc_hostnames:
            output = k8s_util.cordon_node(node_name, dry_run=True)
            status[node_name] = output

        body = f'Uncorrectable ECC Error found in {self.config["cluster_name"]} cluster on the following nodes:\n'
        for node_name in status:
            body += f'{node_name}:\t{status[node_name]}\n\n'

        subject = f'Repair Manager Alert [ECC ERROR] [{self.config["cluster_name"]}]'
        self.alert.handle_email_alert(subject, body)