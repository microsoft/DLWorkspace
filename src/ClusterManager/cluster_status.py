#!/usr/bin/env python3

import copy
import sys
import os
import json
import logging
import requests

sys.path.append(os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "../utils"))

from resource_stat import dictionarize, Gpu, Cpu, Memory


logger = logging.getLogger(__name__)


def str2bool(s):
    return s.lower() in ["true", "1", "t", "y", "yes"]


class ClusterInfo(object):
    def __init__(self):
        self.gpu_capacity = Gpu()
        self.gpu_used = Gpu()
        self.gpu_preemptable_used = Gpu()
        self.gpu_available = Gpu()
        self.gpu_unschedulable = Gpu()
        self.gpu_reserved = Gpu()

        self.cpu_capacity = Cpu()
        self.cpu_used = Cpu()
        self.cpu_preemptable_used = Cpu()
        self.cpu_available = Cpu()
        self.cpu_unschedulable = Cpu()
        self.cpu_reserved = Cpu()

        self.memory_capacity = Memory()
        self.memory_used = Memory()
        self.memory_preemptable_used = Memory()
        self.memory_available = Memory()
        self.memory_unschedulable = Memory()
        self.memory_reserved = Memory()

        self.node_status = None
        self.pod_status = None
        self.user_status = None
        self.user_status_preemptable = None

        self.available_job_num = 0

    def to_dict(self):
        return dictionarize(copy.deepcopy(self.__dict__))


class ClusterStatus(object):
    def __init__(self, prometheus_node, nodes, pods, jobs=None):
        self.prometheus_node = prometheus_node
        self.nodes = nodes
        self.pods = pods
        self.jobs = jobs

        self.node_statuses = None
        self.pod_statuses = None
        self.user_info = None
        self.user_info_preemptable = None

        self.cluster = ClusterInfo()

    def to_dict(self):
        return dictionarize(copy.deepcopy(self.cluster.to_dict()))

    def compute(self):
        """Compute the cluster status"""
        # Generate cluster information on nodes, pods, and users
        self.__gen_node_statuses()
        self.__gen_pod_statuses()
        self.__update_node_statuses()
        self.__gen_user_info()

        # Generate GPU cluster status
        self.__gen_cluster_gpu_status()

        # Generate CPU cluster status
        self.__gen_cluster_cpu_status()

        # Generate memory cluster status
        self.__gen_cluster_memory_status()

        # Generate cluster node status
        self.__gen_cluster_node_status()

        # Generate cluster pod status
        self.__gen_cluster_pod_status()

        # Generate cluster user status
        self.__gen_cluster_user_status()

        # Generate available job number
        self.__gen_available_job_num()

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

    def __gen_node_statuses(self):
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
                    gpu_allocatable = Gpu({sku: gpu_num})
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
                    gpu_capacity = Gpu({sku: gpu_num})
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

    def __gen_pod_statuses(self):
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
            node_selector = pod.spec.node_selector
            node_name = pod.spec.node_name

            gpu_type = ""
            job_id = None
            vc_name = None
            if labels is not None:
                gpu_type = labels.get("gpuType", "")
                job_id = labels.get("jobId")
                vc_name = labels.get("vcName")

            sku = ""
            if node_selector is not None:
                sku = node_selector.get("sku", "")

            if sku == "" and node_name is not None:
                node = self.node_statuses.get(node_name, {})
                node_labels = node.get("labels")
                if node_labels is not None:
                    sku = node_labels.get("sku", "")

            username = None
            if labels is not None and "userName" in labels:
                username = labels.get("userName")

            preemption_allowed = False
            if labels is not None and "preemptionAllowed" in labels:
                preemption_allowed = str2bool(labels["preemptionAllowed"])

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
            memory = Memory()
            preemptable_memory = Memory()

            containers = pod.spec.containers
            if containers is not None:
                for container in containers:
                    # container is of class
                    # 'kubernetes.client.models.v1_container.V1Container'
                    curr_container_gpus = 0
                    container_gpus = Gpu()
                    container_cpus = Cpu()
                    container_memory = Memory()
                    # resources is of class
                    # 'kubernetes.client.models.v1_resource_requirements
                    # .V1ResourceRequirements'
                    resources = container.resources
                    r_requests = {}
                    if resources.requests is not None:
                        r_requests = resources.requests

                    if gpu_str in r_requests:
                        curr_container_gpus = int(r_requests[gpu_str])
                        container_gpus = Gpu({sku: curr_container_gpus})

                    if cpu_str in r_requests:
                        container_cpus = Cpu({sku: r_requests[cpu_str]})

                    if mem_str in r_requests:
                        container_memory = Memory({sku: r_requests[mem_str]})

                    if preemption_allowed:
                        preemptable_gpus += container_gpus
                        preemptable_cpus += container_cpus
                        preemptable_memory += container_memory
                    else:
                        gpus += container_gpus
                        cpus += container_cpus
                        memory += container_memory

                    pod_name += " (gpu #:%s)" % curr_container_gpus

            pod_status = {
                "pod_name": pod_name,
                "job_id": job_id,
                "vc_name": vc_name,
                "namespace": namespace,
                "node_name": node_name,
                "username": username,
                "preemption_allowed": preemption_allowed,
                "gpus": gpus,
                "preemptable_gpus": preemptable_gpus,
                "cpus": cpus,
                "preemptable_cpus": preemptable_cpus,
                "memory": memory,
                "preemptable_memory": preemptable_memory,
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
            pod_memory = pod_status["memory"]
            pod_preemptable_memory = pod_status["preemptable_memory"]

            if node_name not in self.node_statuses:
                continue

            # NOTE gpu_used may include those unallocatable gpus
            node_status = self.node_statuses[node_name]
            node_status["gpu_used"] += pod_gpus
            node_status["gpu_preemptable_used"] += pod_preemptable_gpus
            node_status["cpu_used"] += pod_cpus
            node_status["cpu_preemptable_used"] += pod_preemptable_cpus
            node_status["memory_used"] += pod_memory
            node_status["memory_preemptable_used"] += pod_preemptable_memory

            # Only append a list pods in default namespace
            if namespace == "default":
                node_status["pods"].append(pod_name)

    def __gen_user_info(self):
        u_info = {}
        u_info_preemptable = {}

        for _, pod_status in self.pod_statuses.items():
            username = pod_status["username"]
            gpus = pod_status["gpus"]
            preemptable_gpus = pod_status["preemptable_gpus"]
            cpus = pod_status["cpus"]
            preemptable_cpus = pod_status["preemptable_cpus"]
            memory = pod_status["memory"]
            preemptable_memory = pod_status["preemptable_memory"]
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
                u_info[username]["memory"] += memory

                u_info_preemptable[username]["gpu"] += preemptable_gpus
                u_info_preemptable[username]["cpu"] += preemptable_cpus
                u_info_preemptable[username]["memory"] += preemptable_memory

        self.user_info = u_info
        self.user_info_preemptable = u_info_preemptable

    def __gen_cluster_resource_status(self, r_type):
        capacity = r_type()
        used = r_type()
        preemptable_used = r_type()
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
            node_preemptable_used = node_status[r_name + "_preemptable_used"]
            node_allocatable = node_status[r_name + "_allocatable"]
            if node_status["unschedulable"]:
                unschedulable += node_capacity
                reserved += (node_capacity - node_used)
            else:
                # gpu_used may larger than allocatable: used one GPU that has
                # uncorrectable errors
                avail += (node_allocatable - node_used)
                unschedulable += (node_capacity - node_allocatable)
                reserved += (node_capacity - node_allocatable)
            used += node_used
            preemptable_used += node_preemptable_used
            capacity += node_capacity

        logger.info("Cluster %s status: capacity %s, used %s, "
                    "preemptable used %s, avail %s, "
                    "unschedulable %s, reserved %s",
                    r_name, capacity, used,
                    preemptable_used, avail,
                    unschedulable, reserved)

        cluster = self.cluster
        cluster.__dict__[r_name + "_capacity"] = capacity
        cluster.__dict__[r_name + "_used"] = used
        cluster.__dict__[r_name + "_preemptable_used"] = preemptable_used
        cluster.__dict__[r_name + "_available"] = avail
        cluster.__dict__[r_name + "_unschedulable"] = unschedulable
        cluster.__dict__[r_name + "_reserved"] = reserved

    def __gen_cluster_gpu_status(self):
        self.__gen_cluster_resource_status(Gpu)

    def __gen_cluster_cpu_status(self):
        self.__gen_cluster_resource_status(Cpu)

    def __gen_cluster_memory_status(self):
        self.__gen_cluster_resource_status(Memory)

    def __gen_cluster_node_status(self):
        self.cluster.node_status = [
            node_status for _, node_status in self.node_statuses.items()
        ]

    def __gen_cluster_pod_status(self):
        self.cluster.pod_status = [
            pod_status for _, pod_status in self.pod_statuses.items()
        ]

    def __gen_cluster_user_status(self):
        self.cluster.user_status = [
            {
                "userName": username,
                "userGPU": u_info["gpu"],
                "userCPU": u_info["cpu"],
                "userMemory": u_info["memory"]
            } for username, u_info in self.user_info.items()
        ]

        self.cluster.user_status_preemptable = [
            {
                "userName": username,
                "userGPU": u_info["gpu"],
                "userCPU": u_info["cpu"],
                "userMemory": u_info["memory"]
            } for username, u_info in self.user_info_preemptable.items()
        ]

    def __gen_available_job_num(self):
        if isinstance(self.jobs, list):
            self.available_job_num = len(self.jobs)
        else:
            self.available_job_num = 0
