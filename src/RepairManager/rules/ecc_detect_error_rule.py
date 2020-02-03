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

def _get_node_address_info(node_info):
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


def _extract_ips_from_ecc_data(ecc_data):
    metrics = ecc_data['data']['result']
    if metrics:
        ecc_node_ips = []
        for m in metrics:
            offending_node_ip = m['metric']['instance'].split(':')[0]
            ecc_node_ips.append(offending_node_ip)
        return ecc_node_ips


def _get_job_info_from_nodes(nodes, domain_name, cluster_name):
    pods = k8s_util.list_pod_for_all_namespaces()
    jobs = {}
    for pod in pods.items:
        if pod.metadata and pod.metadata.labels:
            if 'jobId' in pod.metadata.labels and 'userName' in pod.metadata.labels:
                if pod.spec.node_name in nodes:
                    job_id = pod.metadata.labels['jobId']
                    user_name = pod.metadata.labels['userName']
                    node_name = pod.spec.node_name
                    vc_name = pod.metadata.labels['vcName']
                    if job_id not in jobs:
                        jobs[job_id] = {
                        'user_name': user_name,
                        'node_names': {node_name},
                        'vc_names': vc_name,
                        'job_link': f'{domain_name}/job/{vc_name}/{cluster_name}/{job_id}'}
                    else:
                        jobs[job_id]['node_names'].add(node_name)
    return jobs

def _create_email_for_DRIs(node_name, output, cluster_name, dri_email):
    message = MIMEMultipart()
    message['Subject'] = f'Repair Manager Alert [ECC ERROR] [{cluster_name}] [{node_name}]'
    message['To'] = dri_email
    body = f'''<h3>Uncorrectable ECC Error found in {cluster_name} cluster on node {node_name}.</h3>
    <p>Node Status: {output}</p>'''
    message.attach(MIMEText(body, 'html'))
    return message


def _create_email_for_job_owner(job_id, job_owner_email, node_names, job_link, dri_email, cluster_name, days_until_reboot):
    message = MIMEMultipart()
    message['Subject'] = f'Repair Manager Alert [ECC ERROR] [{job_id}]'
    message['To'] = job_owner_email
    message['CC'] = dri_email
    body = f'''<h3>Uncorrectable ECC Error found in {cluster_name} cluster on node(s) {', '.join(node_names)}</h3>
    <p>The following job is impacted:</p>
    <a href="{job_link}">{job_id}</a>
    <p>Please save and end your job ASAP. Node(s) {', '.join(node_names)} will be restarted in \
        {days_until_reboot} days and all progress will be lost.</p>'''
    message.attach(MIMEText(body, 'html'))
    return message


class ECCDetectErrorRule(Rule):

    def __init__(self, alert, config):
        self.config = config
        self.ecc_config = self.load_ecc_config()
        self.ecc_node_hostnames = {}
        self.node_info = {}
        self.alert = alert

    def load_ecc_config(self):
        with open('./config/ecc-config.yaml', 'r') as file:
            return yaml.safe_load(file)


    def check_status(self):
        url = f"http://{self.ecc_config['prometheus']['ip']}:{self.ecc_config['prometheus']['port']}"
        query = self.ecc_config['prometheus']['ecc_error_query']
        ecc_url = prometheus_url.format_prometheus_url_query(url, query)

        try:
            response = requests.get(ecc_url, timeout=10)
            if response:
                ecc_data = response.json()
                ecc_node_ips = _extract_ips_from_ecc_data(ecc_data)
                if ecc_node_ips:
                    self.node_info = k8s_util.list_node() # save node info to reduce API calls
                    address_map = _get_node_address_info(self.node_info)
                    for ip in ecc_node_ips:
                        self.ecc_node_hostnames[address_map[ip]] = ip
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

            if node_cordoned or not self.alert.check_rule_cache('ecc_rule', node_name):
                logging.info(f'Alerting DRIs --> node {node_name} with ecc error: {action_output}')
                dri_message = _create_email_for_DRIs(node_name, action_output, self.config['cluster_name'], self.ecc_config['dri_email'])
                self.alert.send_alert(dri_message)

        if self.ecc_config['alert_job_owners']:
            jobs = _get_job_info_from_nodes(self.ecc_node_hostnames, self.config['domain_name'], self.config['cluster_name'])
            for job_id in jobs:
                job_info = jobs[job_id]
                if not self.alert.check_rule_cache('ecc_rule', node_name):
                    email_params = {
                        'job_id': job_id,
                        'job_owner_email': f"{job_info['user_name']}@{self.config['job_owner_email_domain']}",
                        'node_names': job_info['node_names'],
                        'job_link': job_info['job_link'],
                        'dri_email': self.ecc_config['dri_email'],
                        'cluster_name': self.config['cluster_name'],
                        'days_until_reboot': self.ecc_config['days_until_node_reboot']
                    }
                    job_owner_message = _create_email_for_job_owner(**email_params)
                    self.alert.send_alert(job_owner_message)

        for node_name in self.ecc_node_hostnames:
            if not self.alert.check_rule_cache('ecc_rule', node_name):
                cache_value = {
                    'time_found': datetime.datetime.now(datetime.timezone.utc),
                    'instance': self.ecc_node_hostnames[node_name]
                }
                self.alert.update_rule_cache('ecc_rule', node_name, cache_value)
