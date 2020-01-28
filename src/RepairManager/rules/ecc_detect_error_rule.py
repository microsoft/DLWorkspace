import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rules_abc import Rule
from kubernetes import client, config
from utils import k8s_util, email_util, prometheus_url
from tabulate import tabulate
import datetime
import requests
import json
import yaml
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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


def extract_ips_from_ecc_data(ecc_data):
    metrics = ecc_data['data']['result']
    if metrics:
        ecc_node_ips = []
        for m in metrics:
            offending_node_ip = m['metric']['instance'].split(':')[0]
            ecc_node_ips.append(offending_node_ip)
        return ecc_node_ips


def get_job_info_from_nodes(nodes, cluster_name):
    pods = k8s_util.list_pod_for_all_namespaces()
    jobs = {}
    for pod in pods.items:
        if pod.metadata and pod.metadata.labels:
            if 'jobId' in pod.metadata.labels and 'userName' in pod.metadata.labels:
                if pod.spec.node_name in nodes:
                    jobId = pod.metadata.labels['jobId']
                    userName = pod.metadata.labels['userName']
                    nodeName = pod.spec.node_name
                    vcName = pod.metadata.labels['vcName']
                    if jobId not in jobs:
                        jobs[jobId] = {
                        'userName': userName,
                        'nodeName': {nodeName},
                        'vcName': vcName,
                        'jobLink': f"/job/{vcName}/{cluster_name}/{jobId}"}
                    else:
                        jobs[jobId]['nodeName'].add(nodeName)
    return jobs


class ECCDetectErrorRule(Rule):

    def __init__(self, alert, config):
        self.config = config
        self.ecc_config = self.load_ecc_config()
        self.ecc_node_hostnames = []
        self.node_info = {}
        self.alert = alert


    def load_ecc_config(self):
        with open('./config/ecc-config.yaml', 'r') as file:
            return yaml.safe_load(file)

    def create_email_for_DRIs(self, node_name, output):
        message = MIMEMultipart()
        message['Subject'] = f'Repair Manager Alert [ECC ERROR] [{self.config["cluster_name"]}] [{node_name}]'
        message['To'] = self.ecc_config["dri_email"]
        body = f'''<h3>Uncorrectable ECC Error found in {self.config["cluster_name"]} cluster on node {node_name}.</h3>
        <p>Node Status: {output}</p>'''
        message.attach(MIMEText(body, 'html'))
        return message


    def create_email_for_job_owner(self, job_id, job_info):
        message = MIMEMultipart()
        message['Subject'] = f'Repair Manager Alert [ECC ERROR] [{job_id}]'
        message['To'] = f'{job_info["userName"]}@{self.ecc_config["job_owner_domain"]}'
        message['CC'] = self.ecc_config["dri_email"]
        body = f'''<h3>Uncorrectable ECC Error found in {self.config["cluster_name"]} cluster on node(s) {', '.join(job_info["nodeName"])}</h3>
        <p>The following job is impacted:</p>
        <a href="{job_info["jobLink"]}">{job_id}</a>
        <p>Please save and end your job ASAP. Node(s) {','.join(job_info["nodeName"])} will be restarted in \
         {self.ecc_config["days_until_node_reboot"]} days and all progress will be lost.</p>'''
        message.attach(MIMEText(body, 'html'))
        return message


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
                ecc_node_ips = extract_ips_from_ecc_data(ecc_data)
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
        for node_name in self.ecc_node_hostnames:
            node_cordoned = False
            if k8s_util.is_node_cordoned(self.node_info, node_name):
                action_output = f'no action taken: {node_name} already cordoned'
            else:
                action_output = k8s_util.cordon_node(node_name, dry_run=self.ecc_config['cordon_dry_run'])
                node_cordoned = True

            if node_cordoned or not self.alert.check_rule_cache("ecc_rule", node_name):
                logging.info(f'Alerting DRIs --> node {node_name} with ecc error: {action_output}')
                dri_message = self.create_email_for_DRIs(node_name, action_output)
                self.alert.send_alert(dri_message)

        if self.ecc_config["alert_job_owners"]:
            jobs = get_job_info_from_nodes(self.ecc_node_hostnames, self.config["cluster_name"])
            for job_id in jobs:
                job_info = jobs[job_id]
                if not self.alert.check_rule_cache("ecc_rule", node_name):
                    job_owner_message = self.create_email_for_job_owner(job_id, job_info)
                    self.alert.send_alert(job_owner_message)

        for node_name in self.ecc_node_hostnames:
            if not self.alert.check_rule_cache("ecc_rule", node_name):
                cache_value = {
                    "time_found": datetime.datetime.now(datetime.timezone.utc)
                }
                self.alert.update_rule_cache("ecc_rule", node_name, cache_value)
