#!/usr/bin/env python3

import logging
import json
import os
import requests
import urllib.parse

from enum import Enum
from kubernetes import client as k8s_client, config as k8s_config
from kubernetes.client.rest import ApiException


logger = logging.getLogger(__name__)

KUBERNETES_CONFIG_FILE = "/etc/kubernetes/restapi-kubeconfig.yaml"


class K8sUtil(object):
    def __init__(self):
        k8s_config.load_kube_config(config_file=KUBERNETES_CONFIG_FILE)
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

    def cordon(self, node):
        try:
            api_call_body = k8s_client.V1Node(
                spec=k8s_client.V1NodeSpec(unschedulable=True))
            self.k8s_core_api.patch_node(node, api_call_body)
            logger.info("node %s cordoned", node)
            return True
        except ApiException:
            logger.exception("cordon failed for node %s", node)
        return False

    def uncordon(self, node):
        try:
            api_call_body = k8s_client.V1Node(
                spec=k8s_client.V1NodeSpec(unschedulable=False))
            self.k8s_core_api.patch_node(node, api_call_body)
            logger.info("node %s uncordoned", node)
            return True
        except ApiException:
            logger.exception("uncordon failed for node %s", node)
        return False

    def label(self, node, key, value):
        try:
            api_call_body = k8s_client.V1Node(
                metadata=k8s_client.V1ObjectMeta(labels={key: value}))
            self.k8s_core_api.patch_node(node, api_call_body)
            return True
        except ApiException:
            logger.exception("label failed for node %s, key %s, value %s",
                             node, key, value)
        return False

    def annotate(self, node, key, value):
        try:
            api_call_body = k8s_client.V1Node(
                metadata=k8s_client.V1ObjectMeta(annotations={key: value}))
            self.k8s_core_api.patch_node(node, api_call_body)
            return True
        except ApiException:
            logger.exception("annotate failed for node %s, key %s, value %s",
                             node, key, value)
        return False


class RestUtil(object):
    def __init__(self):
        self.rest_url = os.environ.get("REST_URL", "http://localhost:5000")

    def list_vcs(self):
        args = urllib.parse.urlencode({"userName": "Administrator"})
        url = urllib.parse.urljoin(self.rest_url, "/ListVCs") + "?" + args
        resp = requests.get(url)
        return resp.json()

    def get_job_status(self, job_id):
        args = urllib.parse.urlencode({"jobId": job_id})
        url = urllib.parse.urljoin(self.rest_url, "/GetJobStatus") + "?" + args
        resp = requests.get(url)
        return resp.json()

    def pause_jobs(self, job_ids):
        args = urllib.parse.urlencode({
            "userName": "Administrator",
            "jobIds": job_ids,
        })
        url = urllib.parse.urljoin(self.rest_url, "/PauseJobs") + "?" + args
        resp = requests.get(url)
        return resp.json()

    def resume_jobs(self, job_ids):
        args = urllib.parse.urlencode({
            "userName": "Administrator",
            "jobIds": job_ids,
        })
        url = urllib.parse.urljoin(self.rest_url, "/ResumeJobs") + "?" + args
        resp = requests.get(url)
        return resp.json()


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
    OUT_OF_POOL = "OUT_OF_POOL"
    READY_FOR_REPAIR = "READY_FOR_REPAIR"
    IN_REPAIR = "IN_REPAIR"
    AFTER_REPAIR = "AFTER_REPAIR"


class Job(object):
    def __init__(self, job_id, username, vc_name):
        self.job_id = job_id
        self.username = username
        self.vc_name = vc_name
        self.pods = []

    def __repr__(self):
        return str(self.__dict__)


class Node(object):
    def __init__(self, name, ip, ready, unschedulable, gpu_expected, state,
                 unhealthy_rules):
        self.name = name
        self.ip = ip
        self.ready = ready
        self.unschedulable = unschedulable
        self.gpu_expected = gpu_expected
        self.state = state
        self.unhealthy_rules = unhealthy_rules
        self.jobs = {}

    def __repr__(self):
        return str(self.__dict__)


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


def parse_nodes(k8s_nodes, metadata, nodes):
    for k8s_node in k8s_nodes:
        try:
            hostname, internal_ip = get_hostname_and_internal_ip(k8s_node)
            if hostname is None or internal_ip is None:
                logger.error("skip None hostname/internal_ip: %s", k8s_node)
                continue

            ready = get_ready(k8s_node)
            unschedulable = k8s_node.spec.unschedulable is True
            sku = k8s_node.metadata.labels.get("sku")
            gpu_expected = metadata.get(sku, {}).get("per_node", 0)

            if k8s_node.metadata.labels is None:
                state = State.IN_SERVICE
            else:
                state = State(k8s_node.metadata.labels.get(
                    "REPAIR_STATE", "IN_SERVICE"))

            if k8s_node.metadata.annotations is None:
                unhealthy_rules = None
            else:
                unhealthy_rules = k8s_node.metadata.annotations.get(
                    "REPAIR_UNHEALTHY_RULES", None)
            if unhealthy_rules is not None:
                unhealthy_rules = unhealthy_rules.split(",")

            node = Node(hostname, internal_ip, ready, unschedulable,
                        gpu_expected, state, unhealthy_rules)
            nodes[internal_ip] = node
        except:
            logger.exception("failed to parse k8s node %s", k8s_node)


def parse_pods(k8s_pods, nodes):
    for k8s_pod in k8s_pods:
        try:
            if k8s_pod.metadata is None or k8s_pod.metadata.labels is None or \
                    k8s_pod.metadata.name is None:
                continue
            if k8s_pod.status is None or k8s_pod.status.host_ip is None:
                continue

            pod_name = k8s_pod.metadata.name
            labels = k8s_pod.metadata.labels
            host_ip = k8s_pod.status.host_ip
            node = nodes.get(host_ip)
            if "jobId" in labels and "userName" in labels and \
                    "vcName" in labels and node is not None:
                job_id = labels["jobId"]
                username = labels["userName"]
                vc_name = labels["vcName"]
                if job_id not in node.jobs:
                    node.jobs[job_id] = Job(job_id, username, vc_name)
                node.jobs[job_id].pods.append(pod_name)
        except:
            logger.exception("failed to parse k8s pod %s", k8s_pod)


def parse_for_nodes(k8s_nodes, k8s_pods, vc_list):
    metadata = {}
    # Merge metadata from all VCs together
    for vc in vc_list:
        resource_metadata = json.loads(vc.get("resourceMetadata", {}))
        gpu_metadata = resource_metadata.get("gpu", {})
        metadata.update(gpu_metadata)

    nodes = {}
    parse_nodes(k8s_nodes, metadata, nodes)
    parse_pods(k8s_pods, nodes)
    return list(nodes.values())


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

    # Cordon a node
    ret = k8s_util.cordon(first_node_name)
    logger.info("node: %s cordon success: %s", first_node_name, ret)
    assert ret is True, "node %s should be cordoned" % first_node_name
    first_node = k8s_util.list_node(
        label_selector="kubernetes.io/hostname=%s" % first_node_name)[0]
    unschedulable = first_node.spec.unschedulable is True
    logger.info("node: %s, unschedulable: %s", first_node_name, unschedulable)

    # Uncordon a node
    ret = k8s_util.uncordon(first_node_name)
    logger.info("node: %s uncordon success: %s", first_node_name, ret)
    assert ret is True, "node %s should be uncordoned"
    first_node = k8s_util.list_node(
        label_selector="kubernetes.io/hostname=%s" % first_node_name)[0]
    unschedulable = first_node.spec.unschedulable is True
    logger.info("node: %s, unschedulable: %s", first_node_name, unschedulable)

    # Label a node
    ret = k8s_util.label(first_node_name, "TEST_KEY", "TEST_VALUE")
    logger.info("node: %s label success: %s", first_node_name, ret)
    assert ret is True, "node %s should be labeled" % first_node_name
    first_node = k8s_util.list_node(
        label_selector="kubernetes.io/hostname=%s" % first_node_name)[0]
    assert first_node.metadata.labels.get("TEST_KEY") == "TEST_VALUE"

    # Un-label a node
    ret = k8s_util.label(first_node_name, "TEST_KEY", None)
    logger.info("node: %s un-label success: %s", first_node_name, ret)
    assert ret is True, "node %s should be un-labeled" % first_node_name
    first_node = k8s_util.list_node(
        label_selector="kubernetes.io/hostname=%s" % first_node_name)[0]
    assert first_node.metadata.labels.get("TEST_KEY") is None

    # Annotate a node
    ret = k8s_util.annotate(first_node_name, "TEST_KEY", "TEST_VALUE")
    logger.info("node: %s annotate success: %s", first_node_name, ret)
    assert ret is True, "node %s should be annotated" % first_node_name
    first_node = k8s_util.list_node(
        label_selector="kubernetes.io/hostname=%s" % first_node_name)[0]
    assert first_node.metadata.annotations.get("TEST_KEY") == "TEST_VALUE"

    # Un-annotate a node
    ret = k8s_util.annotate(first_node_name, "TEST_KEY", None)
    logger.info("node: %s un-annotate success: %s", first_node_name, ret)
    assert ret is True, "node %s should be un-annotated" % first_node_name
    first_node = k8s_util.list_node(
        label_selector="kubernetes.io/hostname=%s" % first_node_name)[0]
    assert first_node.metadata.annotations.get("TEST_KEY") is None

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

    # parse_for_nodes
    nodes = parse_for_nodes(k8s_nodes, k8s_pods, vc_list)
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
