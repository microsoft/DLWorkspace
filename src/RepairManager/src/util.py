#!/usr/bin/env python3

import faulthandler
import logging
import json
import os
import requests
import signal
import smtplib
import sys
import threading
import urllib.parse

from enum import Enum
from kubernetes import client as k8s_client, config as k8s_config
from kubernetes.client.rest import ApiException
from constant import REPAIR_STATE, REPAIR_UNHEALTHY_RULES, \
    REPAIR_STATE_LAST_UPDATE_TIME, REPAIR_CYCLE


logger = logging.getLogger(__name__)


class AtomicRef(object):
    """A thread safe way to store and get object. Data retrieved from this ref
    should not be modified.
    """
    def __init__(self):
        self.data = None
        self.lock = threading.RLock()

    def set(self, data):
        with self.lock:
            self.data = data

    def get(self):
        with self.lock:
            return self.data

    def set_if_none(self, data):
        """Set data if there is no existing data"""
        with self.lock:
            if self.data is None:
                self.data = data
                return True
        return False


def get_logging_level():
    mapping = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING
    }

    result = logging.INFO

    if os.environ.get("LOGGING_LEVEL") is not None:
        level = os.environ["LOGGING_LEVEL"]
        result = mapping.get(level.upper())
        if result is None:
            sys.stderr.write("unknown logging level " + level +
                             ", default to INFO\n")
            result = logging.INFO

    return result


def register_stack_trace_dump():
    faulthandler.register(signal.SIGTRAP, all_threads=True, chain=False)


class K8sUtil(object):
    def __init__(self):
        k8s_config.load_kube_config()
        self.k8s_core_api = k8s_client.CoreV1Api()
        self.pretty = "pretty_example"

    def list_node(self, label_selector="worker=active"):
        try:
            resp = self.k8s_core_api.list_node(pretty=self.pretty,
                                               label_selector=label_selector)
            return resp.items
        except ApiException:
            logger.exception("list_node failed for label_selector: %s",
                             label_selector)
        return None

    def list_pods(self, namespace="default", label_selector="jobId"):
        try:
            resp = self.k8s_core_api.list_namespaced_pod(
                pretty=self.pretty, namespace=namespace,
                label_selector=label_selector)
            return resp.items
        except ApiException:
            logger.exception("list_namespaced_pod failed for namespace: %s, "
                             "label_selector: %s", namespace, label_selector)
        return None

    def patch_node(self, node, unschedulable=None, labels=None,
                   annotations=None):
        try:
            api_call_body = k8s_client.V1Node()
            if unschedulable is not None:
                api_call_body.spec = k8s_client.V1NodeSpec(unschedulable=unschedulable)
            metadata = k8s_client.V1ObjectMeta()
            if labels is not None:
                metadata.labels = labels
            if annotations is not None:
                metadata.annotations = annotations
            api_call_body.metadata = metadata
            self.k8s_core_api.patch_node(node, api_call_body)
            return True
        except ApiException:
            logger.exception(
                "patch failed for node: %s, unschedulable: %s, labels: %s, "
                "annotations: %s", node, unschedulable, labels, annotations)
        return False


class RestUtil(object):
    def __init__(self):
        self.rest_url = os.environ.get("REST_URL", "http://localhost:5000")

    def list_vcs(self):
        args = urllib.parse.urlencode({"userName": "Administrator"})
        url = urllib.parse.urljoin(self.rest_url, "/ListVCs") + "?" + args
        resp = requests.get(url, timeout=5)
        return resp.json()

    def get_job_status(self, job_id):
        args = urllib.parse.urlencode({"jobId": job_id})
        url = urllib.parse.urljoin(self.rest_url, "/GetJobStatus") + "?" + args
        resp = requests.get(url, timeout=5)
        return resp.json()

    def pause_jobs(self, job_ids):
        args = urllib.parse.urlencode({
            "userName": "Administrator",
            "jobIds": job_ids,
        })
        url = urllib.parse.urljoin(self.rest_url, "/PauseJobs") + "?" + args
        resp = requests.get(url, timeout=5)
        return resp.json()

    def resume_jobs(self, job_ids):
        args = urllib.parse.urlencode({
            "userName": "Administrator",
            "jobIds": job_ids,
        })
        url = urllib.parse.urljoin(self.rest_url, "/ResumeJobs") + "?" + args
        resp = requests.get(url, timeout=5)
        return resp.json()

    def get_active_jobs(self):
        url = urllib.parse.urljoin(self.rest_url, "/ListActiveJobs")
        resp = requests.get(url)
        return resp.json()

    def update_repair_message(self, job_id, repair_message):
        args = urllib.parse.urlencode({
            "userName": "Administrator",
            "jobId": job_id,
        })
        url = urllib.parse.urljoin(self.rest_url, "/RepairMessage") + "?" + args
        resp = requests.post(url, json=repair_message, timeout=5)
        return resp


class PrometheusUtil(object):
    def __init__(self):
        self.prometheus_url = os.environ.get("PROMETHEUS_URL",
                                             "http://localhost:9091")

    def query(self, query):
        args = urllib.parse.urlencode({"query": query})
        url = urllib.parse.urljoin(self.prometheus_url,
                                   "/prometheus/api/v1/query") + "?" + args
        resp = requests.get(url)
        return resp.json()


def walk_json(obj, *fields):
    try:
        for f in fields:
            obj = obj[f]
        return obj
    except:
        return None


class State(Enum):
    IN_SERVICE = "IN_SERVICE"
    OUT_OF_POOL_UNTRACKED = "OUT_OF_POOL_UNTRACKED"
    OUT_OF_POOL = "OUT_OF_POOL"
    READY_FOR_REPAIR = "READY_FOR_REPAIR"
    IN_REPAIR = "IN_REPAIR"
    AFTER_REPAIR = "AFTER_REPAIR"


class Job(object):
    def __init__(self, job_id, username, vc_name):
        self.job_id = job_id
        self.username = username
        self.vc_name = vc_name
        self.unhealthy_nodes = {}  # node name -> Node

    @property
    def wait_for_jobs(self):
        """Wait if any unhealthy rule from any unhealthy node needs to wait"""
        for _, node in self.unhealthy_nodes:
            for rule in node.unhealthy_rules:
                if rule.wait_for_job:
                    return True
        return False

    def __repr__(self):
        return str(self.__dict__)


class Node(object):
    def __init__(self, name, ip, ready, unschedulable, sku, gpu_expected,
                 gpu_total, gpu_allocatable, state, infiniband=None, ipoib=None,
                 nv_peer_mem=None, nvsm=None, unhealthy_rules=None,
                 last_update_time=None, repair_cycle=False):
        self.name = name
        self.ip = ip
        self.ready = ready
        self.unschedulable = unschedulable
        self.sku = sku
        self.gpu_expected = gpu_expected
        self.gpu_total = gpu_total
        self.gpu_allocatable = gpu_allocatable
        self.state = state
        self.infiniband = infiniband
        self.ipoib = ipoib
        self.nv_peer_mem = nv_peer_mem
        self.nvsm = nvsm
        self.unhealthy_rules = unhealthy_rules if unhealthy_rules else []
        self.last_update_time = last_update_time
        self.repair_cycle = repair_cycle
        self.repair_message = None  # to be filled in in repair cycle
        self.jobs = {}  # job id -> Job
        self.evict_jobs = False  # whether to evict jobs preparing for repair

    @property
    def state_name(self):
        return self.state.name

    def __repr__(self):
        return str(self.__dict__)


def parse_jobs(job_list, jobs):
    for job in job_list:
        job_id = job.get("jobId")
        username = job.get("userName")
        vc_name = job.get("vcName")
        if job_id is None or username is None or vc_name is None:
            logger.warning("ignore parsing job %s", job)
            continue
        jobs[job_id] = Job(job_id, username, vc_name)


def parse_metadata(vc_list, metadata):
    # Merge metadata from all VCs together
    for vc in vc_list:
        resource_metadata = json.loads(vc.get("resourceMetadata", {}))
        gpu_metadata = resource_metadata.get("gpu", {})
        metadata.update(gpu_metadata)


def get_hostname_and_internal_ip(k8s_node):
    hostname = internal_ip = None
    for address in k8s_node.status.addresses:
        if address.type == 'Hostname':
            hostname = address.address
        if address.type == 'InternalIP':
            internal_ip = address.address
    return hostname, internal_ip


def get_ready(k8s_node):
    ready = False
    if k8s_node.status is not None and k8s_node.status.conditions is not None:
        for condition in k8s_node.status.conditions:
            if condition.type == "Ready" and condition.status == "True":
                ready = True
                break
    return ready


def get_gpu_total_and_allocatable(k8s_node):
    if k8s_node.status is None:
        return 0, 0
    total = allocatable = 0
    if k8s_node.status.capacity is not None:
        total = int(k8s_node.status.capacity.get("nvidia.com/gpu", 0))
    if k8s_node.status.allocatable is not None:
        allocatable = int(k8s_node.status.allocatable.get("nvidia.com/gpu", 0))
    return total, allocatable


def parse_nodes(k8s_nodes, metadata, rules, config, nodes):
    rules_mapping = {rule.name: rule for rule in rules}
    for k8s_node in k8s_nodes:
        try:
            # Parse node name and ip
            hostname, internal_ip = get_hostname_and_internal_ip(k8s_node)
            if hostname is None or internal_ip is None:
                logger.error("skip None hostname/internal_ip: %s", k8s_node)
                continue

            # Parse ready and unschedulable
            ready = get_ready(k8s_node)
            unschedulable = k8s_node.spec.unschedulable is True

            sku = k8s_node.metadata.labels.get("sku", "None")
            # Parse expected gpu
            gpu_expected = metadata.get(sku, {}).get("per_node", 0)

            # Parse total and allocatable gpu
            gpu_total, gpu_allocatable = get_gpu_total_and_allocatable(k8s_node)

            # Parse repair state
            if k8s_node.metadata.labels is None:
                state = State.IN_SERVICE
            else:
                state = State(k8s_node.metadata.labels.get(
                    REPAIR_STATE, "IN_SERVICE"))

            # Parse infiniband
            infiniband = config.get("infiniband", {}).get(sku, [])

            # Parse ipoib
            ipoib = config.get("ipoib", {}).get(sku, [])

            # Parse nv_peer_mem
            nv_peer_mem = config.get("nv_peer_mem", {}).get(sku)

            # Parse nvsm
            nvsm = config.get("nvsm", {}).get(sku)
            # Both DGX-2 and DGX-2 equivalent have label "DGX-2"
            # An DGX-2 equivalent does not have nvsm installed.
            # TODO: relabel DGX-2 equivalent with a unique sku
            if nvsm is not None:
                exception = config.get("nvsm_exception", [])
                if hostname in exception:
                    nvsm = None

            # Parse unhealthy rules on the node
            unhealthy_rules = []
            if k8s_node.metadata.annotations is not None:
                unhealthy_rule_names = k8s_node.metadata.annotations.get(
                    REPAIR_UNHEALTHY_RULES)
                if unhealthy_rule_names is not None:
                    unhealthy_rule_names = unhealthy_rule_names.split(",")
                    for rule_name in unhealthy_rule_names:
                        rule = rules_mapping.get(rule_name)
                        if rule is None:
                            logger.error(
                                "skip non-existent rule %s for node %s (%s)",
                                rule_name, hostname, internal_ip)
                            continue
                        unhealthy_rules.append(rule)

            # Parse repair state last update time
            last_update_time = None
            if k8s_node.metadata.annotations is not None:
                last_update_time = k8s_node.metadata.annotations.get(
                    REPAIR_STATE_LAST_UPDATE_TIME)

            # Parse repair cycle boolean
            repair_cycle = False
            if k8s_node.metadata.annotations is not None:
                repair_cycle = k8s_node.metadata.annotations.get(
                    REPAIR_CYCLE) == "True"

            node = Node(hostname, internal_ip, ready, unschedulable, sku,
                        gpu_expected, gpu_total, gpu_allocatable, state,
                        infiniband=infiniband, ipoib=ipoib,
                        nv_peer_mem=nv_peer_mem, nvsm=nvsm,
                        unhealthy_rules=unhealthy_rules,
                        last_update_time=last_update_time,
                        repair_cycle=repair_cycle)
            nodes[internal_ip] = node
        except:
            logger.exception("failed to parse k8s node %s", k8s_node)


def parse_pods(k8s_pods, nodes, jobs):
    for k8s_pod in k8s_pods:
        try:
            if k8s_pod.metadata is None or k8s_pod.metadata.labels is None or \
                    k8s_pod.metadata.name is None:
                continue
            if k8s_pod.status is None or k8s_pod.status.host_ip is None:
                continue

            labels = k8s_pod.metadata.labels
            host_ip = k8s_pod.status.host_ip
            node = nodes.get(host_ip)
            if "jobId" in labels and node is not None:
                job_id = labels["jobId"]
                # Add active job for the node
                if job_id in jobs and job_id not in node.jobs:
                    node.jobs[job_id] = jobs[job_id]
                # Add unhealthy nodes for the job
                if len(node.unhealthy_rules) > 0 and \
                        node.name not in jobs[job_id].unhealthy_nodes:
                    jobs[job_id].unhealthy_nodes[node.name] = node
        except:
            logger.exception("failed to parse k8s pod %s", k8s_pod)


def parse_for_jobs_and_nodes(job_list, vc_list, k8s_nodes, k8s_pods, rules,
                             config):
    # Parse jobs
    jobs = {}
    parse_jobs(job_list, jobs)

    # Parse gpu metadata
    metadata = {}
    parse_metadata(vc_list, metadata)

    # Parse nodes
    nodes = {}
    parse_nodes(k8s_nodes, metadata, rules, config, nodes)

    # Parse pods to populate jobs on node, and unhealthy nodes for jobs
    parse_pods(k8s_pods, nodes, jobs)

    return list(jobs.values()), list(nodes.values())


class EmailHandler(object):
    def __init__(self, smtp_url, sender, username=None, password=None):
        self.smtp_url = smtp_url
        self.sender = sender
        self.username = username
        self.password = password

    def send(self, message):
        message["From"] = self.sender

        try:
            with smtplib.SMTP(self.smtp_url) as server:
                if self.username and self.password:
                    server.starttls()
                    server.login(self.username, self.password)
                server.send_message(message)
        except smtplib.SMTPAuthenticationError:
            logger.error(
                "The server didn\'t accept the user/password combination.")
        except smtplib.SMTPServerDisconnected:
            logger.error("Server unexpectedly disconnected")
        except smtplib.SMTPException:
            logger.exception("STMP exception")


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(threadName)s - %(filename)s:%(lineno)s - %(message)s",
        level="INFO")

    # K8sUtil test
    k8s_util = K8sUtil()
    logger.info("nodes:")
    k8s_nodes = k8s_util.list_node()
    assert k8s_nodes is not None

    first_node = None
    first_node_name = None
    for i, node in enumerate(k8s_nodes):
        hostname = None
        internal_ip = None
        for address in node.status.addresses:
            if address.type == 'Hostname':
                hostname = address.address
            if address.type == 'InternalIP':
                internal_ip = address.address
        logger.info("hostname: %s, internal_ip: %s", hostname, internal_ip)
        if i == 0:
            first_node = node
            first_node_name = hostname

    unschedulable = first_node.spec.unschedulable is True
    assert unschedulable is False, "node %s should be schedulable" % \
                                   first_node_name
    logger.info("node: %s, unschedulable: %s", first_node_name, unschedulable)

    # Cordon, label, annotate a node
    ret = k8s_util.patch_node(
        first_node_name,
        unschedulable=True,
        labels={"TEST_LABEL_KEY": "TEST_LABEL_VALUE"},
        annotations={"TEST_ANNOTATION_KEY": "TEST_ANNOTATION_VALUE"})
    logger.info("node: %s patch success: %s", first_node_name, ret)
    assert ret is True, "node %s should be patched" % first_node_name
    first_node = k8s_util.list_node(
        label_selector="kubernetes.io/hostname=%s" % first_node_name)[0]
    unschedulable = first_node.spec.unschedulable is True
    logger.info("node: %s, unschedulable: %s, TEST_LABEL_KEY: %s, "
                "TEST_ANNOTATION_KEY: %s", first_node_name, unschedulable,
                first_node.metadata.labels.get("TEST_LABEL_KEY"),
                first_node.metadata.annotations.get("TEST_ANNOTATION_KEY"))
    assert unschedulable is True
    assert first_node.metadata.labels.get("TEST_LABEL_KEY") == \
        "TEST_LABEL_VALUE"
    assert first_node.metadata.annotations.get("TEST_ANNOTATION_KEY") == \
        "TEST_ANNOTATION_VALUE"

    # Uncordon, un-label, un-annotate a node
    ret = k8s_util.patch_node(
        first_node_name,
        unschedulable=False,
        labels={"TEST_LABEL_KEY": None},
        annotations={"TEST_ANNOTATION_KEY": None})
    logger.info("node: %s patch success: %s", first_node_name, ret)
    assert ret is True, "node %s should be patched" % first_node_name
    first_node = k8s_util.list_node(
        label_selector="kubernetes.io/hostname=%s" % first_node_name)[0]
    unschedulable = first_node.spec.unschedulable is True
    logger.info("node: %s, unschedulable: %s, TEST_LABEL_KEY: %s, "
                "TEST_ANNOTATION_KEY: %s", first_node_name, unschedulable,
                first_node.metadata.labels.get("TEST_LABEL_KEY"),
                first_node.metadata.annotations.get("TEST_ANNOTATION_KEY"))
    assert unschedulable is False
    assert first_node.metadata.labels.get("TEST_LABEL_KEY") is None
    assert first_node.metadata.annotations.get("TEST_ANNOTATION_KEY") is None

    # Patch empty stuff
    ret = k8s_util.patch_node(first_node_name)
    logger.info("node: %s patch success: %s", first_node_name, ret)
    assert ret is True, "node %s should be patched" % first_node_name
    first_node = k8s_util.list_node(
        label_selector="kubernetes.io/hostname=%s" % first_node_name)[0]
    unschedulable = first_node.spec.unschedulable is True
    logger.info("node: %s, unschedulable: %s", first_node_name, unschedulable)
    assert unschedulable is False

    logger.info("pods:")
    k8s_pods = k8s_util.list_pods()
    assert k8s_pods is not None

    for pod in k8s_pods:
        name = pod.metadata.name
        job_id = pod.metadata.labels.get("jobId")
        node_name = pod.spec.node_name
        username = pod.metadata.labels.get("userName")
        vc_name = pod.metadata.labels.get("vcName")
        logger.info("name: %s, job_id: %s, node_name: %s, username: %s, "
                    "vc_name: %s", name, job_id, node_name, username, vc_name)

    # RestUtil test
    rest_util = RestUtil()
    # Display the status of the first job from pods
    if k8s_pods is not None and len(k8s_pods) > 0:
        job_id = k8s_pods[0].metadata.labels.get("jobId")
        job_status = rest_util.get_job_status(job_id)["jobStatus"]
        logger.info("job_id: %s status: %s", job_id, job_status)

    vc_list = rest_util.list_vcs()["result"]
    for vc in vc_list:
        logger.info("vcName: %s, resourceMetadata: %s", vc.get("vcName"),
                    vc.get("resourceMetadata"))

    # parse_for_jobs_and_nodes
    from rule import K8sGpuRule, DcgmEccDBERule
    hostname, _ = get_hostname_and_internal_ip(k8s_nodes[1])
    config = {
        "infiniband": {"Standard_ND24rs": ["mlx4_0:1"]},
        "ipoib": {"Standard_ND24rs": ["ib0"]},
        "nv_peer_mem": {"Standard_ND24rs": 1},
        "nvsm": {"Standard_ND24rs": True},
        "nvsm_exception": [hostname],
    }
    nodes = parse_for_jobs_and_nodes(
        k8s_nodes, k8s_pods, vc_list, [K8sGpuRule(), DcgmEccDBERule()], config)
    for node in nodes:
        logger.info("%s", node)

    # PrometheusUtil test
    prometheus_util = PrometheusUtil()
    query = "avg_over_time(dcgm_ecc_dbe_volatile_total[10m])==0"
    resp = prometheus_util.query(query)
    logger.info("query: %s. result: %s", query,
                walk_json(resp, "data", "result"))

    query = "avg_over_time(dcgm_ecc_dbe_volatile_total[10m])>0"
    resp = prometheus_util.query(query)
    logger.info("query: %s. result: %s", query,
                walk_json(resp, "data", "result"))
