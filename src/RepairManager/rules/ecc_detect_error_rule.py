import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rules_abc import Rule
from actions.cordon_action import CordonAction
from actions.send_alert_action import SendAlertAction
from kubernetes import client, config
from utils import k8s_util, email_util, prometheus_util
from datetime import datetime, timezone
import requests
import json
import yaml
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

activity_log = logging.getLogger('activity')


def _create_email_for_dris(nodes, action_status, jobs, cluster_name):
    message = MIMEMultipart()
    message['Subject'] = f'Repair Manager Alert [ECC ERROR] [{cluster_name}]'
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


def _create_email_for_job_owner(job_id, job_owner_email, node_names, job_link, 
                                cluster_name, reboot_enabled, days_until_reboot):
    message = MIMEMultipart()
    message['Subject'] = f'Repair Manager Alert [ECC ERROR] [{job_id}]'
    message['To'] = job_owner_email
    body = f'''<p>Uncorrectable ECC Error found in {cluster_name} cluster on following node(s):</p>
    <table border="1">'''
    for node in node_names:
        body += f'''<tr><td>{node}</td></tr>'''
    body += f'''</table><p>The node(s) will require reboot in order to repair.
    The following job is impacted:</p> <a href="{job_link}">{job_id}</a>
    <p>Please save and end your job ASAP. '''

    if reboot_enabled:
        body += f'''Node(s) will be rebooted in {days_until_reboot} days and all progress will be lost.</p>'''
    else:
        body += f'''Node(s) will be rebooted soon for repair and all progress will be lost</p>'''

    message.attach(MIMEText(body, 'html'))
    return message


class EccDetectErrorRule(Rule):

    def __init__(self, alert, config):
        self.rule = 'ecc_rule'
        self.config = config
        self.ecc_config = self.load_ecc_config()
        self.new_bad_nodes = {}
        self.node_info = {}
        self.alert = alert


    def load_ecc_config(self):
        with open('/etc/RepairManager/config/ecc-config.yaml', 'r') as file:
            return yaml.safe_load(file)


    def update_rule_cache_with_bad_nodes(self):
        for node_name in self.new_bad_nodes:
            cache_value = {
                'time_found': datetime.utcnow().strftime(self.config['date_time_format']),
                'instance': self.new_bad_nodes[node_name]
            }
            self.alert.update_rule_cache(self.rule, node_name, cache_value)
    
        logging.debug(f"rule_cache: {json.dumps(self.alert.rule_cache, default=str)}")


    def check_status(self):
        url = f"http://{self.config['prometheus']['ip']}:{self.config['prometheus']['port']}"
        query = self.config['prometheus']['ecc_error_query']
        ecc_url = prometheus_util.format_url_query(url, query)

        try:
            response = requests.get(ecc_url, timeout=10)
            if response:
                logging.debug(f'NvidiaSmiECCError Response: {response}')
                node_ips = prometheus_util.extract_ips_from_response(response)
                if node_ips:
                    address_map = k8s_util.get_node_address_info()
                    for ip in node_ips:
                        node_name = address_map[ip]
                        if not self.alert.check_rule_cache(self.rule, node_name):
                            self.new_bad_nodes[node_name] = ip
                    logging.info(f'Uncorrectable ECC metrics: {self.new_bad_nodes}')
                    return len(self.new_bad_nodes) > 0
                else:
                    logging.debug('No uncorrectable ECC metrics found.')
            else:
                logging.warning(f'Response from {ecc_url} was None.')
        except:
            logging.exception(f'Error retrieving data from {ecc_url}')

        return False


    def take_action(self):
        # cordon nodes
        cordon_dry_run = not self.ecc_config['enable_cordon']
        action_status = {}
        for node_name in self.new_bad_nodes:
            cordon_action = CordonAction()
            action_status[node_name] = cordon_action.execute(
                node_name=node_name,
                dry_run=cordon_dry_run)

        impacted_jobs = k8s_util.get_job_info_indexed_by_job_id(
            nodes=self.new_bad_nodes,
            portal_url=self.config['portal_url'],
            cluster_name=self.config['cluster_name'])

        # send alert email to DRI
        dri_message = _create_email_for_dris(
            nodes=self.new_bad_nodes,
            action_status=action_status,
            jobs=impacted_jobs,
            cluster_name=self.config['cluster_name']
        )
        alert_action = SendAlertAction(self.alert)
        alert_action.execute(dri_message, additional_log={"bad_nodes": self.new_bad_nodes})

        # send alert email to impacted job owners
        for job_id, job_info in impacted_jobs.items():
            job_owner_message = _create_email_for_job_owner(
                job_id=job_id,
                job_owner_email=f"{job_info['user_name']}@{self.config['job_owner_email_domain']}",
                node_names=job_info['node_names'],
                job_link=job_info['job_link'],
                cluster_name=self.config['cluster_name'],
                reboot_enabled=self.ecc_config['enable_reboot'],
                days_until_reboot=self.ecc_config.get('days_until_node_reboot', 5)
            )
            if not cordon_dry_run and self.ecc_config['enable_alert_job_owners']:
                alert_dry_run = False
            else:
                alert_dry_run = True
            alert_action.execute(
                message=job_owner_message,
                dry_run=alert_dry_run,
                additional_log={"job_id": job_id,
                                "job_owner": job_info['user_name'],
                                "nodes": job_info['node_names']})

        self.update_rule_cache_with_bad_nodes()
