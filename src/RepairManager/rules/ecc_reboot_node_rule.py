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

activity_log = logging.getLogger('activity')

DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

def _extract_node_boot_time_info(response):
    node_boot_times = {}

    if response is not None and "data" in response:
        if "result" in response["data"]:
            for m in response["data"]["result"]:
                instance = m["metric"]["instance"].split(":")[0]
                boot_datetime = datetime.utcfromtimestamp(float(m["value"][1]))
                node_boot_times[instance] = boot_datetime
    
    return node_boot_times

def _pause_resume_job(rest_url, job_id, job_owner_email, attempts, wait_time, dry_run):
    try:
        if dry_run:
            return True
        else:
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
        pause_resp = requests.get(pause_url).json()
        if pause_resp is not None \
            and "result" in pause_resp \
            and "success" in pause_resp["result"].lower():
            return True
        time.sleep(5)
    return False


def _resume_job(rest_url, job_id, job_owner_email, attempts):
    for i in range(attempts):
        resume_url = f'{rest_url}/ResumeJob?userName={job_owner_email}&jobId={job_id}'
        resume_resp = requests.get(resume_url).json()
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
        status_resp = requests.get(status_url).json()
        if status_resp is not None \
            and "jobStatus" in status_resp \
            and status_resp["jobStatus"] == "paused":
            return True
    return False


def _create_email_for_pause_resume_job(job_id, node_names, job_link, job_owner_email):
    message = MIMEMultipart()
    message['Subject'] = f'Repair Manager Alert [{job_id} paused/resumed]'
    message['To'] = job_owner_email
    body = f'''<p>As previously notified, the following node(s) require reboot due to uncorrectable ECC error:</p>
    <table border="1">'''
    for node in node_names:
        body += f'''<tr><td>{node}</td></tr>'''
    body += f'''</table><p>
    <p> Job <a href="{job_link}">{job_id}</a> has been paused/resumed so node(s) can be repaired.</p>'''
    message.attach(MIMEText(body, 'html'))
    return message


def _create_email_for_issue_with_pause_resume_job(unsuccessful_pause_resume_jobs):
    message = MIMEMultipart()
    message['Subject'] = 'Repair Manager Alert [Failed to Pause/Resume Job(s)]'
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
        with open('/etc/RepairManager/config/ecc-config.yaml', 'r') as file:
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
                        time_found_string = self.alert.rule_cache[self.rule][node]["time_found"]
                        time_found_datetime = datetime.strptime(time_found_string, DATE_FORMAT)
                        last_reboot_time = reboot_times[instance]
                        if last_reboot_time > time_found_datetime:
                            remove_from_cache.append(node)
                            activity_log.info({"action":"node marked as resolved","node":node})

                    for node in remove_from_cache:
                        self.alert.remove_from_rule_cache(self.rule, node)
        except:
            logging.exception(f'Error retrieving data from {reboot_url}')


        # if configured time has elapsed since first detection, take action on node (if not done already)
        if self.rule in self.alert.rule_cache:
            for node in self.alert.rule_cache[self.rule]:
                cache_value = self.alert.get_rule_cache(self.rule, node)
                if 'paused/resumed' not in cache_value:
                    time_found_string = self.alert.rule_cache[self.rule][node]["time_found"]
                    time_found_datetime = datetime.strptime(time_found_string, DATE_FORMAT)
                    delta = timedelta(days=self.ecc_config.get("days_until_node_reboot", 5))
                    now = datetime.utcnow()
                    if now - time_found_datetime > delta:
                        logging.info(f'Configured time has passed for node {node}')
                        self.nodes_ready_for_action.append(node)

        logging.debug(f"rule_cache: {json.dumps(self.alert.rule_cache, default=str)}")
        return len(self.nodes_ready_for_action) > 0


    def take_action(self):
        pods = k8s_util.list_namespaced_pod("default")
        job_params = {
            "pods": pods,
            "nodes": self.nodes_ready_for_action,
            "portal_url": self.config["portal_url"],
            "cluster_name": self.config["cluster_name"]
        }
        job_info = k8s_util._get_job_info_from_nodes(**job_params)

        unsuccessful_pause_resume_jobs = {}

        for job_id in job_info:
            job_owner = job_info[job_id]['user_name']
            job_owner_email = f"{job_owner}@{self.config['job_owner_email_domain']}"
            node_names = job_info[job_id]["node_names"]
            job_link = job_info[job_id]['job_link']
            reboot_dry_run = self.ecc_config.get("reboot_dry_run", True)

            # attempt to pause/resume job
            pause_resume_params = {
                "rest_url": self.ecc_config["rest_url"],
                "job_id": job_id,
                "job_owner_email": job_owner_email,
                "attempts": self.ecc_config.get("attempts_for_pause_resume_jobs", 5),
                "wait_time": self.ecc_config.get("time_sleep_after_pausing", 30),
                "dry_run": reboot_dry_run
            }
            success = _pause_resume_job(**pause_resume_params)
            activity_log.info({"action":"pause/resume job","job_id":job_id,"job_owner":job_owner,"success":success,"dry_run":reboot_dry_run})

            if success:
                if self.ecc_config["alert_job_owners"] and not reboot_dry_run:
                    message = _create_email_for_pause_resume_job(job_id, node_names, job_link, job_owner_email)
                    self.alert.send_alert(message)
                    activity_log.info({"action":"job owner alert - pause/resume","job_id":job_id,"job_owner":job_owner})
            else:
                logging.warning(f"Could not pause/resume the following job: {job_id}")
                unsuccessful_pause_resume_jobs[job_id] = job_info[job_id]
            
            if len(unsuccessful_pause_resume_jobs) > 0:
                message = _create_email_for_issue_with_pause_resume_job(unsuccessful_pause_resume_jobs)
                self.alert.send_alert(message)
                activity_log.info(activity_log.info({"action":"dri alert - failed to pause/resume","job_id":job_id,"job_owner":job_owner}))

        # TODO: reboot node and remove from cache

        # update pause/resume status so action is not taken again
        for node in self.nodes_ready_for_action:
            cache_value = self.alert.get_rule_cache(self.rule, node)
            cache_value['paused/resumed'] = True
            self.alert.update_rule_cache(self.rule, node, cache_value)
