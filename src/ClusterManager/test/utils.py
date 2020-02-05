#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import urllib.parse
import json
import logging
import datetime
import time

import requests

logger = logging.getLogger(__file__)


def post_regular_job(rest_url, email, uid, vc, image, cmd):
    args = {
        "userName": email,
        "userId": uid,
        "jobType": "training",
        "gpuType": "P40",
        "vcName": vc,
        "containerUserId": 0,
        "jobName": "DeepScale1.0-Regular",
        "jobtrainingtype": "RegularJob",
        "preemptionAllowed": "False",
        "image": image,
        "cmd": cmd,
        "workPath": "./",
        "enableworkpath": True,
        "dataPath": "./",
        "enabledatapath": True,
        "jobPath": "",
        "enablejobpath": True,
        "env": [],
        "hostNetwork": False,
        "isPrivileged": False,
        "resourcegpu": 0,
        "cpulimit": 1,
    }
    url = urllib.parse.urljoin(rest_url, "/PostJob")
    resp = requests.post(url,
                         data=json.dumps(args))  # do not handle exception here
    jid = resp.json()["jobId"]
    logger.info("regular job %s created", jid)
    return jid


def post_distributed_job(rest_url, email, uid, vc, image, cmd):
    args = {
        "userName": email,
        "userId": uid,
        "jobType": "training",
        "gpuType": "P40",
        "vcName": vc,
        "containerUserId": 0,
        "jobName": "DeepScale1.0-Distributed",
        "jobtrainingtype": "PSDistJob",
        "preemptionAllowed": "False",
        "image": image,
        "cmd": cmd,
        "workPath": "./",
        "enableworkpath": True,
        "dataPath": "./",
        "enabledatapath": True,
        "jobPath": "",
        "enablejobpath": False,
        "env": [],
        "hostNetwork": True,
        "isPrivileged": True,
        "numps": 1,
        "resourcegpu": 0,
        "numpsworker": 1
    }
    url = urllib.parse.urljoin(rest_url, "/PostJob")
    resp = requests.post(url,
                         data=json.dumps(args))  # do not handle exception here
    jid = resp.json()["jobId"]
    logger.info("distributed job %s created", jid)
    return jid


def post_data_job(rest_url, email, uid, vc, image, cmd):
    args = {
        "userName": email,
        "userId": uid,
        "jobType": "training",
        "vcName": vc,
        "containerUserId": 0,
        "jobName": "DLTS-Data-Job",
        "jobtrainingtype": "RegularJob",
        "preemptionAllowed": "False",
        "image": image,
        "cmd": cmd,
        "workPath": "./",
        "enableworkpath": True,
        "dataPath": "./",
        "enabledatapath": True,
        "jobPath": "",
        "enablejobpath": True,
        "env": [],
        "hostNetwork": False,
        "isPrivileged": False,
        "resourcegpu": 0,
        "cpulimit": 1
    }
    url = urllib.parse.urljoin(rest_url, "/PostJob")
    resp = requests.post(url,
                         data=json.dumps(args))  # do not handle exception here
    jid = resp.json()["jobId"]
    logger.info("data job %s created", jid)
    return jid


def get_job_status(rest_url, job_id):
    args = urllib.parse.urlencode({
        "jobId": job_id,
    })
    url = urllib.parse.urljoin(rest_url, "/GetJobStatus") + "?" + args
    resp = requests.get(url)
    return resp.json()


def get_job_detail(rest_url, email, job_id):
    args = urllib.parse.urlencode({
        "userName": email,
        "jobId": job_id,
    })
    url = urllib.parse.urljoin(rest_url, "/GetJobDetail") + "?" + args
    resp = requests.get(url)
    return resp.json()


def _op_job(rest_url, email, job_id, op):
    args = urllib.parse.urlencode({
        "userName": email,
        "jobId": job_id,
    })
    url = urllib.parse.urljoin(rest_url, "/%sJob" % op) + "?" + args
    resp = requests.get(url)
    return resp.json()


def kill_job(rest_url, email, job_id):
    return _op_job(rest_url, email, job_id, "Kill")


def pause_job(rest_url, email, job_id):
    return _op_job(rest_url, email, job_id, "Pause")


def resume_job(rest_url, email, job_id):
    return _op_job(rest_url, email, job_id, "Resume")


def approve_job(rest_url, email, job_id):
    return _op_job(rest_url, email, job_id, "Approve")


def _op_jobs(rest_url, email, job_ids, op):
    if isinstance(job_ids, list):
        job_ids = ",".join(job_ids)

    args = urllib.parse.urlencode({
        "userName": email,
        "jobIds": job_ids,
    })
    url = urllib.parse.urljoin(rest_url, "/%sJobs" % op) + "?" + args
    resp = requests.get(url)
    return resp.json()


def kill_jobs(rest_url, email, job_ids):
    return _op_jobs(rest_url, email, job_ids, "Kill")


def pause_jobs(rest_url, email, job_ids):
    return _op_job(rest_url, email, job_ids, "Pause")


def resume_jobs(rest_url, email, job_ids):
    return _op_job(rest_url, email, job_ids, "Resume")


def approve_jobs(rest_url, email, job_ids):
    return _op_job(rest_url, email, job_ids, "Approve")


class run_job(object):
    def __init__(self, rest_url, job_type, email, uid, vc, image, cmd):
        self.rest_url = rest_url
        self.job_type = job_type
        self.email = email
        self.uid = uid
        self.vc = vc
        self.image = image
        self.cmd = cmd
        self.jid = None

    def __enter__(self):
        if self.job_type == "regular":
            self.jid = post_regular_job(self.rest_url, self.email, self.uid,
                                        self.vc, self.image, self.cmd)
        elif self.job_type == "distributed":
            self.jid = post_distributed_job(self.rest_url, self.email,
                                            self.uid, self.vc, self.image,
                                            self.cmd)
        elif self.job_type == "data":
            self.jid = post_data_job(self.rest_url, self.email, self.uid,
                                     self.vc, self.image, self.cmd)
        else:
            logger.error("unknown job_type %s, wrong test case", self.job_type)
        return self

    def __exit__(self, type, value, traceback):
        try:
            resp = kill_job(self.rest_url, self.email, self.jid)
            logger.info("killed %s job %s", self.job_type, self.jid)
        except Exception:
            logger.exception("failed to kill %s job %s", self.job_type,
                             self.jid)


def block_until_state(rest_url, jid, not_in, states, timeout=300):
    start = datetime.datetime.now()
    delta = datetime.timedelta(seconds=timeout)

    while True:
        status = get_job_status(rest_url, jid)["jobStatus"]

        cond = status in states if not_in else status not in states

        if cond:
            logger.debug("waiting status in %s", status)
            if datetime.datetime.now() - start < delta:
                time.sleep(1)
            else:
                raise RuntimeError("Job stays in %s for more than %d seconds" %
                                   (status, timeout))
        else:
            logger.info("spent %s in waiting job become %s",
                        datetime.datetime.now() - start, status)
            return status


def block_until_state_not_in(rest_url, jid, states, timeout=300):
    return block_until_state(rest_url, jid, True, states, timeout=timeout)


def block_until_state_in(rest_url, jid, states, timeout=300):
    return block_until_state(rest_url, jid, False, states, timeout=timeout)


def get_job_log(rest_url, email, jid):
    args = urllib.parse.urlencode({
        "userName": email,
        "jobId": jid,
    })
    url = urllib.parse.urljoin(rest_url, "/GetJobLog") + "?" + args
    resp = requests.get(url)
    return resp.json()
