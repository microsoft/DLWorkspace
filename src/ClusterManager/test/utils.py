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
import inspect
import requests

STATUS_YAML = "status.yaml"
from kubernetes import client as k8s_client
from kubernetes.client.rest import ApiException
from kubernetes.client import Configuration, ApiClient
from kubernetes.stream import stream
from kubernetes.stream.ws_client import ERROR_CHANNEL, STDERR_CHANNEL, STDOUT_CHANNEL

logger = logging.getLogger(__file__)


def walk_json_safe(obj, *fields):
    """ for example a=[{"a": {"b": 2}}]
    walk_json_safe(a, 0, "a", "b") will get 2
    walk_json_safe(a, 0, "not_exist") will get None
    """
    try:
        for f in fields:
            obj = obj[f]
        return obj
    except:
        return None


def case(unstable=False):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapped(*args, **kwargs):
            start = datetime.datetime.now()
            full_name = fn.__module__ + "." + fn.__name__
            max_retry = 3 if unstable else 1

            for times in range(max_retry):
                try:
                    logger.info("%s ...(%s times)", full_name, times)
                    fn(*args, **kwargs)
                    return False
                except Exception:
                    logger.exception("executing %s failed", full_name)
                    continue
                finally:
                    logger.info("spent %s in executing test case %s",
                                datetime.datetime.now() - start, full_name)
            return True

        wrapped.is_case = True
        return wrapped

    return decorator


def load_azure_blob_config(config_path, mount_path):
    config_path = os.path.join(config_path, "config.yaml")

    with open(config_path) as f:
        config = yaml.full_load(f)

    blob_config = walk_json_safe(config, "integration-test", "azure-blob")

    if walk_json_safe(blob_config, "account") is None or \
            walk_json_safe(blob_config, "key") is None or \
            walk_json_safe(blob_config, "container") is None:
        raise RuntimeError("no azure blob configured for integration test")

    return {
        "blobfuse": [{
            "accountName": walk_json_safe(blob_config, "account"),
            "accountKey": walk_json_safe(blob_config, "key"),
            "containerName": walk_json_safe(blob_config, "container"),
            "mountPath": mount_path,
        }]
    }


def gen_default_job_description(
    job_type,
    email,
    uid,
    vc,
    preemptable=False,
    image="indexserveregistry.azurecr.io/deepscale:1.0.post0",
    cmd="sleep 120",
    resourcegpu=0):

    caller_frame = inspect.stack()[1]
    module_name = os.path.basename(caller_frame.filename).split(".")[0]
    case_name = caller_frame.function

    args = {
        "userName": email,
        "userId": uid,
        "jobType": "training",
        "gpuType": "P40",
        "vcName": vc,
        "containerUserId": 0,
        "jobName": "%s.%s" % (module_name, case_name),
        "preemptionAllowed": preemptable,
        "image": image,
        "cmd": cmd,
        "workPath": "./",
        "enableworkpath": True,
        "dataPath": "./",
        "enabledatapath": True,
        "jobPath": "",
        "enablejobpath": True,
        "env": [],
        "resourcegpu": resourcegpu,
        "memorylimit": "500M",
        "cpulimit": 1,
        "_allow_partial_node": True,
    }

    if job_type in {"regular", "data"}:
        args["jobtrainingtype"] = "RegularJob"
        args["hostNetwork"] = False
        args["isPrivileged"] = False
    elif job_type == "distributed":
        args["jobtrainingtype"] = "PSDistJob"
        args["hostNetwork"] = True
        args["isPrivileged"] = True
        args["numps"] = 1
        args["resourcegpu"] = resourcegpu
        args["numpsworker"] = 1
    elif job_type == "inference":
        args["jobtrainingtype"] = "InferenceJob"
        args["hostNetwork"] = False
        args["isPrivileged"] = False
        args["resourcegpu"] = 1 # num of worker
    else:
        logger.error("unknown job_type %s, wrong test case", job_type)
        raise RuntimeError("unknown job_type %s" % (job_type))

    return args


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


def post_job(rest_url, job_spec):
    url = urllib.parse.urljoin(rest_url, "/PostJob")
    resp = requests.post(url, data=json.dumps(job_spec))
    jid = resp.json()["jobId"]
    logger.info("job %s created", jid)
    return jid


class run_job(object):
    def __init__(self, rest_url, job_spec):
        self.rest_url = rest_url
        self.job_spec = job_spec
        self.jid = None

    def __enter__(self):
        self.jid = post_job(self.rest_url, self.job_spec)
        return self

    def __exit__(self, type, value, traceback):
        email = self.job_spec["userName"]
        try:
            resp = kill_job(self.rest_url, email, self.jid)
            logger.info("killed job %s", self.jid)
        except Exception:
            logger.exception("failed to kill job %s", self.jid)

    def block_until_state_not_in(self, states):
        return block_until_state_not_in(self.rest_url, self.jid, states)


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
    cursor = None
    job_logs = []
    for _ in range(500): # avoid dead loop
        args = {
            "userName": email,
            "jobId": jid,
        }
        if cursor is not None:
            args['cursor'] = cursor
        args = urllib.parse.urlencode(args)
        url = urllib.parse.urljoin(rest_url, "/GetJobLog") + "?" + args
        resp = requests.get(url)
        if resp.status_code == 404:
            break
        resp_json = resp.json()
        log = resp_json["log"]
        cursor = resp_json["cursor"]
        if isinstance(log, dict):
            job_logs.extend(log.values())
        else:
            job_logs.append(log)
        if cursor is None:
            break
    return '\n'.join(job_logs)


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


def wait_endpoint_state(rest_url,
                        email,
                        jid,
                        endpoint_id,
                        state="running",
                        timeout=30):
    start = datetime.datetime.now()
    delta = datetime.timedelta(seconds=timeout)

    while True:
        points = get_endpoints(rest_url, email, jid)
        for p in points:
            if p["id"] != endpoint_id or p["status"] != state:
                continue
            logger.info("spent %s in waiting endpoint %s become %s",
                        datetime.datetime.now() - start, endpoint_id, state)
            return p
        logger.debug("waiting endpoint %s become %s, is %s", endpoint_id, state,
                     p["status"])
        if datetime.datetime.now() - start < delta:
            time.sleep(1)
        else:
            raise RuntimeError(
                "endpoint %s did not become %s for more than %d seconds" %
                (endpoint_id, state, timeout))


def find_infra_node_name(machines):
    for hostname, val in machines.items():
        role_val = val.get("role")
        if type(role_val) == str and role_val == "infrastructure":
            return hostname
        elif type(role_val) == list:
            for role in role_val:
                if role == "infra":
                    return hostname


def build_k8s_config(config_path):
    cluster_path = os.path.join(config_path, "cluster.yaml")
    if not os.path.isfile(cluster_path):
        cluster_path = os.path.join(config_path, STATUS_YAML)

    with open(cluster_path) as f:
        cluster_config = yaml.full_load(f)

    config = Configuration()

    infra_host = find_infra_node_name(cluster_config["machines"])

    if os.path.isfile(cluster_path):
        config.host = "https://%s.%s:1443" % (infra_host,
                                          cluster_config["network"]["domain"])
        basic_auth = cluster_config["basic_auth"]
    else:
        config.host = cluster_config["machines"][infra_host]["fqdns"]
        with open(os.path.join(config_path, "clusterID", "k8s_basic_auth.yml")) as auf:
            basic_auth = yaml.safe_load(auf)["basic_auth"]

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


def kube_delete_pod(config_path, namespace, pod_name):
    k8s_config = build_k8s_config(config_path)
    api_client = ApiClient(configuration=k8s_config)

    k8s_core_api = k8s_client.CoreV1Api(api_client)

    api_response = k8s_core_api.delete_namespaced_pod(
        pod_name,
        namespace,
        pretty="pretty_example",
        grace_period_seconds=0,
    )

    logger.debug("delete %s from namespace %s: api_response %s", pod_name,
                 namespace, api_response)
    return api_response.code


def kube_pod_exec(config_path,
                  namespace,
                  pod_name,
                  container_name,
                  exec_command,
                  timeout=60):
    """ exec_command should be an array, e.g. ["bash", "-c", "echo abc > /tmp/abc"] """
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
