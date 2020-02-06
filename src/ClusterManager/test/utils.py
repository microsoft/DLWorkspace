#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import urllib.parse
import json
import logging
import datetime
import time
import os
import yaml
import base64
import functools

import requests

from kubernetes import client as k8s_client
from kubernetes.client.rest import ApiException
from kubernetes.client import Configuration, ApiClient
from kubernetes.stream import stream
from kubernetes.stream.ws_client import ERROR_CHANNEL, STDERR_CHANNEL, STDOUT_CHANNEL

logger = logging.getLogger(__file__)


def case(fn):
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        start = datetime.datetime.now()
        full_name = fn.__module__ + "." + fn.__name__
        try:
            logger.info("%s ...", full_name)
            return fn(*args, **kwargs)
        except Exception:
            logger.exception("executing %s failed", full_name)
            # let other test case continue
        finally:
            logger.info("spent %s in executing test case %s",
                        datetime.datetime.now() - start, full_name)

    wrapped.is_case = True
    return wrapped


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
    return _op_jobs(rest_url, email, job_ids, "Pause")


def resume_jobs(rest_url, email, job_ids):
    return _op_jobs(rest_url, email, job_ids, "Resume")


def approve_jobs(rest_url, email, job_ids):
    return _op_jobs(rest_url, email, job_ids, "Approve")


def get_job_list(rest_url, email, vc_name, job_owner, num=10):
    args = urllib.parse.urlencode({
        "userName": email,
        "vcName": vc_name,
        "jobOwner": job_owner,
        "num": num,
    })
    url = urllib.parse.urljoin(rest_url, "/ListJobsV2") + "?" + args
    resp = requests.get(url)
    return resp.json()


class run_job(object):
    def __init__(self,
                 rest_url,
                 job_type,
                 email,
                 uid,
                 vc,
                 image="indexserveregistry.azurecr.io/deepscale:1.0.post0",
                 cmd="sleep 120"):
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


def get_endpoints(rest_url, email, jid):
    args = urllib.parse.urlencode({
        "userName": email,
        "jobId": jid,
    })
    url = urllib.parse.urljoin(rest_url, "/endpoints") + "?" + args
    resp = requests.get(url)
    return resp.json()


def create_endpoint(rest_url, email, jid, point_names):
    args = urllib.parse.urlencode({
        "userName": email,
    })
    url = urllib.parse.urljoin(rest_url, "/endpoints") + "?" + args
    payload = {"jobId": jid, "endpoints": point_names}
    resp = requests.post(url, json=payload)
    return resp.json()


def wait_endpoint_ready(rest_url, email, jid, endpoint_id, timeout=30):
    start = datetime.datetime.now()
    delta = datetime.timedelta(seconds=timeout)

    while True:
        points = get_endpoints(rest_url, email, jid)
        for p in points:
            if p["id"] != endpoint_id or p["status"] != "running":
                continue
            logger.info("spent %s in waiting endpoint %s become running",
                        datetime.datetime.now() - start, endpoint_id)
            return p
        logger.debug("waiting endpoint %s become running", endpoint_id)
        if datetime.datetime.now() - start < delta:
            time.sleep(1)
        else:
            raise RuntimeError(
                "endpoint %s did not become running for more than %d seconds" %
                (endpoint_id, timeout))


def find_infra_node_name(machines):
    for hostname, val in machines.items():
        if val.get("role") == "infrastructure":
            return hostname


def build_k8s_config(config_path):
    cluster_path = os.path.join(config_path, "cluster.yaml")

    with open(cluster_path) as f:
        cluster_config = yaml.load(f, Loader=yaml.FullLoader)

    config = Configuration()

    infra_host = find_infra_node_name(cluster_config["machines"])
    config.host = "https://%s.%s:1443" % (infra_host,
                                          cluster_config["network"]["domain"])

    basic_auth = cluster_config["basic_auth"]
    config.username = basic_auth.split(",")[1]
    config.password = basic_auth.split(",")[0]
    bearer = "%s:%s" % (config.username, config.password)
    encoded = base64.b64encode(bearer.encode("utf-8")).decode("utf-8")
    config.api_key["authorization"] = "Basic " + encoded

    config.ssl_ca_cert = os.path.join(config_path, "ssl/apiserver/ca.pem")
    return config


def kube_get_pods(config_path, namespace, label_selector):
    k8s_config = build_k8s_config(config_path)
    api_client = ApiClient(configuration=k8s_config)

    k8s_core_api = k8s_client.CoreV1Api(api_client)

    api_response = k8s_core_api.list_namespaced_pod(
        namespace=namespace,
        pretty="pretty_example",
        label_selector=label_selector,
    )
    logger.debug("%s got pods from namespace %s: api_response", label_selector,
                 namespace, api_response)
    return api_response.items


def kube_pod_exec(config_path,
                  namespace,
                  pod_name,
                  container_name,
                  exec_command,
                  timeout=60):
    k8s_config = build_k8s_config(config_path)
    api_client = ApiClient(configuration=k8s_config)

    k8s_core_api = k8s_client.CoreV1Api(api_client)
    try:
        stream_client = stream(
            k8s_core_api.connect_get_namespaced_pod_exec,
            namespace="default",
            name=pod_name,
            container=container_name,
            command=exec_command,
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False,
            _preload_content=False,
        )
        stream_client.run_forever(timeout=timeout)

        err = yaml.full_load(stream_client.read_channel(ERROR_CHANNEL))
        if err is None:
            return [-1, "Timeout"]

        if err["status"] == "Success":
            status_code = 0
        else:
            logger.debug("exec on pod %s failed. cmd: %s, err: %s.", pod_name,
                         exec_command, err)
            status_code = int(err["details"]["causes"][0]["message"])
        output = stream_client.read_all()
        logger.debug("exec on pod %s, status: %s, cmd: %s, output: %s",
                     pod_name, status_code, exec_command, output)
        return [status_code, output]
    except ApiException as err:
        logger.exception("exec on pod %s error. cmd: %s", pod_name,
                         exec_command)
        return [-1, str(err)]
