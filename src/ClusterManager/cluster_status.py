#!/usr/bin/env python3

import copy
import sys
import os
import json
import logging
import requests

sys.path.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../utils"))

from resource_stat import dictionarize, Gpu, Cpu, Memory
from cluster_resource import ClusterResource
from job_params_util import get_resource_params_from_job_params
from common import base64decode

logger = logging.getLogger(__name__)


def override(func):
    return func


def str2bool(s):
    return s.lower() in ["true", "1", "t", "y", "yes"]


def get_jobs(job_list):
    jobs = []
    for job in job_list:
        job_params = job["jobParams"]
        if not isinstance(job_params, dict):
            job["jobParams"] = json.loads(base64decode(job_params))
        jobs.append(job)
    return jobs


def get_jobs_without_pods(jobs, pod_statuses):
    """This function is to find all the jobs which has entered 'scheduling'
    status in DLTS database, but k8s hasn't started to schedule them.
    We need to count these jobs for accurate available resource in cluster.
    """
    jobs_without_pods = []

    job_ids_with_pods = set()
    for _, pod_status in pod_statuses.items():
        job_id = pod_status.get("job_id")
        if job_id is not None:
            job_ids_with_pods.add(job_id)

    for job in jobs:
        job_id = job.get("jobId")
        if job_id is None:
            logger.warning("Skip job %s", job_id)
            continue

        if job_id in job_ids_with_pods:
            logger.debug("Job %s is accounted in k8s pods", job_id)
            continue

        jobs_without_pods.append(job)

    return jobs_without_pods


class ClusterStatus(object):
    def __init__(self, node_statuses, pod_statuses, jobs):
        self.node_status = None
        self.pod_status = None
        self.user_status = None
        self.user_status_preemptable = None
        self.available_job_num = None

        self.gpu_capacity = None
        self.gpu_used = None
        self.gpu_preemptable_used = None
        self.gpu_available = None
        self.gpu_unschedulable = None
        self.gpu_reserved = None

        self.cpu_capacity = None
        self.cpu_used = None
        self.cpu_preemptable_used = None
        self.cpu_available = None
        self.cpu_unschedulable = None
        self.cpu_reserved = None

        self.memory_capacity = None
        self.memory_used = None
        self.memory_preemptable_used = None
        self.memory_available = None
        self.memory_unschedulable = None
        self.memory_reserved = None

        # Not included in returning dict
        self.jobs = get_jobs(jobs)
        self.node_statuses = node_statuses
        self.pod_statuses = pod_statuses
        self.jobs_without_pods = None
        self.pods_without_node_assignment = None
        self.user_statuses = None
        self.user_statuses_preemptable = None

        self.exclusion = [
            "exclusion", # exclude self
            "jobs",
            "jobs_without_pods",
            "pods_without_node_assignment",
            "node_statuses",
            "pod_statuses",
            "user_statuses",
            "user_statuses_preemptable",
        ]

        self.compute()

    def to_dict(self):
        return dictionarize({
            k: v
            for k, v in copy.deepcopy(self.__dict__).items()
            if k not in self.exclusion
        })

    def compute(self):
        # Generate jobs without k8s pods
        self.gen_jobs_without_pods()

        # Generate pods without node assignment
        self.gen_pods_without_node_assignment()

        # Generate node_status list and pod_status list
        self.gen_node_status()
        self.gen_pod_status()

        # Generate user statuses
        self.gen_user_statuses()

        # Generate cluster resource status
        self.gen_resource_status()

        # Generate user_status list
        self.gen_user_status()

        # Generate active job count
        self.gen_available_job_num()

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            logger.debug("self class %s, other class %s", self.__class__,
                         other.__class__)
            return False

        for k in self.__dict__:
            if k in self.exclusion:
                continue

            self_val = self.__dict__[k]
            other_val = other.__dict__[k]
            if isinstance(self_val, list) and isinstance(other_val, list):
                for item in self_val:
                    if item not in other_val:
                        logger.debug("For %s: self %s, other %s", k,
                                     self.__dict__[k], other.__dict__[k])
                        return False
                for item in other_val:
                    if item not in self_val:
                        logger.debug("For %s: self %s, other %s", k,
                                     self.__dict__[k], other.__dict__[k])
                        return False
            elif self_val != other_val:
                logger.debug("For %s: self %s, other %s", k, self.__dict__[k],
                             other.__dict__[k])
                return False

        return True

    def gen_jobs_without_pods(self):
        self.jobs_without_pods = get_jobs_without_pods(self.jobs,
                                                       self.pod_statuses)

    def gen_pods_without_node_assignment(self):
        self.pods_without_node_assignment = {}
        for name, pod_status in self.pod_statuses.items():
            if pod_status["node_name"] is None:
                self.pods_without_node_assignment[name] = pod_status

    def gen_node_status(self):
        self.node_status = [
            node_status for _, node_status in self.node_statuses.items()
        ]

    def gen_pod_status(self):
        self.pod_status = [
            pod_status for _, pod_status in self.pod_statuses.items()
        ]

    def gen_user_statuses(self):
        user_statuses = {}
        user_statuses_preemptable = {}

        for _, pod_status in self.pod_statuses.items():
            username = pod_status["username"]
            gpu = pod_status["gpu"]
            preemptable_gpu = pod_status["preemptable_gpu"]
            cpu = pod_status["cpu"]
            preemptable_cpu = pod_status["preemptable_cpu"]
            memory = pod_status["memory"]
            preemptable_memory = pod_status["preemptable_memory"]
            if username is not None:
                if username not in user_statuses:
                    user_statuses[username] = {
                        "gpu": Gpu(),
                        "cpu": Cpu(),
                        "memory": Memory()
                    }
                if username not in user_statuses_preemptable:
                    user_statuses_preemptable[username] = {
                        "gpu": Gpu(),
                        "cpu": Cpu(),
                        "memory": Memory()
                    }

                user_statuses[username]["gpu"] += gpu
                user_statuses[username]["cpu"] += cpu
                user_statuses[username]["memory"] += memory

                user_statuses_preemptable[username]["gpu"] += preemptable_gpu
                user_statuses_preemptable[username]["cpu"] += preemptable_cpu
                user_statuses_preemptable[username]["memory"] += \
                    preemptable_memory

        self.user_statuses = user_statuses
        self.user_statuses_preemptable = user_statuses_preemptable

        self.__adjust_user_statuses()

    def __adjust_user_statuses(self):
        # Adjust with jobs that have not been scheduled on k8s.
        # Add to corresponding user usage
        for job in self.jobs_without_pods:
            job_params = job["jobParams"]
            job_res_params = get_resource_params_from_job_params(job_params)
            job_res = ClusterResource(params=job_res_params)
            username = job["userName"].split("@")[0].strip()

            if username not in self.user_statuses:
                self.user_statuses[username] = {
                    "gpu": Gpu(),
                    "cpu": Cpu(),
                    "memory": Memory()
                }
            if username not in self.user_statuses_preemptable:
                self.user_statuses_preemptable[username] = {
                    "gpu": Gpu(),
                    "cpu": Cpu(),
                    "memory": Memory()
                }

            preemption_allowed = job_params.get("preemptionAllowed", False)
            if not preemption_allowed:
                self.user_statuses[username]["gpu"] += job_res.gpu
                self.user_statuses[username]["cpu"] += job_res.cpu
                self.user_statuses[username]["memory"] += job_res.memory
                logger.info("Added job %s resource %s to used for user %s", job,
                            job_res, username)
            else:
                self.user_statuses_preemptable[username]["gpu"] += job_res.gpu
                self.user_statuses_preemptable[username]["cpu"] += job_res.cpu
                self.user_statuses_preemptable[username]["memory"] += \
                    job_res.memory
                logger.info(
                    "Added job %s resource %s to preemptable used for "
                    "user %s", job, job_res, username)

    @override
    def gen_resource_status(self):
        self.__gen_cpu_status()
        self.__gen_memory_status()
        self.__gen_gpu_status()
        self.__adjust_resource_status()

    def __adjust_resource_status(self):
        # Adjust with jobs that have not been scheduled on k8s.
        # Subtract from cluster available
        # Add to cluster used
        for job in self.jobs_without_pods:
            job_params = job["jobParams"]
            job_res_params = get_resource_params_from_job_params(job_params)
            job_res = ClusterResource(params=job_res_params)

            preemption_allowed = job_params.get("preemptionAllowed", False)
            if not preemption_allowed:
                self.gpu_available -= job_res.gpu
                self.cpu_available -= job_res.cpu
                self.memory_available -= job_res.memory

                self.gpu_used += job_res.gpu
                self.cpu_used += job_res.cpu
                self.memory_used += job_res.memory
                logger.info("Added job %s resource %s to used", job, job_res)
            else:
                self.gpu_preemptable_used += job_res.gpu
                self.cpu_preemptable_used += job_res.cpu
                self.memory_preemptable_used += job_res.memory
                logger.info("Added job %s resource %s to preemptable used", job,
                            job_res)

        # Account pods without node assignment.
        # This occurs when fragmentation happens and job manager still let
        # through jobs because there is still remaining quota.
        for name, pod_status in self.pods_without_node_assignment.items():
            if pod_status["preemption_allowed"] is False:
                self.gpu_used += pod_status["gpu"]
                self.cpu_used += pod_status["cpu"]
                self.memory_used += pod_status["memory"]

                self.gpu_available -= pod_status["gpu"]
                self.cpu_available -= pod_status["cpu"]
                self.memory_available -= pod_status["memory"]
            else:
                self.gpu_preemptable_used += pod_status["preemptable_gpu"]
                self.cpu_preemptable_used += pod_status["preemptable_cpu"]
                self.memory_preemptable_used += pod_status["preemptable_memory"]

    def gen_user_status(self):
        self.user_status = [{
            "userName": username,
            "userGPU": user_status["gpu"],
            "userCPU": user_status["cpu"],
            "userMemory": user_status["memory"]
        } for username, user_status in self.user_statuses.items()]

        self.user_status_preemptable = [{
            "userName": username,
            "userGPU": user_status["gpu"],
            "userCPU": user_status["cpu"],
            "userMemory": user_status["memory"]
        } for username, user_status in self.user_statuses_preemptable.items()]

    def gen_available_job_num(self):
        self.available_job_num = 0
        if isinstance(self.jobs, list):
            self.available_job_num = len(self.jobs)

    def __gen_r_type_status(self, r_type):
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

        logger.info(
            "Cluster %s status: capacity %s, used %s, "
            "preemptable used %s, avail %s, "
            "unschedulable %s, reserved %s", r_name, capacity, used,
            preemptable_used, avail, unschedulable, reserved)

        self.__dict__[r_name + "_capacity"] = capacity
        self.__dict__[r_name + "_used"] = used
        self.__dict__[r_name + "_preemptable_used"] = preemptable_used
        self.__dict__[r_name + "_available"] = avail
        self.__dict__[r_name + "_unschedulable"] = unschedulable
        self.__dict__[r_name + "_reserved"] = reserved

    def __gen_cpu_status(self):
        self.__gen_r_type_status(Cpu)

    def __gen_memory_status(self):
        self.__gen_r_type_status(Memory)

    def __gen_gpu_status(self):
        self.__gen_r_type_status(Gpu)


class ClusterStatusFactory(object):
    def __init__(self, prometheus_node, nodes, pods, jobs):
        self.prometheus_node = prometheus_node
        self.nodes = nodes
        self.pods = pods
        self.jobs = jobs

        self.node_statuses = None
        self.pod_statuses = None

        self.__gen_node_statuses()
        self.__gen_pod_statuses()
        self.__update_node_statuses()

    def make(self):
        try:
            cluster_status = ClusterStatus(self.node_statuses,
                                           self.pod_statuses, self.jobs)
        except:
            logger.exception("Failed to create cluster_status")
            cluster_status = None

        return cluster_status

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

            gpu = Gpu()
            preemptable_gpu = Gpu()
            cpu = Cpu()
            preemptable_cpu = Cpu()
            memory = Memory()
            preemptable_memory = Memory()

            containers = pod.spec.containers
            if containers is not None:
                for container in containers:
                    # container is of class
                    # 'kubernetes.client.models.v1_container.V1Container'
                    curr_container_gpu = 0
                    container_gpu = Gpu()
                    container_cpu = Cpu()
                    container_memory = Memory()
                    # resources is of class
                    # 'kubernetes.client.models.v1_resource_requirements
                    # .V1ResourceRequirements'
                    resources = container.resources
                    r_requests = {}
                    if resources.requests is not None:
                        r_requests = resources.requests

                    if gpu_str in r_requests:
                        curr_container_gpu = int(r_requests[gpu_str])
                        container_gpu = Gpu({sku: curr_container_gpu})

                    if cpu_str in r_requests:
                        container_cpu = Cpu({sku: r_requests[cpu_str]})

                    if mem_str in r_requests:
                        container_memory = Memory({sku: r_requests[mem_str]})

                    if preemption_allowed:
                        preemptable_gpu += container_gpu
                        preemptable_cpu += container_cpu
                        preemptable_memory += container_memory
                    else:
                        gpu += container_gpu
                        cpu += container_cpu
                        memory += container_memory

                    pod_name += " (gpu #:%s)" % curr_container_gpu

            pod_status = {
                "name": name,
                "pod_name": pod_name,
                "job_id": job_id,
                "vc_name": vc_name,
                "namespace": namespace,
                "node_name": node_name,
                "username": username,
                "preemption_allowed": preemption_allowed,
                "gpu": gpu,
                "preemptable_gpu": preemptable_gpu,
                "cpu": cpu,
                "preemptable_cpu": preemptable_cpu,
                "memory": memory,
                "preemptable_memory": preemptable_memory,
                "gpuType": gpu_type,
                "gpu_usage": gpu_usage,
            }
            self.pod_statuses[name] = pod_status

    def __update_node_statuses(self):
        for _, pod_status in self.pod_statuses.items():
            pod_name = pod_status["pod_name"]
            namespace = pod_status["namespace"]
            node_name = pod_status["node_name"]
            pod_gpu = pod_status["gpu"]
            pod_preemptable_gpu = pod_status["preemptable_gpu"]
            pod_cpu = pod_status["cpu"]
            pod_preemptable_cpu = pod_status["preemptable_cpu"]
            pod_memory = pod_status["memory"]
            pod_preemptable_memory = pod_status["preemptable_memory"]

            if node_name not in self.node_statuses:
                continue

            # NOTE gpu_used may include those unallocatable gpu
            node_status = self.node_statuses[node_name]
            node_status["gpu_used"] += pod_gpu
            node_status["gpu_preemptable_used"] += pod_preemptable_gpu
            node_status["cpu_used"] += pod_cpu
            node_status["cpu_preemptable_used"] += pod_preemptable_cpu
            node_status["memory_used"] += pod_memory
            node_status["memory_preemptable_used"] += pod_preemptable_memory

            # Only append a list pods in default namespace
            if namespace == "default":
                node_status["pods"].append(pod_name)

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
