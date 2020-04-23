import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import json
import logging
import yaml
import requests
import time
from actions.migrate_job_action import MigrateJobAction
from actions.send_alert_action import SendAlertAction
from actions.reboot_node_action import RebootNodeAction
from datetime import datetime, timedelta, timezone
from rules_abc import Rule
from utils import prometheus_util, k8s_util
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

activity_log = logging.getLogger('activity')

def _extract_node_boot_time_info(response):
    node_boot_times = {}

    if response is not None and "data" in response:
        if "result" in response["data"]:
            for m in response["data"]["result"]:
                instance = m["metric"]["instance"].split(":")[0]
                boot_datetime = datetime.utcfromtimestamp(float(m["value"][1]))
                node_boot_times[instance] = boot_datetime
    
    return node_boot_times


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


class EccRebootNodeRule(Rule):

    def __init__(self, alert, config):
        self.rule = 'ecc_rule'
        self.alert = alert
        self.config = config
        self.ecc_config = self.load_ecc_config()
        self.etcd_config = self.load_etcd_config()
        self.all_jobs_indexed_by_node = {}
        self.nodes_ready_for_action = set()
        self.jobs_ready_for_migration = {}

    def load_ecc_config(self):
        with open('/etc/RepairManager/config/ecc-config.yaml', 'r') as file:
            return yaml.safe_load(file)

    def load_etcd_config(self):
        with open('/etc/RepairManager/config/etcd.conf.yaml', 'r') as file:
            return yaml.safe_load(file)

    def check_if_nodes_have_rebooted(self):
        # if node has been rebooted since ecc error initially detected,
        # remove from rule_cache and mark as resolved
        url = f"http://{self.config['prometheus']['ip']}:{self.config['prometheus']['port']}"
        query = self.config['prometheus']['node_boot_time_query']
        reboot_times_url = prometheus_util.format_url_query(url, query)

        try:
            response = requests.get(reboot_times_url, timeout=10)
            if response:
                reboot_data = response.json()
                reboot_times = _extract_node_boot_time_info(reboot_data)
            bad_nodes = self.alert.get_rule_cache_keys(self.rule)
            for node in bad_nodes:
                instance = self.alert.get_rule_cache(self.rule, node)["instance"]
                time_found_string = self.alert.get_rule_cache(self.rule, node)["time_found"]
                time_found_datetime = datetime.strptime(time_found_string, self.config['date_time_format'])
                last_reboot_time = reboot_times[instance]
                if last_reboot_time > time_found_datetime:
                    self.alert.remove_from_rule_cache(self.rule, node)
                    activity_log.info({"action":"marked as resolved from incorrectable ecc error","node":node})
        except:
            logging.exception(f'Error checking if nodes have rebooted')

    def check_for_nodes_with_no_jobs(self):
        # if no jobs are running on node, take action on node
        bad_nodes = self.alert.get_rule_cache_keys(self.rule)
        self.all_jobs_indexed_by_node = k8s_util.get_job_info_indexed_by_node(
           nodes=bad_nodes,
           portal_url=self.config['portal_url'],
           cluster_name=self.config['cluster_name'])
        for node in bad_nodes:
            node_has_no_jobs = node not in self.all_jobs_indexed_by_node
            node_reboot_pending = 'reboot_requested' in self.alert.get_rule_cache(self.rule, node)
            if node_has_no_jobs and not node_reboot_pending:
                logging.debug(f'node {node} has no running jobs')
                self.nodes_ready_for_action.add(node)

    def check_if_nodes_are_due_for_reboot(self):
        # if configured time has elapsed since initial detection, take action on node
        bad_nodes = self.alert.get_rule_cache_keys(self.rule)
        for node in bad_nodes:
            time_found_string = self.alert.rule_cache[self.rule][node]["time_found"]
            time_found_datetime = datetime.strptime(time_found_string, self.config['date_time_format'])
            delta = timedelta(days=self.ecc_config.get("days_until_node_reboot", 5))
            now = datetime.utcnow()
            node_reboot_pending = 'reboot_requested' in self.alert.get_rule_cache(self.rule, node)
            if now - time_found_datetime > delta and not node_reboot_pending:
                logging.debug(f'Configured time has passed for node {node}')
                self.nodes_ready_for_action.add(node)
                self.determine_jobs_to_be_migrated(node)

    def determine_jobs_to_be_migrated(self, node):
        if node in self.all_jobs_indexed_by_node:
            jobs_on_node = self.all_jobs_indexed_by_node[node]
            for job in jobs_on_node:
                job_id = job["job_id"]
                if job_id not in self.jobs_ready_for_migration:
                    self.jobs_ready_for_migration[job_id] = {
                        "user_name": job["user_name"],
                        "vc_name": job["vc_name"],
                        "node_names": [node],
                        "job_link": job["job_link"]
                    }
                else:
                    self.jobs_ready_for_migration[job_id]["node_names"].append(node)

    def migrate_jobs_and_alert_job_owners(self):
        alert_action = SendAlertAction(self.alert)
        max_attempts = self.ecc_config.get("attempts_for_pause_resume_jobs", 5)
        wait_time = self.ecc_config.get("time_sleep_after_pausing", 30)
        dry_run = not self.ecc_config["enable_reboot"]

        for job_id in self.jobs_ready_for_migration:
            job = self.jobs_ready_for_migration[job_id]
            job_owner = job['user_name']
            job_owner_email = f"{job_owner}@{self.config['job_owner_email_domain']}"
            node_names = job["node_names"]
            job_link = job['job_link']
            rest_url = self.config["rest_url"]

            # migrate all jobs
            migrate_job = MigrateJobAction(rest_url, max_attempts)
            success = migrate_job.execute(
                job_id=job_id,
                job_owner_email=job_owner_email,
                wait_time=wait_time, 
                dry_run=dry_run)

            # alert job owners
            if success:
                message = _create_email_for_pause_resume_job(job_id, node_names, job_link, job_owner_email)
                alert_dry_run = dry_run or not self.ecc_config['enable_alert_job_owners']
                alert_action.execute(
                    message=message,
                    dry_run=alert_dry_run,
                    additional_log={"job_id":job_id,"job_owner":job_owner})
            else:
                logging.warning(f"Could not pause/resume the following job: {job_id}")
                # skip rebooting the node this iteration
                # and try again later
                for node in node_names:
                    self.nodes_ready_for_action.remove(node)

    def reboot_bad_nodes(self):
        reboot_action = RebootNodeAction()
        for node in self.nodes_ready_for_action:
           success = reboot_action.execute(node, self.etcd_config)
           if success:
                # update reboot status so action is not taken again
                cache_value = self.alert.get_rule_cache(self.rule, node)
                cache_value['reboot_requested'] =  datetime.utcnow().strftime(self.config['date_time_format'])
                self.alert.update_rule_cache(self.rule, node, cache_value)

    def check_status(self):
        self.check_if_nodes_have_rebooted()
        self.check_for_nodes_with_no_jobs()
        self.check_if_nodes_are_due_for_reboot()
        return len(self.nodes_ready_for_action) > 0


    def take_action(self):
        self.migrate_jobs_and_alert_job_owners()
        self.reboot_bad_nodes()
