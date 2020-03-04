import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
from action_abc import Action
from utils import k8s_util
import time
import requests

class ResumeJobAction(Action):

    def __init__(self, rest_url, max_attempts=5):
        self.action_logger = logging.getLogger('activity')
        self.rest_url = rest_url
        self.max_attempts = max_attempts

    def execute(self, job_id, job_owner_email, dry_run=False):
        resume_url = f'{self.rest_url}/ResumeJob?userName={job_owner_email}&jobId={job_id}'
        success = False
        attempts = 0

        if dry_run:
            success = True
        else:
            while not success and attempts < self.max_attempts:
                try:
                    resume_resp = requests.get(resume_url).json()
                    if resume_resp is not None \
                        and "result" in resume_resp \
                        and "success" in resume_resp["result"].lower():
                        success = True
                    else:
                        time.sleep(5)
                except:
                    logging.exception(f'Error retrieving data from {resume_url}')
                attempts+=1

        self.action_logger.info({
            "action": "resume job",
            "job_id": job_id,
            "job_owner_email": job_owner_email,
            "resume_url": resume_url,
            "dry_run": dry_run,
            "success": success
            })
        return success
