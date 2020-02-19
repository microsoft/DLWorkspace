import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rules_abc import Rule
from kubernetes import client, config
from utils import k8s_util, email_util, prometheus_url
from datetime import datetime, timezone
import requests
import json
import yaml
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

activity_log = logging.getLogger('activity')

DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

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


def _create_email_for_dris(nodes, action_status, jobs, cluster_name, dri_email):
    message = MIMEMultipart()
    message['Subject'] = f'Repair Manager Alert [ECC ERROR] [{cluster_name}]'
    message['To'] = dri_email
    body = f'<p>Uncorrectable ECC Error found in cluster {cluster_name} on the following node(s):</p>'
    body += f'<table border="1"><tr><th>Node Name</th><th>Action Status</th></tr>'
    for node in action_status:
        body += f'''<tr><td>{node}</td><td>{action_status[node]}</td></tr>'''
    body += '</table>'
    body += f'''<p>Impacted Jobs:</p>
    <table border="1"><tr><th>Job Id</th><th>Job Owner</th><th>Node Names</th><th>VC</th></tr>'''
    for job_id, job_info in jobs.items():
        body += f'''<tr><td><a href="{job_info['job_link']}">{job_id}</a></td>
        <td>{job_info['user_name']}</td>
        <td>{', '.join(job_info['node_names'])}</td>
        <td>{job_info['vc_name']}</td></tr>'''
    body += '</table>'
    message.attach(MIMEText(body, 'html'))
    return message


def _create_email_for_job_owner(job_id, job_owner_email, node_names, job_link, dri_email, 
                                cluster_name, reboot_dry_run, days_until_reboot):
    message = MIMEMultipart()
    message['Subject'] = f'Repair Manager Alert [ECC ERROR] [{job_id}]'
    message['To'] = job_owner_email
    message['CC'] = dri_email
    body = f'''<p>Uncorrectable ECC Error found in {cluster_name} cluster on following node(s):</p>
    <table border="1">'''
    for node in node_names:
        body += f'''<tr><td>{node}</td></tr>'''
    body += f'''</table><p>The node(s) will require reboot in order to repair.
    The following job is impacted:</p> <a href="{job_link}">{job_id}</a>
    <p>Please save and end your job ASAP. '''

    if reboot_dry_run:
        body += f'''Node(s) will be rebooted soon for repair and all progress will be lost</p>'''
    else:
        body += f'''Node(s) will be rebooted in {days_until_reboot} days and all progress will be lost.</p>'''

    message.attach(MIMEText(body, 'html'))
    return message


class ECCDetectErrorRule(Rule):

    def __init__(self, alert, config):
        self.rule = 'ecc_rule'
        self.config = config
        self.ecc_config = self.load_ecc_config()
        self.new_bad_nodes = {}
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
                logging.info(f'Uncorrectable ECC metrics found: {ecc_data}')
                ecc_node_ips = _extract_ips_from_ecc_data(ecc_data)
                if ecc_node_ips:
                    self.node_info = k8s_util.list_node()
                    address_map = _get_node_address_info(self.node_info)
                    for ip in ecc_node_ips:
                        node_name = address_map[ip]
                        if not self.alert.check_rule_cache(self.rule, node_name):
                            self.new_bad_nodes[node_name] = ip
                    return len(self.new_bad_nodes) > 0
                else:
                    logging.debug('No uncorrectable ECC metrics found.')
            else:
                logging.warning(f'Response from {ecc_url} was None.')
        except:
            logging.exception(f'Error retrieving data from {ecc_url}')

        return False


    def take_action(self):
        pods = k8s_util.list_namespaced_pod("default")
        job_params = {
            "pods": pods,
            "nodes": self.new_bad_nodes,
            "domain_name": self.config["domain_name"],
            "cluster_name": self.config["cluster_name"]
        }
        impacted_jobs = k8s_util._get_job_info_from_nodes(**job_params)

        action_status = {}
        
        for node_name in self.new_bad_nodes:
            # cordon node
            if k8s_util.is_node_cordoned(self.node_info, node_name):
                action_status[node_name] = f'no action taken: {node_name} already cordoned'
            else:
                action_status[node_name] = k8s_util.cordon_node(node_name, dry_run=self.ecc_config['cordon_dry_run'])
                activity_log.info({"action":"cordon","node":node_name,"dry_run":self.ecc_config['cordon_dry_run']})


        # send email to DRI
        email_params = {
            "nodes": self.new_bad_nodes,
            "action_status": action_status,
            "jobs": impacted_jobs,
            "cluster_name": self.config['cluster_name'],
            "dri_email": self.ecc_config['dri_email']
        }
        dri_message = _create_email_for_dris(**email_params)
        self.alert.send_alert(dri_message)
        activity_log.info({"action":"dri alert - ecc error detected","nodes":self.new_bad_nodes})

        # alert impacted job owners
        if self.ecc_config['alert_job_owners']:
            for job_id, job_info in impacted_jobs.items():
                email_params = {
                    'job_id': job_id,
                    'job_owner_email': f"{job_info['user_name']}@{self.config['job_owner_email_domain']}",
                    'node_names': job_info['node_names'],
                    'job_link': job_info['job_link'],
                    'dri_email': self.ecc_config['dri_email'],
                    'cluster_name': self.config['cluster_name'],
                    'reboot_dry_run': self.ecc_config['reboot_dry_run'],
                    'days_until_reboot': self.ecc_config['days_until_node_reboot']
                }
                job_owner_message = _create_email_for_job_owner(**email_params)
                self.alert.send_alert(job_owner_message)
                activity_log.info({"action":"job owner alert - request to end job","job_id":job_id,
                "job_owner":job_info['user_name'],"nodes":job_info['node_names']})

        for node_name in self.new_bad_nodes:
            cache_value = {
                'time_found': datetime.utcnow().strftime(DATE_FORMAT),
                'instance': self.new_bad_nodes[node_name]
            }
            self.alert.update_rule_cache(self.rule, node_name, cache_value)
        
        logging.debug(f"rule_cache: {json.dumps(self.alert.rule_cache, default=str)}")

