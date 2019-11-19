from Rules.rules_abc import Rule
from kubernetes import client, config
import requests
import json
import os
import time
import yaml
import util
import logging

def get_node_address_info():
    config.load_kube_config(config_file='/etc/kubernetes/restapi-kubeconfig.yaml')
    api_instance = client.CoreV1Api()

    service_account_list = api_instance.list_node()

    # map InternalIP to Hostname
    address_map = {}
    
    if (service_account_list):

        for account in service_account_list.items:
            internal_ip = None
            hostname = None

            for address in account.status.addresses:
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

    def check_status(self):
        try:
            with open('rule-config.yaml', 'r') as rule_config:
                config = yaml.safe_load(rule_config)
                       
            address_map = get_node_address_info()

            ecc_url = os.environ['PROMETHEUS_HOST'] + config['rules']['ecc_rule']['ecc_error_url']
            ecc_metrics = get_ECC_error_data(ecc_url)
    
            if (ecc_metrics):
                for m in ecc_metrics:
                    offending_node_ip = m['metric']['instance'].split(':')[0]
                    ecc_hostnames.append(address_map[offending_node_ip])

                logging.info('Uncorrectable ECC metrics found: ' + ecc_hostnames)
                return True
                
            else:
                logging.debug('No uncorrectable ECC metrics found.')
                return False



        except Exception as e:
            logging.exception('Error checking status for ECCRule')
            #TODO: send email alert, raise exception?
        
    def take_action(self):
        try:
            for node in ecc_hostnames:
                success = util.cordon_node(node)

                if (success != 0):
                    logging.warning('Unscheduling of node ' + node + ' not successful')

        except Exception as e:
            logging.exception('Error taking action for ECCRule')
            #TODO: send email alert, rasie exception?
