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
        "resourcegpu": 1,
        "cpulimit": 1,
    }
    url = urllib.parse.urljoin(rest_url, "/PostJob")
    resp = requests.post(url, data=json.dumps(args)) # do not handle exception here
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
        "resourcegpu": 4,
        "numpsworker": 1
    }
    url = urllib.parse.urljoin(rest_url, "/PostJob")
    resp = requests.post(url, data=json.dumps(args)) # do not handle exception here
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
    resp = requests.post(url, data=json.dumps(args)) # do not handle exception here
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


def kill_job(rest_url, email, job_id):
    args = urllib.parse.urlencode({
        "userName": email,
        "jobId": job_id,
        })
    url = urllib.parse.urljoin(rest_url, "/KillJob") + "?" + args
    resp = requests.get(url)
    return resp.json()


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
            self.jid = post_regular_job(self.rest_url, self.email, self.uid, self.vc, self.image, self.cmd)
        elif self.job_type == "distributed":
            self.jid = post_distributed_job(self.rest_url, self.email, self.uid, self.vc, self.image, self.cmd)
        elif self.job_type == "data":
            self.jid = post_data_job(self.rest_url, self.email, self.uid, self.vc, self.image, self.cmd)
        return self

    def __exit__(self, type, value, traceback):
        try:
            resp = kill_job(self.rest_url, self.email, self.jid)
            logger.info("killed %s job %s", self.job_type, self.jid)
        except Exception:
            logger.exception("failed to kill %s job %s", self.job_type, self.jid)


def block_until_running(rest_url, jid, timeout=300):
    start = datetime.datetime.now()
    delta = datetime.timedelta(seconds=timeout)
    waiting_state = {"unapproved", "queued", "scheduling"}

    while True:
        status = get_job_status(rest_url, jid)["jobStatus"]

        if status in waiting_state:
            logger.debug("waiting status in %s", status)
            if datetime.datetime.now() - start < delta:
                time.sleep(1)
            else:
                raise RuntimeError("Job stays in %s for more than %d seconds" % (status, timeout))
        elif status == "running":
            logger.info("spent %s in waiting job running", datetime.datetime.now() - start)
            return status
        else:
            raise RuntimeError("Got unexpected job status %s for job %s" % (status, jid))


def block_until_finished(rest_url, jid, timeout=300):
    start = datetime.datetime.now()
    delta = datetime.timedelta(seconds=timeout)
    final_state = {"finished", "killed", "failed", "error"}

    while True:
        status = get_job_status(rest_url, jid)["jobStatus"]

        if status == "running":
            logger.debug("job is still running")
            if datetime.datetime.now() - start < delta:
                time.sleep(1)
            else:
                raise RuntimeError("Job is running for more than %d seconds" % timeout)
        elif status in final_state:
            logger.info("spent %s in running, finishes with state %s", datetime.datetime.now() - start, status)
            return status
        else:
            raise RuntimeError("Got unexpected job status %s for job %s" % (status, jid))


def get_job_log(rest_url, email, jid):
    args = urllib.parse.urlencode({
        "userName": email,
        "jobId": jid,
        })
    url = urllib.parse.urljoin(rest_url, "/GetJobLog") + "?" + args
    resp = requests.get(url)
    return resp.json()
