import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
import yaml
import requests
import time
from datetime import datetime, timedelta, timezone
from rules_abc import Rule
from utils import prometheus_url, k8s_util
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def _extract_node_boot_time_info(response):
    node_boot_times = {}

    if response is not None and "data" in response:
        if "result" in response["data"]:
            for m in response["data"]["result"]:
                instance = m["metric"]["instance"].split(":")[0]
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
                        'vc_name': vc_name,
                        'job_link': f'http://{domain_name}/job/{vc_name}/{cluster_name}/{job_id}'}
                    else:
                        jobs[job_id]['node_names'].add(node_name)
    return jobs


def _pause_resume_job(rest_url, job_id, job_owner_email, attempts, wait_time):
    try:
        pause_resp = _pause_job(rest_url, job_id, job_owner_email, attempts) 
        if pause_resp:      
            status_resp = _wait_for_job_to_pause(rest_url, job_id, attempts, wait_time)
            if status_resp:
                resume_resp = _resume_job(rest_url, job_id, job_owner_email, attempts)
                if resume_resp:
                    return True
    except:
        logging.exception(f'Error pausing/resuming job {job_id}')
    
    return False


def _pause_job(rest_url, job_id, job_owner_email, attempts):
    for i in range(attempts):
        pause_url = f'{rest_url}/PauseJob?userName={job_owner_email}&jobId={job_id}'
        pause_resp = requests.get(pause_url)
        if pause_resp is not None \
            and "result" in pause_resp \
            and "success" in pause_resp["result"].lower():
            return True
        time.sleep(5)
    return False


def _resume_job(rest_url, job_id, job_owner_email, attempts):
    for i in range(attempts):
        resume_url = f'{rest_url}/ResumeJob?userName={job_owner_email}&jobId={job_id}'
        resume_resp = requests.get(resume_url)
        if resume_resp is not None \
            and "result" in resume_resp \
            and "success" in resume_resp["result"].lower():
            return True
        time.sleep(5)
    return False


def _wait_for_job_to_pause(rest_url, job_id, attempts, wait_time):
    for i in range(attempts):
        time.sleep(wait_time)
        status_url = f'{rest_url}/GetJobStatus?jobId={job_id}'
        status_resp = requests.get(status_url)
        if status_resp is not None \
            and "jobStatus" in status_resp \
            and status_resp["jobStatus"] == "paused":
            return True
    return False


def _create_email_for_pause_resume_job(job_id, node_names, job_link, job_owner_email, dri_email):
    message = MIMEMultipart()
    message['Subject'] = f'Repair Manager Alert [{job_id} paused/resumed]'
    message['To'] = job_owner_email
    message['CC'] = dri_email
    body = f'''<p>As previously notified, the following node(s) require reboot due to uncorrectable ECC error:</p>
    <table border="1">'''
    for node in node_names:
        body += f'''<tr><td>{node}</td></tr>'''
    body += f'''</table><p>
    <p> Job <a href="{job_link}">{job_id}</a> has been paused/resumed so node(s) can be repaired.</p>'''
    message.attach(MIMEText(body, 'html'))
    return message


def _create_email_for_issue_with_pause_resume_job(unsuccessful_pause_resume_jobs, dri_email):
    message = MIMEMultipart()
    message['Subject'] = 'Repair Manager Alert [Failed to Pause/Resume Job(s)]'
    message['To'] = dri_email
    body = f'''<p>Repair manager failed to pause/resume the following job(s):</p>
     <table border="1"><tr><th>Job Id</th><th>Job Owner</th><th>Node(s)</th></tr>'''
    for job_id, job_info in unsuccessful_pause_resume_jobs.items():
        body += f'''<tr><td><a href="{job_info['job_link']}">{job_id}</a></td>
            <td>{job_info['user_name']}</td>
            <td>{', '.join(job_info['node_names'])}</td></tr>'''
    body += '</table><p> Please investigate so node(s) can be repaired.</p>'
    message.attach(MIMEText(body, 'html'))
    return message


class ECCRebootNodeRule(Rule):

    def __init__(self, alert, config):
        self.rule = 'ecc_rule'
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
                if self.rule in self.alert.rule_cache:
                    remove_from_cache = []
                    for node in self.alert.rule_cache[self.rule]:
                        instance = self.alert.rule_cache[self.rule][node]["instance"]
                        time_found = self.alert.rule_cache[self.rule][node]["time_found"]
                        last_reboot_time = reboot_times[instance]
                        if last_reboot_time > time_found:
                            remove_from_cache.append(node)

                    for node in remove_from_cache:
                        self.alert.remove_from_rule_cache(self.rule, node)
        except:
            logging.exception(f'Error retrieving data from {reboot_url}')


        # if configured time has elapsed since first detection, take action on node
        if self.rule in self.alert.rule_cache:
            for node in self.alert.rule_cache[self.rule]:
                time_found = self.alert.rule_cache[self.rule][node]["time_found"]
                delta = timedelta(days=self.ecc_config["days_until_node_reboot"])
                now = datetime.utcnow()
                if now - time_found > delta:
                    self.nodes_ready_for_action.append(node)

        return len(self.nodes_ready_for_action) > 0


    def take_action(self):
        pods = k8s_util.list_namespaced_pod("default")
        job_params = {
            "pods": pods,
            "nodes": self.nodes_ready_for_action,
            "domain_name": self.config["domain_name"],
            "cluster_name": self.config["cluster_name"]
        }
        job_info = _get_job_info_from_nodes(**job_params)

        unsuccessful_pause_resume_jobs = {}

        for job_id in job_info:
            dri_email = self.ecc_config["dri_email"]
            job_owner = job_info[job_id]['user_name']
            job_owner_email = f"{job_owner}@{self.config['job_owner_email_domain']}"
            node_names = job_info[job_id]["node_names"]
            job_link = job_info[job_id]['job_link']

            # attempt to pause/resume job
            pause_resume_params = {
                "rest_url": self.ecc_config["rest_url"],
                "job_id": job_id,
                "job_owner_email": job_owner_email,
                "attempts": 10,
                "wait_time": self.ecc_config["time_sleep_after_pausing"]            }
            success = _pause_resume_job(**pause_resume_params)

            if success:
                if self.ecc_config["alert_job_owners"]:
                    message = _create_email_for_pause_resume_job(job_id, node_names, job_link, job_owner_email, dri_email)
                    self.alert.send_alert(message)
            else:
                logging.warning(f"Could not pause/resume the following job: {job_id}")
                unsuccessful_pause_resume_jobs[job_id] = job_info
            
            if len(unsuccessful_pause_resume_jobs) > 0:
                message = _create_email_for_issue_with_pause_resume_job(unsuccessful_pause_resume_jobs, dri_email)
                self.alert.send_alert(message)

        # TODO: reboot node and remove from cache
