#!/usr/bin/env python3

import sys
import os
import json
import logging
import requests

sys.path.append(os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "../utils"))

from resource_stat import Gpu, Cpu, Memory


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
            "node_statuses",
            "pod_statuses",
            "user_info",
            "user_info_preemptable",
            "dict_exclusion"
        ]

        self.gpu_capacity = None
        self.gpu_used = None
        self.gpu_available = None
        self.gpu_unschedulable = None
        self.gpu_reserved = None

        self.cpu_capacity = None
        self.cpu_used = None
        self.cpu_available = None
        self.cpu_unschedulable = None
        self.cpu_reserved = None

        self.memory_capacity = None
        self.memory_used = None
        self.memory_available = None
        self.memory_unschedulable = None
        self.memory_reserved = None

        self.node_status = None
        self.user_status = None
        self.user_status_preemptable = None

    def compute(self):
        """Compute the cluster status

        Returns:
            A dictionary representing cluster status.
        """
        # Retrieve cluster information on nodes, pods, and users
        self.__parse_node_statuses()
        self.__parse_pod_statuses()
        self.__update_node_statuses()
        self.__parse_user_info()

        # Compute GPU cluster status
        self.__set_cluster_gpu_status()

        # Compute CPU cluster status
        self.__set_cluster_cpu_status()

        # Compute memory cluster status
        self.__set_cluster_memory_status()

        # Compute cluster node status
        self.__set_cluster_node_status()

        # Compute cluster user status
        self.__set_cluster_user_status()

    def to_dict(self):
        """Returns a dictionary representing the properties of ClusterStatus"""
        return {
            k: v
            for k, v in self.__dict__.items()
            if k not in self.dict_exclusion
        }

    def __job_gpu_usage(self, job_id):
        try:
            hostaddress = self.prometheus_node

            url = """http://"""+hostaddress+""":9091/prometheus/api/v1/query?query=avg%28avg_over_time%28task_gpu_percent%7Bpod_name%3D%22""" + \
                  job_id + """%22%7D%5B4h%5D%29%29+by+%28pod_name%2C+instance%2C+username%29"""

            resp = requests.get(url)
            result = json.loads(resp.text)
            gpu_usage = int(float(result["data"]["result"][0]["value"][1]))

        except Exception:
            logger.debug("Failed to get gpu usage for job id %s", job_id)
            gpu_usage = None

        return gpu_usage

    def __parse_node_statuses(self):
        gpu_str = "nvidia.com/gpu"
        cpu_str = "cpu"
        mem_str = "memory"

        self.node_statuses = {}

        for node in self.nodes:
            # node is of class 'kubernetes.client.models.v1_node.V1Node'
            if node.metadata is None:
                continue

            if node.spec is None:
                continue

            if node.status is None:
                continue

            name = node.metadata.name
            labels = node.metadata.labels

            gpu_type = ""
            sku = ""
            scheduled_service = []
            if labels is not None:
                for label, status in labels.items():
                    if status == "active" and label not in ["all", "default"]:
                        scheduled_service.append(label)
                    if label == "gpuType":
                        scheduled_service.append(status)
                        gpu_type = status
                    if label == "sku":
                        scheduled_service.append(status)
                        sku = status

            if node.status is None:
                continue

            allocatable = node.status.allocatable
            gpu_allocatable = Gpu()
            cpu_allocatable = Cpu()
            mem_allocatable = Memory()
            if allocatable is not None:
                if gpu_str in allocatable:
                    gpu_num = int(allocatable[gpu_str])
                    gpu_allocatable = Gpu({gpu_type: gpu_num})
                if cpu_str in allocatable:
                    cpu_num = allocatable[cpu_str]
                    cpu_allocatable = Cpu({sku: cpu_num})
                if mem_str in allocatable:
                    mem_num = allocatable[mem_str]
                    mem_allocatable = Memory({sku: mem_num})

            capacity = node.status.capacity
            gpu_capacity = Gpu()
            cpu_capacity = Cpu()
            mem_capacity = Memory()
            if capacity is not None:
                if gpu_str in capacity:
                    gpu_num = int(capacity[gpu_str])
                    gpu_capacity = Gpu({gpu_type: gpu_num})
                if cpu_str in capacity:
                    cpu_num = capacity[cpu_str]
                    cpu_capacity = Cpu({sku: cpu_num})
                if mem_str in capacity:
                    mem_num = capacity[mem_str]
                    mem_capacity = Memory({sku: mem_num})

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
                "cpu_allocatable": cpu_allocatable,
                "cpu_capacity": cpu_capacity,
                "cpu_used": Cpu(),
                "cpu_preemptable_used": Cpu(),
                "memory_allocatable": mem_allocatable,
                "memory_capacity": mem_capacity,
                "memory_used": Memory(),
                "memory_preemptable_used": Memory(),
                "InternalIP": internal_ip,
                "pods": [],
                "unschedulable": unschedulable
            }

            self.node_statuses[name] = node_status

    def __parse_pod_statuses(self):
        gpu_str = "nvidia.com/gpu"
        cpu_str = "cpu"
        mem_str = "memory"

        self.pod_statuses = {}
        for pod in self.pods:
            # pod is of class 'kubernetes.client.models.v1_pod.V1Pod'
            if pod.metadata is None:
                continue

            if pod.status is None:
                continue

            phase = pod.status.phase
            if phase in ["Succeeded", "Failed"]:
                continue

            if pod.spec is None:
                continue

            name = pod.metadata.name
            namespace = pod.metadata.namespace
            labels = pod.metadata.labels

            gpu_type = ""
            sku = ""
            if labels is not None:
                for label, status in labels.items():
                    if label == "gpuType":
                        gpu_type = status
                    if label == "sku":
                        sku = status

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

            gpu_usage = self.__job_gpu_usage(name)
            if gpu_usage is not None:
                pod_name += " (gpu usage:%s%%)" % gpu_usage
                if gpu_usage <= 25:
                    pod_name += "!!!!!!"

            gpus = Gpu()
            preemptable_gpus = Gpu()
            cpus = Cpu()
            preemptable_cpus = Cpu()
            mems = Memory()
            preemptable_mems = Memory()

            containers = pod.spec.containers
            if containers is not None:
                for container in containers:
                    # container is of class
                    # 'kubernetes.client.models.v1_container.V1Container'
                    curr_container_gpus = 0
                    container_gpus = Gpu()
                    container_cpus = Cpu()
                    container_mems = Memory()
                    # resources is of class
                    # 'kubernetes.client.models.v1_resource_requirements
                    # .V1ResourceRequirements'
                    resources = container.resources
                    r_requests = {}
                    if resources.requests is not None:
                        r_requests = resources.requests

                    if gpu_str in r_requests:
                        curr_container_gpus = int(r_requests[gpu_str])
                        container_gpus = Gpu({gpu_type: curr_container_gpus})

                    if cpu_str in r_requests:
                        container_cpus = Cpu({sku: r_requests[cpu_str]})

                    if mem_str in r_requests:
                        container_mems = Memory({sku: r_requests[mem_str]})

                    if preemption_allowed:
                        preemptable_gpus += container_gpus
                        preemptable_cpus += container_cpus
                        preemptable_mems += container_mems
                    else:
                        gpus += container_gpus
                        cpus += container_cpus
                        mems += container_mems

                    pod_name += " (gpu #:%s)" % curr_container_gpus

            pod_status = {
                "pod_name": pod_name,
                "namespace": namespace,
                "node_name": node_name,
                "username": username,
                "gpus": gpus.prune(),
                "preemptable_gpus": preemptable_gpus.prune(),
                "cpus": cpus.prune(),
                "preemptable_cpus": preemptable_cpus.prune(),
                "mems": mems.prune(),
                "preemptable_mems": preemptable_mems.prune(),
                "gpuType": gpu_type
            }
            self.pod_statuses[name] = pod_status

    def __update_node_statuses(self):
        for _, pod_status in self.pod_statuses.items():
            pod_name = pod_status["pod_name"]
            namespace = pod_status["namespace"]
            node_name = pod_status["node_name"]
            pod_gpus = pod_status["gpus"]
            pod_preemptable_gpus = pod_status["preemptable_gpus"]
            pod_cpus = pod_status["cpus"]
            pod_preemptable_cpus = pod_status["preemptable_cpus"]
            pod_mems = pod_status["mems"]
            pod_preemptable_mems = pod_status["preemptable_mems"]

            if node_name not in self.node_statuses:
                continue

            # NOTE gpu_used may include those unallocatable gpus
            node_status = self.node_statuses[node_name]
            node_status["gpu_used"] += pod_gpus
            node_status["gpu_preemptable_used"] += pod_preemptable_gpus
            node_status["cpu_used"] += pod_cpus
            node_status["cpu_preemptable_used"] += pod_preemptable_cpus
            node_status["memory_used"] += pod_mems
            node_status["memory_preemptable_used"] += pod_preemptable_mems

            # Only append a list pods in default namespace
            if namespace == "default":
                node_status["pods"].append(pod_name)

    def __parse_user_info(self):
        u_info = {}
        u_info_preemptable = {}

        for _, pod_status in self.pod_statuses.items():
            username = pod_status["username"]
            gpus = pod_status["gpus"]
            preemptable_gpus = pod_status["preemptable_gpus"]
            cpus = pod_status["cpus"]
            preemptable_cpus = pod_status["preemptable_cpus"]
            mems = pod_status["mems"]
            preemptable_mems = pod_status["preemptable_mems"]
            if username is not None:
                if username not in u_info:
                    u_info[username] = {
                        "gpu": Gpu(),
                        "cpu": Cpu(),
                        "memory": Memory()
                    }
                    u_info_preemptable[username] = {
                        "gpu": Gpu(),
                        "cpu": Cpu(),
                        "memory": Memory()
                    }

                u_info[username]["gpu"] += gpus
                u_info[username]["cpu"] += cpus
                u_info[username]["memory"] += mems

                u_info_preemptable[username]["gpu"] += preemptable_gpus
                u_info_preemptable[username]["cpu"] += preemptable_cpus
                u_info_preemptable[username]["memory"] += preemptable_mems

        self.user_info = u_info
        self.user_info_preemptable = u_info_preemptable

    def __set_cluster_resource_status(self, r_type):
        capacity = r_type()
        used = r_type()
        avail = r_type()
        unschedulable = r_type()
        reserved = r_type()

        r_name = r_type.__name__.lower()

        for node_name, node_status in self.node_statuses.items():
            # Only do accounting for nodes with label "worker=active"
            active_worker = node_status["labels"].get("worker") == "active"
            if not active_worker:
                continue

            node_capacity = node_status[r_name + "_capacity"]
            node_used = node_status[r_name + "_used"]
            node_allocatable = node_status[r_name + "_allocatable"]
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

        capacity.prune()
        used.prune()
        avail.prune()
        unschedulable.prune()
        reserved.prune()

        logger.info("Cluster %s status: capacity %s, used %s, avail %s, "
                    "unschedulable %s, reserved %s", r_name,
                    capacity, used, avail, unschedulable, reserved)
        return capacity, used, avail, unschedulable, reserved

    def __set_cluster_gpu_status(self):
        capacity, used, avail, unschedulable, reserved = \
            self.__set_cluster_resource_status(Gpu)

        self.gpu_capacity = capacity.resource_int
        self.gpu_used = used.resource_int
        self.gpu_available = avail.resource_int
        self.gpu_unschedulable = unschedulable.resource_int
        self.gpu_reserved = reserved.resource_int

    def __set_cluster_cpu_status(self):
        capacity, used, avail, unschedulable, reserved = \
            self.__set_cluster_resource_status(Cpu)

        self.cpu_capacity = capacity.resource_int
        self.cpu_used = used.resource_int
        self.cpu_available = avail.resource_int
        self.cpu_unschedulable = unschedulable.resource_int
        self.cpu_reserved = reserved.resource_int

    def __set_cluster_memory_status(self):
        capacity, used, avail, unschedulable, reserved = \
            self.__set_cluster_resource_status(Memory)

        self.memory_capacity = capacity.resource_int
        self.memory_used = used.resource_int
        self.memory_available = avail.resource_int
        self.memory_unschedulable = unschedulable.resource_int
        self.memory_reserved = reserved.resource_int

    def __set_cluster_node_status(self):
        for _, node_status in self.node_statuses.items():
            for r_type in ["gpu", "cpu", "memory"]:
                k_capacity = r_type + "_capacity"
                k_used = r_type + "_used"
                k_preemptable_used = r_type + "_preemptable_used"
                k_allocatable = r_type + "_allocatable"

                capacity = node_status[k_capacity].resource_int
                used = node_status[k_used].resource_int
                preemptable_used = node_status[k_preemptable_used].resource_int
                allocatable = node_status[k_allocatable].resource_int

                node_status[k_capacity] = capacity
                node_status[k_used] = used
                node_status[k_preemptable_used] = preemptable_used
                node_status[k_allocatable] = allocatable

        self.node_status = [
            node_status for _, node_status in self.node_statuses.items()
        ]

    def __set_cluster_user_status(self):
        self.user_status = [
            {
                "userName": username,
                "userGPU": u_info["gpu"].resource_int,
                "userCPU": u_info["cpu"].resource_int,
                "userMemory": u_info["memory"].resource_int
            } for username, u_info in self.user_info.items()
        ]

        self.user_status_preemptable = [
            {
                "userName": username,
                "userGPU": u_info["gpu"].resource_int,
                "userCPU": u_info["cpu"].resource_int,
                "userMemory": u_info["memory"].resource_int
            } for username, u_info in self.user_info_preemptable.items()
        ]
