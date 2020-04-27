import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
from action_abc import Action
from pause_job_action import PauseJobAction
from resume_job_action import ResumeJobAction
from utils import k8s_util
import time
import requests

class MigrateJobAction(Action):

    def __init__(self, rest_url, max_attempts=5):
        self.action_logger = logging.getLogger('activity')
        self.rest_url = rest_url
        self.max_attempts = max_attempts


    def wait_for_job_to_pause(self, job_id, wait_time=30, dry_run=False):
        pause_complete = False
        attempts = 0

        if dry_run:
            pause_complete = True
        else:
            while not pause_complete and attempts < self.max_attempts:
                try:
                    time.sleep(wait_time)
                    status_url = f'{self.rest_url}/GetJobStatus?jobId={job_id}'
                    status_resp = requests.get(status_url).json()
                    if status_resp is not None \
                        and "jobStatus" in status_resp \
                        and status_resp["jobStatus"] == "paused":
                        pause_complete = True
                except:
                    logging.exception(f'Error retrieving data from {status_url}')
                attempts+=1
        return pause_complete


    def execute(self, job_id, job_owner_email, wait_time=30, dry_run=False):
        migrate_success = False

        pause_job = PauseJobAction(self.rest_url, self.max_attempts)
        pause_success = pause_job.execute(job_id, job_owner_email, dry_run)
        if pause_success:
            pause_complete = self.wait_for_job_to_pause(job_id, wait_time, dry_run)
            if pause_complete:
                resume_job = ResumeJobAction(self.rest_url, self.max_attempts)
                migrate_success = resume_job.execute(job_id, job_owner_email, dry_run)

        self.action_logger.info({
            "action": "migrate job",
            "job_id": job_id,
            "job_owner_email": job_owner_email,
            "dry_run": dry_run,
            "success": migrate_success
            })
        return migrate_success
