from Rules.rules_abc import Rule
from kubernetes import client, config
from utils import k8s_util, email
from tabulate import tabulate
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
    logging.debug(f'node address map: {address_map}')
    return address_map


def get_ECC_error_data(ecc_url):
    try:
        response = requests.get(ecc_url)
        if response:
            data = json.loads(response.text)
            if data:
                ecc_metrics = data['data']['result']
                logging.info('ECC error metrics from prometheus: ' + json.dumps(ecc_metrics))
                return ecc_metrics
        else:
            logging.warning(f'No response from {ecc_url} found.')
    except:
        logging.exception(f'Error retrieving data from {ecc_url}')


def get_job_info_from_nodes(nodes):
    pods = k8s_util.list_pod_for_all_namespaces()
    jobs = {}
    for pod in pods.items:
        if pod.metadata and pod.metadata.labels:
            if 'jobId' in pod.metadata.labels and 'userName' in pod.metadata.labels:
                if pod.spec.node_name in nodes:
                    jobs[pod.metadata.labels['jobId']] = {
                    'userName': pod.metadata.labels['userName'],
                    'nodeName': pod.spec.node_name,
                    'vcName': pod.metadata.labels['vcName']}
    return jobs


def create_email_body(cluster_name, node_status, jobs):
        body = f'<h3>Uncorrectable ECC Error found in {cluster_name} cluster on the following nodes:</h3>'
        body += tabulate(node_status, headers=['node name', 'action status'], tablefmt="html").replace('<table>','<table border="1">')

        job_table = []
        for job_id in jobs:
            job_table.append([job_id, jobs[job_id]['userName'], jobs[job_id]['nodeName'], jobs[job_id]['vcName']])

        body += f'<h3>Impacted Jobs and Job Owners</h3>'
        body += tabulate(job_table, headers=['job id', 'job owner', 'node name', 'vc name' ], tablefmt="html").replace('<table>','<table border="1">')
        return body


class ECCRule(Rule):

    def __init__(self, alert):
        self.config = self.load_rule_config()
        self.ecc_node_hostnames = []
        self.node_info = {}
        self.alert = alert


    def load_rule_config(self):
        with open('./config/rule-config.yaml', 'r') as file:
            return yaml.safe_load(file)


    def check_status(self):
        self.node_info = k8s_util.list_node() # save node_info to reduce the number of API calls
        address_map = get_node_address_info(self.node_info)
        ecc_url = os.environ['PROMETHEUS_HOST'] + self.config['rules']['ecc_rule']['ecc_error_url']
        ecc_metrics = get_ECC_error_data(ecc_url)

        if ecc_metrics:
            for m in ecc_metrics:
                offending_node_ip = m['metric']['instance'].split(':')[0]
                self.ecc_node_hostnames.append(address_map[offending_node_ip])
            logging.info(f'Uncorrectable ECC metrics found: {self.ecc_node_hostnames}')
            return True
        else:
            logging.debug('No uncorrectable ECC metrics found.')
            self.alert.clear_ecc_alert_cache()
            return False


    def take_action(self):
        node_status = []
        action_taken = False
        for node_name in self.ecc_node_hostnames:
            if k8s_util.is_node_cordoned(self.node_info, node_name):
                output = f'{node_name} already cordoned'
            else:
                output = k8s_util.cordon_node(node_name, dry_run=self.config['rules']['ecc_rule']['cordon_dry_run'])
                action_taken = True
            node_status.append([node_name, output])

        jobs = get_job_info_from_nodes(self.ecc_node_hostnames)
        subject = f'Repair Manager Alert [ECC ERROR] [{self.config["cluster_name"]}]'
        body = create_email_body(self.config["cluster_name"], node_status, jobs)

        if action_taken:
            logging.info(f"An action has been taken on one or more of the following nodes: {node_status}")
            self.alert.send_email_alert("ecc_rule", subject, body, self.ecc_node_hostnames, 
                self.config['rules']['ecc_rule']['node_ttl_window'], self.config['rules']['ecc_rule']['reminder_wait_time'])
        else: # send email alert based on rule cache
            self.alert.handle_email_alert("ecc_rule", subject, body, self.ecc_node_hostnames, 
                self.config['rules']['ecc_rule']['node_ttl_window'], self.config['rules']['ecc_rule']['reminder_wait_time'])
