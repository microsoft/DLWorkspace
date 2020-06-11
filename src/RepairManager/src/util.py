#!/usr/bin/env python3

import logging
import os
import requests
import urllib.parse

from kubernetes import client as k8s_client, config as k8s_config
from kubernetes.client.rest import ApiException


logger = logging.getLogger(__name__)


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


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(threadName)s - %(filename)s:%(lineno)s - %(message)s",
        level="INFO")

    # K8sUtil test
    k8s_util = K8sUtil()
    logger.info("nodes:")
    nodes = k8s_util.list_node()
    assert nodes is not None

    first_node = None
    first_node_name = None
    for i, node in enumerate(nodes):
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

    ret = k8s_util.cordon(first_node_name)
    logger.info("node: %s cordon success: %s", first_node_name, ret)
    assert ret is True, "node %s should be cordoned" % first_node_name
    first_node = k8s_util.list_node(
        label_selector="kubernetes.io/hostname=%s" % first_node_name)[0]
    unschedulable = first_node.spec.unschedulable is True
    logger.info("node: %s, unschedulable: %s", first_node_name, unschedulable)

    ret = k8s_util.uncordon(first_node_name)
    logger.info("node: %s uncordon success: %s", first_node_name, ret)
    assert ret is True, "node %s should be uncordoned"
    first_node = k8s_util.list_node(
        label_selector="kubernetes.io/hostname=%s" % first_node_name)[0]
    unschedulable = first_node.spec.unschedulable is True
    logger.info("node: %s, unschedulable: %s", first_node_name, unschedulable)

    logger.info("pods:")
    pods = k8s_util.list_pods()
    assert pods is not None

    for pod in pods:
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
    if pods is not None and len(pods) > 0:
        job_id = pods[0].metadata.labels.get("jobId")
        job_status = rest_util.get_job_status(job_id)["jobStatus"]
        logger.info("job_id: %s status: %s", job_id, job_status)

    vc_list = rest_util.list_vcs()["result"]
    for vc in vc_list:
        logger.info("vcName: %s, resourceMetadata: %s", vc.get("vcName"),
                    vc.get("resourceMetadata"))

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
