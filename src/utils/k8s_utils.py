#!/usr/bin/env python3

import logging

from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)

# The config will be loaded from default location.
k8s_config.load_kube_config()
k8s_core_api = client.CoreV1Api()
k8s_app_api = client.AppsV1Api()


class K8sUtil(object):
    def __init__(self, timeout_seconds=0):
        self.core_api = k8s_core_api
        self.app_api = k8s_app_api
        self.pretty = "true"
        self.timeout_seconds = timeout_seconds

    def get_namespaced_pods(self, namespace="default"):
        """Finds all pods in the given namespace.

        Args:
            namespace: Kubernetes namespace in which to look for pods.

        Returns:
            A list of pods in the given namespace
        """
        pods = []
        try:
            resp = self.core_api.list_namespaced_pod(
                namespace,
                pretty=self.pretty,
                timeout_seconds=self.timeout_seconds)
            logger.debug("Namespaced pods for %s: %s", namespace, resp)
            pods = resp.items
        except ApiException:
            msg = "Error getting namespaced pods for %s" % namespace
            logger.warning(msg, exc_info=True)
        return pods

    def get_all_pods(self):
        """Finds all pods in all Kubernetes namespaces.

        Returns:
            A list of pods in all Kubernetes namespaces.
        """
        pods = []
        try:
            resp = self.core_api.list_pod_for_all_namespaces(
                pretty=self.pretty, timeout_seconds=self.timeout_seconds)
            logger.debug("All pods: %s", resp)
            pods = resp.items
        except ApiException:
            msg = "Error getting all pods"
            logger.warning(msg, exc_info=True)
        return pods

    def get_all_nodes(self):
        """Finds all Kubernetes nodes.

        Returns:
            A list of all Kubernetes nodes.
        """
        nodes = []
        try:
            resp = self.core_api.list_node(pretty=self.pretty,
                                           timeout_seconds=self.timeout_seconds)
            logger.debug("All nodes: %s", resp)
            nodes = resp.items
        except ApiException:
            msg = "Error getting all nodes"
            logger.warning(msg, exc_info=True)
        return nodes
