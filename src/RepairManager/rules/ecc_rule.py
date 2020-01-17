import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rules_abc import Rule
from kubernetes import client, config
from utils import k8s_util, email, prometheus_url
from tabulate import tabulate
import requests
import json
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


def extract_ips_from_ecc_data(ecc_data, ecc_percent_threshold, interval):
    metrics = ecc_data['data']['result']
    if metrics:
        ecc_node_ips = []
        for m in metrics:
            # percentage of data points with ecc error
            percent_ecc = len(m['values']) / (interval+1) * 100
            if percent_ecc >= ecc_percent_threshold:
                offending_node_ip = m['metric']['instance'].split(':')[0]
                ecc_node_ips.append(offending_node_ip)
        return ecc_node_ips


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

    def __init__(self, alert, config):
        self.config = config
        self.ecc_config = self.load_ecc_config()
        self.ecc_node_hostnames = []
        self.node_info = {}
        self.alert = alert


    def load_ecc_config(self):
        with open('./config/ecc-config.yaml', 'r') as file:
            return yaml.safe_load(file)


    def check_status(self):
        url = f"http://{self.ecc_config['prometheus']['ip']}:{self.ecc_config['prometheus']['port']}"
        query = self.ecc_config['prometheus']['ecc_error_query']
        step = self.ecc_config['prometheus']['step']
        interval = self.ecc_config['prometheus']['interval']
        ecc_url = prometheus_url.format_prometheus_url_from_interval(url, query, step, interval)

        try:
            response = requests.get(ecc_url, timeout=10)
            if response:
                ecc_data = response.json()
                percent_threshold = self.ecc_config['prometheus']['percent_threshold']
                ecc_node_ips = extract_ips_from_ecc_data(ecc_data, percent_threshold, interval)
                if ecc_node_ips:
                    self.node_info = k8s_util.list_node() # save node info to reduce API calls
                    address_map = get_node_address_info(self.node_info)
                    for ip in ecc_node_ips:
                        self.ecc_node_hostnames.append(address_map[ip])
                    logging.info(f'Uncorrectable ECC metrics found: {self.ecc_node_hostnames}')
                    return True
                else:
                    logging.debug('No uncorrectable ECC metrics found.')
            else:
                logging.warning(f'Response from {ecc_url} was None.')
        except:
            logging.exception(f'Error retrieving data from {ecc_url}')

        return False


    def take_action(self):
        node_status = []
        action_taken = False
        for node_name in self.ecc_node_hostnames:
            if k8s_util.is_node_cordoned(self.node_info, node_name):
                output = f'no action taken: {node_name} already cordoned'
            else:
                output = k8s_util.cordon_node(node_name, dry_run=self.ecc_config['cordon_dry_run'])
                action_taken = True
            node_status.append([node_name, output])

        jobs = get_job_info_from_nodes(self.ecc_node_hostnames)
        subject = f'Repair Manager Alert [ECC ERROR] [{self.config["cluster_name"]}]'
        body = create_email_body(self.config["cluster_name"], node_status, jobs)

        if action_taken and not self.ecc_config['cordon_dry_run']:
            logging.info(f"An action has been taken on one or more of the following nodes: {node_status}")
            self.alert.send_alert("ecc_rule", subject, body, self.ecc_node_hostnames)
        else: 
            self.alert.handle_alert("ecc_rule", subject, body, self.ecc_node_hostnames)
