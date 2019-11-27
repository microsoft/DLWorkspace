from Rules.rules_abc import Rule
from kubernetes import client, config
import requests
import json
import os
import time
import yaml
import util
import k8s_util
import logging

def list_node():
    config.load_kube_config(config_file='/etc/kubernetes/restapi-kubeconfig.yaml')
    api_instance = client.CoreV1Api()

    return api_instance.list_node()


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

    def __init__(self):
        self.ecc_hostnames = []
        self.config = self.load_config()
        self.node_info = {}

    def load_config(self):
        with open('rule-config.yaml', 'r') as rule_file:
            return yaml.safe_load(rule_file)

    def check_status(self):
        # save node_info to reduce the number of API calls
        self.node_info = list_node()
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
        body = 'ECC Error found on the following nodes:\n'
        all_nodes_already_unscheduled = True

        for node_name in self.ecc_hostnames:

            if not k8s_util.is_node_unschedulable(self.node_info, node_name):
                all_nodes_already_unscheduled = False
                success = k8s_util.cordon_node(node_name)

                if success != 0:
                    logging.warning(f'Unscheduling of node {node_name} not successful')
                    body += f'{node_name}: Failed to mark as unschedulable\n'
                else:
                    body += f'{node_name}: Successfully marked as unschedulable\n'

        if not all_nodes_already_unscheduled:
            alert_info = self.config['email_alerts']
            subject = 'Repair Manager Alert [ECC ERROR]'
            util.smtp_send_email(**alert_info, subject=subject, body=body)

