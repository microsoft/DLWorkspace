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
import re
import multiprocessing
import copy

import requests

STATUS_YAML = "status.yaml"
from kubernetes import client as k8s_client
from kubernetes.client.rest import ApiException
from kubernetes.client import Configuration, ApiClient
from kubernetes.stream import stream
from kubernetes.stream.ws_client import ERROR_CHANNEL, STDERR_CHANNEL, STDOUT_CHANNEL

logger = logging.getLogger(__file__)


def walk_json(obj, *fields, default=None):
    """ for example a=[{"a": {"b": 2}}]
    walk_json(a, 0, "a", "b") will get 2
    walk_json(a, 0, "not_exist") will get None
    """
    try:
        for f in fields:
            obj = obj[f]
        return obj
    except:
        return default


def case(unstable=False, dangerous=False):
    """ return False on success, True on failed, None on unfinished """
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
                except KeyboardInterrupt:
                    return None
                except Exception:
                    logger.exception("executing %s failed", full_name)
                    continue
                finally:
                    logger.info("spent %s in executing test case %s",
                                datetime.datetime.now() - start, full_name)
            return True

        wrapped.is_case = True
        wrapped.is_dangerous_case = dangerous
        return wrapped

    return decorator


def run_cases_in_parallel(cases, args, pool_size):
    def wrapper(queue, case, *args, **kwargs):
        result = None
        try:
            result = case(*args, **kwargs)
        finally:
            queue.put(result)

    pool = set()
    queues = [multiprocessing.Queue() for _ in cases]

    try:
        for i, case in enumerate(cases):
            if len(pool) >= pool_size:
                joined = False
                while not joined:
                    for p in pool:
                        p.join(0.1)
                        if not p.is_alive():
                            joined = True
                            pool.remove(p)
                            break

            processor = functools.partial(wrapper, queues[i], case)
            p = multiprocessing.Process(target=processor,
                                        args=(args,),
                                        name="worker-" + str(i))
            p.start()
            pool.add(p)

        for p in pool:
            p.join()
    except KeyboardInterrupt:
        pass

    def getter(queue):
        if queue.empty():
            return None
        return queue.get_nowait()

    return list(map(getter, queues))


def snake_case(s):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', s)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def get_alias(email):
    if not isinstance(email, str):
        return None
    return email.split("@")[0]


def get_config(config_path):
    config_path = os.path.join(config_path, "config.yaml")
    with open(config_path) as f:
        config = yaml.full_load(f)
    return config


def get_launcher(config_path):
    config = get_config(config_path)
    launcher = walk_json(config, "job-manager", "launcher")
    if launcher is None:
        launcher = "python"
    return launcher


def load_azure_blob_config(config_path, mount_path):
    config = get_config(config_path)
    blob_config = walk_json(config, "integration-test", "azure-blob")

    if walk_json(blob_config, "account") is None or \
            walk_json(blob_config, "key") is None or \
            walk_json(blob_config, "container") is None:
        raise RuntimeError("no azure blob configured for integration test")

    return {
        "blobfuse": [{
            "accountName": walk_json(blob_config, "account"),
            "accountKey": walk_json(blob_config, "key"),
            "containerName": walk_json(blob_config, "container"),
            "mountPath": mount_path,
        }]
    }


def load_cluster_nfs_mountpoints(args, job_id):
    config = get_config(args.config)
    cluster_nfs = walk_json(config, "cluster_nfs")

    if walk_json(cluster_nfs, "server") is None or \
            walk_json(cluster_nfs, "path") is None:
        raise RuntimeError("no cluster_nfs configured")

    server = walk_json(cluster_nfs, "server")
    path = walk_json(cluster_nfs, "path")
    alias = get_alias(args.email)

    job_path = get_job_detail(args.rest, args.email,
                              job_id)["jobParams"]["jobPath"]

    mps = [
        {
            # /home/<alias>
            "server": server,
            "path": os.path.join(path, "work", alias),
            "mountPath": "/home/%s" % alias,
            "mountType": "nfs",
        },
        {
            # /job
            "server": server,
            "path": os.path.join(path, "work", ""),
            "mountPath": "/job",
            "mountType": "nfs",
            "subPath": job_path
        },
        {
            # /work
            "server": server,
            "path": os.path.join(path, "work", alias),
            "mountPath": "/work",
            "mountType": "nfs",
        },
        {
            # /data
            "server": server,
            "path": os.path.join(path, "storage", ""),
            "mountPath": "/data",
            "mountType": "nfs",
        }
    ]

    return mps


def load_system_mountpoints(args):
    config = get_config(args.config)
    sys_mps = walk_json(config, "system_mountpoints")
    if sys_mps is None:
        sys_mps = []
    mps = []
    for mp in sys_mps:
        vc = mp.get("vc")
        if vc is not None and vc != args.vc:
            continue
        if "mountType" not in mp:
            mp["mountType"] = "hostPath"
        mps.append(mp)
    return mps


def load_infiniband_mounts(args):
    config = get_config(args.config)
    mps = walk_json(config, "infiniband_mounts")
    if mps is None:
        mps = []
    return [{
        "mountType": "hostPath",
        "mountPath": mp["containerPath"],
        "hostPath": mp["hostPath"],
    } for mp in mps]


def load_distributed_system_envs(args):
    config = get_config(args.config)
    distributed_system_envs = walk_json(config, "distributed_system_envs")
    if distributed_system_envs is None or \
            not isinstance(distributed_system_envs, dict):
        distributed_system_envs = {}
    return distributed_system_envs


def mountpoint_in_volumes(mp, volumes):
    mount_type = mp["mountType"]
    if mount_type == "hostPath":
        path = mp["hostPath"]
    elif mount_type == "nfs":
        path = mp["path"]
    else:
        raise RuntimeError("Unrecognized mountpoint type %s" % mount_type)

    for volume in volumes:
        v = volume.to_dict().get(snake_case(mount_type))
        if v and v["path"] == path:
            return True
    return False


def mountpoint_in_volume_mounts(mp, volume_mounts):
    for volume_mount in volume_mounts:
        volume_mount = volume_mount.to_dict()
        mount_path = volume_mount.get("mount_path")
        sub_path = volume_mount.get("sub_path")
        if mount_path == mp["mountPath"] and sub_path == mp.get("subPath"):
            return True
    return False


def mountpoint_in_pod(mountpoint, pod):
    volumes = pod.spec.volumes
    volume_mounts = pod.spec.containers[0].volume_mounts
    return mountpoint_in_volumes(mountpoint, volumes) and \
        mountpoint_in_volume_mounts(mountpoint, volume_mounts)


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


def get_job_detail_v2(rest_url, email, job_id):
    args = urllib.parse.urlencode({
        "userName": email,
        "jobId": job_id,
    })
    url = urllib.parse.urljoin(rest_url, "/GetJobDetailV2") + "?" + args
    resp = requests.get(url)
    return resp.json()


def _op_job(rest_url, email, job_id, op, **kwargs):
    args = {
        "userName": email,
        "jobId": job_id,
    }
    args.update(kwargs)
    args = urllib.parse.urlencode(args)
    url = urllib.parse.urljoin(rest_url, "/%sJob" % op) + "?" + args
    resp = requests.get(url)
    return resp.json()


def kill_job(rest_url, email, job_id, desc):
    return _op_job(rest_url, email, job_id, "Kill", desc=desc)


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


def get_vc_meta(rest_url, vc_name, username):
    args = urllib.parse.urlencode({
        "userName": username,
        "vcName": vc_name,
    })
    url = urllib.parse.urljoin(rest_url, "/VCMeta") + "?" + args
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()


def update_vc_meta(rest_url, vc_name, username, vc_meta):
    args = urllib.parse.urlencode({
        "userName": username,
        "vcName": vc_name,
    })
    url = urllib.parse.urljoin(rest_url, "/VCMeta") + "?" + args
    resp = requests.post(url, json=vc_meta)
    resp.raise_for_status()
    return resp.json()


def add_public_key(rest_url, username, key_title, public_key):
    args = urllib.parse.urlencode({
        "username": username,
        "key_title": key_title,
    })
    url = urllib.parse.urljoin(rest_url, "/PublicKey") + "?" + args
    resp = requests.post(url, json={"public_key": public_key})
    resp.raise_for_status()
    return resp.json()


def delete_public_key(rest_url, username, key_id):
    args = urllib.parse.urlencode({
        "username": username,
        "key_id": key_id,
    })
    url = urllib.parse.urljoin(rest_url, "/PublicKey") + "?" + args
    resp = requests.delete(url)
    resp.raise_for_status()
    return resp.json()


def get_public_key(rest_url, username):
    args = urllib.parse.urlencode({
        "username": username,
    })
    url = urllib.parse.urljoin(rest_url, "/PublicKey") + "?" + args
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()


def scale_job(rest_url, email, job_id, resourcegpu):
    args = urllib.parse.urlencode({
        "userName": email,
        "jobId": job_id,
        "resourcegpu": resourcegpu,
    })
    url = urllib.parse.urljoin(rest_url, "ScaleJob") + "?" + args
    resp = requests.get(url)
    return resp.json()


def get_job_insight(rest_url, email, job_id):
    args = urllib.parse.urlencode({
        "jobId": job_id,
        "userName": email,
    })
    url = urllib.parse.urljoin(rest_url, "/Insight") + "?" + args
    resp = requests.get(url)
    return resp.json()


def set_job_insight(rest_url, email, job_id, insight):
    args = urllib.parse.urlencode({
        "jobId": job_id,
        "userName": email,
    })
    url = urllib.parse.urljoin(rest_url, "/Insight") + "?" + args
    resp = requests.post(url, json=insight)
    return resp


def set_repair_message(rest_url, email, job_id, repair_message):
    args = urllib.parse.urlencode({
        "jobId": job_id,
        "userName": email,
    })
    url = urllib.parse.urljoin(rest_url, "/RepairMessage") + "?" + args
    resp = requests.post(url, json=repair_message)
    return resp


def get_job_priorities(rest_url):
    """This retrieves priorities of all active jobs"""
    url = urllib.parse.urljoin(rest_url, "/jobs/priorities")
    resp = requests.get(url)
    return resp.json()


def set_job_priorities(rest_url, email, priorities):
    args = urllib.parse.urlencode({
        "userName": email,
    })
    url = urllib.parse.urljoin(rest_url, "/jobs/priorities") + "?" + args
    resp = requests.post(url, json=priorities)
    return resp


def get_active_jobs(rest_url):
    """This retrieves all active jobs"""
    url = urllib.parse.urljoin(rest_url, "/ListActiveJobs")
    resp = requests.get(url)
    return resp.json()


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
            resp = kill_job(
                self.rest_url, email, self.jid,
                "kill from testing with type %s, value %s, traceback %s" %
                (type, value, traceback))
            logger.info("killed job %s", self.jid)
        except Exception:
            logger.exception("failed to kill job %s", self.jid)

    def block_until_state_not_in(self, states, timeout=300):
        return block_until_state_not_in(self.rest_url,
                                        self.jid,
                                        states,
                                        timeout=timeout)


class vc_setting(object):
    def __init__(self, rest_url, vc_name, username, vc_spec):
        self.rest_url = rest_url
        self.vc_name = vc_name
        self.username = username
        self.vc_spec = vc_spec
        self.origin_vc_spec = None

    def __enter__(self):
        self.origin_vc_spec = get_vc_meta(self.rest_url, self.vc_name,
                                          self.username)
        spec = copy.deepcopy(self.origin_vc_spec)
        spec.update(self.vc_spec)
        update_vc_meta(self.rest_url, self.vc_name, self.username, spec)
        logger.info("update vc meta from %s to %s",
                    json.dumps(self.origin_vc_spec), json.dumps(spec))
        return self

    def __exit__(self, type, value, traceback):
        try:
            if self.origin_vc_spec is None:
                return
            update_vc_meta(self.rest_url, self.vc_name, self.username,
                           self.origin_vc_spec)
            logger.info("rollback vc meta to %s",
                        json.dumps(self.origin_vc_spec))
        except Exception:
            logger.exception("failed to rollback vc meta %s",
                             json.dumps(self.origin_vc_spec))


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
    args = {
        "userName": email,
        "jobId": jid,
    }
    args = urllib.parse.urlencode(args)
    url = urllib.parse.urljoin(rest_url, "/GetJobRawLog") + "?" + args
    resp = requests.get(url)
    if resp.status_code == 404:
        return None
    return resp.text


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
    resp.raise_for_status()
    return resp.json()


def wait_endpoint_state(rest_url,
                        email,
                        jid,
                        endpoint_id,
                        state="running",
                        timeout=120):
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
        config.host = "https://%s.%s:1443" % (
            infra_host, cluster_config["network"]["domain"])
        basic_auth = cluster_config["basic_auth"]
    else:
        config.host = cluster_config["machines"][infra_host]["fqdns"]
        with open(os.path.join(config_path, "clusterID",
                               "k8s_basic_auth.yml")) as auf:
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


def kube_get_deployment(config_path, namespace, name):
    k8s_config = build_k8s_config(config_path)
    api_client = ApiClient(configuration=k8s_config)

    k8s_apps_api = k8s_client.AppsV1Api(api_client)
    api_response = k8s_apps_api.read_namespaced_deployment_scale(
        namespace=namespace,
        pretty="pretty_example",
        name=name,
    )
    logger.debug("%s got deployment from namespace %s: api_response", name,
                 namespace, api_response)
    return api_response


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


def set_job_max_time(rest_url, email, job_id, second):
    args = urllib.parse.urlencode({
        "userName": email,
        "jobId": job_id,
        "second": second,
    })
    url = urllib.parse.urljoin(rest_url, "/JobMaxTime") + "?" + args
    return requests.post(url)
