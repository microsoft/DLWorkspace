#!/usr/bin/env python3

import sys
import os
import pycurl
import json
import logging

sys.path.append(os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "../utils"))

from io import StringIO
from resource_stat import Gpu


logger = logging.getLogger(__name__)


def str2bool(s):
    return s.lower() in ["true", "1", "t", "y", "yes"]


class ClusterStatus(object):
    def __init__(self, config, nodes, pods):
        self.prometheus_node = config.get("prometheus_node", "127.0.0.1")
        self.nodes = nodes
        self.pods = pods

        self.node_statuses = None
        self.pod_statuses = None
        self.user_info = None
        self.user_info_preemptable = None

        self.dict_exclusion = [
            "prometheus_node",
            "nodes",
            "pods",
            "user_info",
            "user_info_preemptable"
        ]

        self.gpu_capacity = None
        self.gpu_used = None
        self.gpu_available = None
        self.gpu_unschedulable = None
        self.gpu_reserved = None

        self.node_status = None
        self.user_status = None
        self.user_status_preemptable = None

    def compute(self):
        """Compute the cluster status

        Returns:
            A dictionary representing cluster status.
        """
        # Retrieve cluster information on nodes, pods, and users
        self.get_node_statuses()
        self.get_pod_statuses()
        self.update_node_statuses()
        self.get_user_info()

        # Compute GPU cluster status
        self.compute_cluster_gpu_status()

        # TODO: Compute CPU cluster status

        # TODO: Compute memory cluster status

        # Compute cluster node status
        self.compute_cluster_node_status()

        # Compute cluster user status
        self.compute_cluster_user_status()

    def to_dict(self):
        """Returns a dictionary representing the properties of ClusterStatus"""
        return {
            k: v
            for k, v in self.__dict__.items()
            if k not in self.dict_exclusion
        }

    def get_job_gpu_usage(self, job_id):
        try:
            hostaddress = self.prometheus_node

            url = """http://"""+hostaddress+""":9091/prometheus/api/v1/query?query=avg%28avg_over_time%28task_gpu_percent%7Bpod_name%3D%22""" + \
                  job_id + """%22%7D%5B4h%5D%29%29+by+%28pod_name%2C+instance%2C+username%29"""

            curl = pycurl.Curl()
            curl.setopt(pycurl.URL, url)
            curl.setopt(pycurl.SSL_VERIFYPEER, 1)
            curl.setopt(pycurl.SSL_VERIFYHOST, 0)
            curl.setopt(curl.FOLLOWLOCATION, True)
            buff = StringIO()
            curl.setopt(pycurl.WRITEFUNCTION, buff.write)
            curl.perform()
            response = buff.getvalue()
            curl.close()
            gpu_usage = int(float(json.loads(response)["data"]["result"][0]["value"][1]))

        except Exception:
            logger.exception("Failed to get gpu usage for job id %s", job_id)
            gpu_usage = None

        return gpu_usage

    def get_node_statuses(self):
        """Selects specific fields from Kubernetes node information.

        Returns:
            A dictionary of nodes with selected fields.
        """
        gpu_str = "nvidia.com/gpu"

        self.node_statuses = {}

        for node in self.nodes:
            # node is of class 'kubernetes.client.models.v1_node.V1Node'
            name = node.metadata.name
            labels = node.metadata.labels

            gpu_type = ""
            scheduled_service = []
            if labels is not None:
                for label, status in labels.items():
                    if status == "active" and label not in ["all", "default"]:
                        scheduled_service.append(label)
                    if label == "gpuType":
                        scheduled_service.append(status)
                        gpu_type = status

            allocatable = node.status.allocatable
            gpu_allocatable = Gpu()
            if allocatable is not None and gpu_str in allocatable:
                gpu_num = int(allocatable[gpu_str])
                gpu_allocatable = Gpu({gpu_type: gpu_num})

            capacity = node.status.capacity
            gpu_capacity = Gpu()
            if capacity is not None and gpu_str in capacity:
                gpu_num = int(capacity[gpu_str])
                gpu_capacity = Gpu({gpu_type: gpu_num})

            internal_ip = "unknown"

            addresses = node.status.addresses
            if addresses is not None:
                for addr in addresses:
                    # addr is of class
                    # 'kubernetes.client.models.v1_node_address.V1NodeAddress'
                    if addr.type == "InternalIP":
                        internal_ip = addr.address

            unschedulable = node.spec.unschedulable
            if unschedulable is not None and unschedulable is True:
                unschedulable = True
            else:
                unschedulable = False

            conditions = node.status.conditions
            if conditions is not None:
                for cond in conditions:
                    # cond is of class
                    # 'kubernetes.client.models.v1_node_condition
                    # .V1NodeCondition'
                    if cond.type == "Ready" and cond.status != "True":
                        unschedulable = True

            node_status = {
                "name": name,
                "labels": labels,
                "gpuType": gpu_type,
                "scheduled_service": scheduled_service,
                "gpu_allocatable": gpu_allocatable,
                "gpu_capacity": gpu_capacity,
                "gpu_used": Gpu(),
                "gpu_preemptable_used": Gpu(),
                "InternalIP": internal_ip,
                "pods": [],
                "unschedulable": unschedulable
            }

            self.node_statuses[name] = node_status

        return self.node_statuses

    def get_pod_statuses(self):
        """Selects specific fields from Kubernetes pods information.

        Returns:
            A dictionary of pods with selected fields.
        """
        gpu_str = "nvidia.com/gpu"

        self.pod_statuses = {}
        for pod in self.pods:
            # pod is of class 'kubernetes.client.models.v1_pod.V1Pod'
            phase = pod.status.phase
            if phase in ["Succeeded", "Failed"]:
                continue

            name = pod.metadata.name
            labels = pod.metadata.labels

            gpu_type = ""
            if labels is not None:
                for label, status in labels.items():
                    if label == "gpuType":
                        gpu_type = status

            gpus = 0
            preemptable_gpus = 0

            username = None
            if labels is not None and "userName" in labels:
                username = labels.get("userName")

            preemption_allowed = False
            if labels is not None and "preemptionAllowed" in labels:
                preemption_allowed = str2bool(labels["preemptionAllowed"])

            node_name = pod.spec.node_name
            pod_name = name
            if username is not None:
                pod_name += " : " + username

            gpu_usage = self.get_job_gpu_usage(name)
            if gpu_usage is not None:
                pod_name += " (gpu usage:%s%%)" % gpu_usage
                if gpu_usage <= 25:
                    pod_name += "!!!!!!"

            containers = pod.spec.containers
            if containers is not None:
                for container in containers:
                    # container is of class
                    # 'kubernetes.client.models.v1_container.V1Container'
                    container_gpus = 0
                    # resources is of class
                    # 'kubernetes.client.models.v1_resource_requirements
                    # .V1ResourceRequirements'
                    resources = container.resources
                    requests = {}
                    if resources.requests is not None:
                        requests = resources.requests

                    if gpu_str in requests:
                        container_gpus = int(requests[gpu_str])

                    if preemption_allowed:
                        preemptable_gpus += container_gpus
                    else:
                        gpus += container_gpus

                    pod_name += " (gpu #:%s)" % container_gpus

            pod_status = {
                "pod_name": pod_name,
                "node_name": node_name,
                "username": username,
                "gpus": Gpu({gpu_type: gpus}),
                "preemptable_gpus": Gpu({gpu_type: preemptable_gpus}),
                "gpuType": gpu_type
            }
            self.pod_statuses[name] = pod_status

        return self.pod_statuses

    def update_node_statuses(self):
        for _, pod_status in self.pod_statuses.items():
            pod_name = pod_status["pod_name"]
            node_name = pod_status["node_name"]
            pod_gpus = pod_status["gpus"]
            pod_preemptable_gpus = pod_status["preemptable_gpus"]

            if node_name not in self.node_statuses:
                continue

            # NOTE gpu_used may include those unallocatable gpus
            node_status = self.node_statuses[node_name]
            node_status["gpu_used"] += pod_gpus
            node_status["gpu_preemptable_used"] += pod_preemptable_gpus
            node_status["pods"].append(pod_name)

    def get_user_info(self):
        u_info = {}
        u_info_preemptable = {}

        for _, pod_status in self.pod_statuses.items():
            username = pod_status["username"]
            gpus = pod_status["gpus"]
            preemptable_gpus = pod_status["preemptable_gpus"]
            if username is not None:
                if username not in u_info:
                    u_info[username] = Gpu()
                    u_info_preemptable[username] = Gpu()
                u_info[username] += gpus
                u_info_preemptable[username] += preemptable_gpus

        self.user_info = u_info
        self.user_info_preemptable = u_info_preemptable

    def compute_cluster_gpu_status(self):
        capacity = Gpu()
        used = Gpu()
        avail = Gpu()
        unschedulable = Gpu()
        reserved = Gpu()

        for node_name, node_status in self.node_statuses.items():
            node_capacity = node_status["gpu_capacity"]
            node_used = node_status["gpu_used"]
            node_allocatable = node_status["gpu_allocatable"]
            if node_status["unschedulable"]:
                unschedulable += node_capacity
                reserved += (node_capacity - node_used)
            else:
                # gpu_used may larger than allocatable: used one GPU that has
                # uncorrectable errors
                avail += (node_allocatable - node_used).min_zero()
                unschedulable += (node_capacity - node_allocatable)
                reserved += (node_capacity - node_allocatable)
            used += node_used
            capacity += node_capacity

        logger.info("Cluster GPU status: capacity %s, used %s, avail %s, "
                    "unschedulable %s, reserved %s",
                    capacity, used, avail, unschedulable, reserved)

        self.gpu_capacity = capacity.resource
        self.gpu_used = used.resource
        self.gpu_available = avail.resource
        self.gpu_unschedulable = unschedulable.resource
        self.gpu_reserved = reserved.resource

    def compute_cluster_node_status(self):
        for _, node_status in self.node_statuses.items():
            gpu_capacity = node_status["gpu_capacity"].resource
            gpu_used = node_status["gpu_used"].resource
            gpu_preemptable_used = node_status["gpu_preemptable_used"].resource
            gpu_allocatable = node_status["gpu_allocatable"].resource

            node_status["gpu_capacity"] = gpu_capacity
            node_status["gpu_used"] = gpu_used
            node_status["gpu_preemptable_used"] = gpu_preemptable_used
            node_status["gpu_allocatable"] = gpu_allocatable

        return [node_status for _, node_status in self.node_statuses.items()]

    def compute_cluster_user_status(self):
        self.user_status = [
            {
                "userName": username,
                "userGPU": user_gpu.resource
            } for username, user_gpu in self.user_info.items()
        ]

        self.user_status_preemptable = [
            {
                "userName": username,
                "userGPU": user_gpu.resource
            } for username, user_gpu in self.user_info_preemptable.items()
        ]
