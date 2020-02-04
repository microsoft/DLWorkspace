import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import yaml
import requests
import time
from datetime import datetime, timedelta
from rules_abc import Rule
from utils import prometheus_url, k8s_util
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def _extract_node_boot_time_info(response):
    node_boot_times = {}

    if response is not None and "data" in response:
        if "result" in response["data"]:
            for m in response["data"]["result"]:
                instance = m["metric"]["instance"]
                boot_datetime = datetime.utcfromtimestamp(float(m["value"][1]))
                node_boot_times[instance] = boot_datetime
    
    return node_boot_times


def _get_job_info_from_nodes(pods, nodes, domain_name, cluster_name):
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
                        'job_link': f'http://{domain_name}/job/{vc_name}/{cluster_name}/{job_id}'}
                    else:
                        jobs[job_id]['node_names'].add(node_name)
    return jobs


def _pause_resume_job(job_pause_url, job_id, job_owner_email, attempts, wait_time):
    try:
        for index in range(attempts):
            pause_resp = _pause_job(job_pause_url, job_id, job_owner_email)
            if pause_resp["result"] == "Success, the job is scheduled to be paused.":
                for index in range(attempts):
                    time.sleep(wait_time)
                    job_response = _get_job_status(job_pause_url, job_id)
                    if job_response:
                        if job_response["jobStatus"] == "paused":
                            _resume_job(job_pause_url, job_id, job_owner_email)
                            return True
        return False
    except:
        logging.exception(f'Error pausing/resuming job')
        return False


def _pause_job(job_pause_url, job_id, job_owner_email):
    pause_url = f'{job_pause_url}/PauseJob?userName={job_owner_email}&jobId={job_id}'
    pause_resp = requests.get(pause_url)
    return pause_resp


def _resume_job(job_pause_url, job_id, job_owner_email):
    resume_url = f'{job_pause_url}/ResumeJob?userName={job_owner_email}&jobId={job_id}'
    resume_resp = requests.get(resume_url)
    return resume_resp


def _get_job_status(job_pause_url, job_id):
    status_url = f'{job_pause_url}/GetJobStatus?jobId={job_id}'
    status_resp = requests.get(status_url)
    return status_resp


def _create_email_for_pause_resume_job(job_id, node_names, job_link, job_owner_email, dri_email):
    message = MIMEMultipart()
    message['Subject'] = f'Repair Manager Alert [{job_id} will be paused/resumed]'
    message['To'] = job_owner_email
    message['CC'] = dri_email
    body = f'''<h3>Pausing/Resuming job <a href="{job_link}">{job_id}</a>.</h3>
    <p>As previously notified, the following node(s) need to be rebooted due to uncorrectable ecc error:</p>
    <ul>'''
    for node in node_names:
        body += f'<li>{node}</li>'
    body += f'''</ul>
    <p> Job <a href="{job_link}">{job_id}</a> will be now be paused/resumed so node(s) can be repaired.</p>'''
    message.attach(MIMEText(body, 'html'))
    return message


class ECCRebootNodeRule(Rule):

    def __init__(self, alert, config):
        self.alert = alert
        self.config = config
        self.ecc_config = self.load_ecc_config()
        self.nodes_ready_for_action = []

    def load_ecc_config(self):
        with open('./config/ecc-config.yaml', 'r') as file:
            return yaml.safe_load(file)

    def check_status(self):
        url = f"http://{self.ecc_config['prometheus']['ip']}:{self.ecc_config['prometheus']['port']}"
        query = self.ecc_config['prometheus']['node_boot_time_query']
        reboot_url = prometheus_url.format_prometheus_url_query(url, query)

        try:
            response = requests.get(reboot_url, timeout=10)
            if response:
                reboot_data = response.json()
                reboot_times = _extract_node_boot_time_info(reboot_data)
                
                # if node has been rebooted since ecc error first detected,
                # remove from rule_cache
                remove_from_cache = []
                for node in self.alert.rule_cache["ecc_rule"]:
                    instance = self.alert.rule_cache["ecc_rule"][node]["instance"]
                    time_found = self.alert.rule_cache["ecc_rule"][node]["time_found"]
                    last_reboot_time = reboot_times[instance]
                    if last_reboot_time > time_found:
                        remove_from_cache.append(node)

                for node in remove_from_cache:
                    self.alert.remove_from_rule_cache("ecc_rule", node)
        except:
            logging.exception(f'Error retrieving data from {reboot_url}')

        # if configured time has elapsed since first detection
        for node in self.alert.rule_cache["ecc_rule"]:
            time_found = self.alert.rule_cache["ecc_rule"][node]["time_found"]
            delta = timedelta(days=self.ecc_config["days_until_node_reboot"])
            if datetime.now() - time_found > delta:
                self.nodes_ready_for_action.append(node)

        return self.nodes_ready_for_action

    def take_action(self):
        pods = k8s_util.list_pod_for_all_namespaces()
        job_info = _get_job_info_from_nodes(pods, 
                                            self.nodes_ready_for_action,
                                            self.config["domain_name"],
                                            self.config["cluster_name"])

        for job_id in job_info:
            job_owner_email = f"{job_info[job_id]['user_name']}@{self.config['job_owner_email_domain']}"
            node_names = job_info[job_id]["node_names"]
            result = _pause_resume_job(self.ecc_config["job_pause_resume_url"], job_id, job_owner_email, 10, self.ecc_config["time_sleep_after_pausing"])
            if result:
                if self.ecc_config["alert_job_owners"]:
                    job_link = job_info[job_id]['job_link']
                    message = _create_email_for_pause_resume_job(job_id, node_names, job_link, job_owner_email, self.ecc_config["dri_email"])
                    self.alert.send_alert(message)

        # TODO: reboot node

        for node in self.nodes_ready_for_action:
            self.alert.remove_from_rule_cache("ecc_rule", node)
