#!/usr/bin/env python3

import collections
import json
import logging
import os
import sys

sys.path.append(os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "../utils"))

from resource_stat import Cpu, Memory, Gpu
from cluster_resource import ClusterResource
from cluster_status import ClusterStatus
from job_params_util import get_resource_params_from_job_params
from quota import calculate_vc_resources

logger = logging.getLogger(__name__)


def get_vc_info(vc_list):
    vc_info = {}
    for vc in vc_list:
        resource_quota = {}
        try:
            resource_quota = json.loads(vc["resourceQuota"])
        except:
            logger.exception("Parsing resourceQuota failed for %s", vc,
                             exc_info=True)
        vc_info[vc["vcName"]] = ClusterResource(params=resource_quota)
    return vc_info


class VirtualClusterStatus(ClusterStatus):
    def __init__(self, vc_name, vc_metrics_map, vc_jobs_without_pods,
                 node_statuses, pod_statuses, jobs):
        self.vc_name = vc_name
        self.vc_metrics_map = vc_metrics_map
        self.vc_jobs_without_pods = vc_jobs_without_pods

        super(VirtualClusterStatus, self).__init__(
            node_statuses, pod_statuses, jobs)

        self.exclusion.append("vc_metrics_map")
        self.exclusion.append("vc_jobs_without_pods")

    def gen_user_statuses(self):
        super(VirtualClusterStatus, self).gen_user_statuses()

        vc_name = self.vc_name
        jobs_without_pods = self.vc_jobs_without_pods.get(vc_name, [])
        for job in jobs_without_pods:
            username = job["userName"].split("@")[0].strip()
            job_res_params = get_resource_params_from_job_params(job)
            job_res = ClusterResource(params=job_res_params)

            if not job["preemptionAllowed"]:
                self.user_statuses[username]["gpu"] += job_res.gpu
                self.user_statuses[username]["cpu"] += job_res.cpu
                self.user_statuses[username]["memory"] += job_res.memory
            else:
                self.user_statuses_preemptable[username]["gpu"] += job_res.gpu
                self.user_statuses_preemptable[username]["cpu"] += job_res.cpu
                self.user_statuses_preemptable[username]["memory"] += \
                    job_res.memory
            logger.info("Added job %s resource %s to the usage of user %s in "
                        "vc %s", job, job_res, username, vc_name)

    def gen_resource_status(self):
        for r_type in ["cpu", "memory", "gpu"]:
            for metric, vc_metrics in self.vc_metrics_map.items():
                vc_metric = vc_metrics.get(self.vc_name)
                if vc_metric is None:
                    continue

                self.__dict__["%s_%s" % (r_type, metric)] = \
                    vc_metric.__dict__[r_type]


class VirtualClusterStatusesFactory(object):
    def __init__(self, cluster_status, vc_list):
        self.cluster_status = cluster_status
        self.vc_info = get_vc_info(vc_list)

    def make(self):
        try:
            vc_node_statuses = self.__get_vc_node_statuses()
            vc_pod_statuses = self.__get_vc_pod_statuses()
            vc_jobs = self.__get_vc_jobs()
            vc_jobs_without_pods = self.__get_vc_jobs_without_pods(
                vc_jobs, vc_pod_statuses)
            vc_metrics_map = self.__get_vc_metrics_map(
                vc_pod_statuses, vc_jobs_without_pods)

            vc_statuses = {
                vc_name: VirtualClusterStatus(
                    vc_name,
                    vc_metrics_map,
                    vc_jobs_without_pods,
                    vc_node_statuses,
                    vc_pod_statuses,
                    vc_jobs
                ) for vc_name in self.vc_info
            }
        except:
            logger.exception("Failed to make vc status", exc_info=True)
            vc_statuses = None

        return vc_statuses

    def __get_vc_node_statuses(self):
        node_statuses = self.cluster_status.node_statuses
        vc_node_statuses = {
            vc_name: node_statuses for vc_name in self.vc_info
        }
        return vc_node_statuses

    def __get_vc_pod_statuses(self):
        pod_statuses = self.cluster_status.pod_statuses
        vc_pod_statuses = {}
        for vc_name in self.vc_info:
            vc_pod_statuses[vc_name] = {
                name: pod_status
                for name, pod_status in pod_statuses.items()
                if pod_status.get("vc_name") == vc_name
            }
        return vc_pod_statuses

    def __get_vc_jobs(self):
        jobs = self.cluster_status.jobs
        vc_jobs = {}
        for vc_name in self.vc_info:
            vc_jobs[vc_name] = [
                job for job in jobs if job.get("vcName") == vc_name
            ]
        return vc_jobs

    def __get_vc_jobs_without_pods(self, vc_jobs, vc_pod_statuses):
        vc_jobs_without_pods = collections.defaultdict(lambda: list())
        for vc_name in self.vc_info:
            jobs = vc_jobs.get(vc_name, [])
            pod_statuses = vc_pod_statuses.get(vc_name, {})

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

                vc_jobs_without_pods[vc_name].append(job)

        return vc_jobs_without_pods

    def __get_vc_metrics_map(self, vc_pod_statuses, vc_jobs_without_pods):
        capacity, avail, reserved = self.__get_cluster_status()
        vc_used, vc_preemptable_used = self.__get_vc_used(
            vc_pod_statuses, vc_jobs_without_pods)

        vc_capacity, vc_used, vc_avail, vc_unschedulable = \
            calculate_vc_resources(capacity, avail, reserved, self.vc_info,
                                   vc_used)

        vc_metrics_map = {
            "capacity": vc_capacity,
            "used": vc_used,
            "preemptable_used": vc_preemptable_used,
            "available": vc_avail,
            "unschedulable": vc_unschedulable,
            # reserved is set to unschedulable for vc
            "reserved": vc_unschedulable,
        }

        return vc_metrics_map

    def __get_vc_used(self, vc_pod_statuses, vc_jobs_without_pods):
        vc_used = collections.defaultdict(lambda: ClusterResource())
        vc_preemptable_used = collections.defaultdict(lambda: ClusterResource())

        for vc_name in self.vc_info:
            # Account all pods in vc
            pod_statuses = vc_pod_statuses.get(vc_name, {})

            for _, pod_status in pod_statuses.items():
                pod_res = ClusterResource(params={
                    "cpu": pod_status.get("cpu", Cpu()).to_dict(),
                    "memory": pod_status.get("memory", Memory()).to_dict(),
                    "gpu": pod_status.get("gpu", Gpu()).to_dict(),
                })
                vc_used[vc_name] += pod_res

                pod_preemptable_res = ClusterResource(params={
                    "preemptable_cpu":
                        pod_status.get("preemptable_cpu", Cpu()).to_dict(),
                    "preemptable_memory":
                        pod_status.get("preemptable_memory", Memory()).to_dict(),
                    "preemptable_gpu":
                        pod_status.get("preemptable_gpu", Gpu()).to_dict(),
                })
                vc_preemptable_used[vc_name] += pod_preemptable_res

            # Account all jobs without pods in vc
            jobs_without_pods = vc_jobs_without_pods.get(vc_name, [])
            for job in jobs_without_pods:
                job_res_params = get_resource_params_from_job_params(job)
                job_res = ClusterResource(params=job_res_params)

                vc_name = job["vcName"]
                if not job["preemptionAllowed"]:
                    vc_used[vc_name] += job_res
                else:
                    vc_preemptable_used[vc_name] += job_res
                logger.info("Added job %s resource %s to the usage of vc %s",
                            job, job_res, vc_name)

        return vc_used, vc_preemptable_used

    def __get_cluster_status(self):
        cluster = self.cluster_status
        capacity = ClusterResource(
            params={
                "cpu": cluster.cpu_capacity,
                "memory": cluster.memory_capacity,
                "gpu": cluster.gpu_capacity,
            }
        )
        avail = ClusterResource(
            params={
                "cpu": cluster.cpu_available,
                "memory": cluster.memory_available,
                "gpu": cluster.gpu_available,
            }
        )
        reserved = ClusterResource(
            params={
                "cpu": cluster.cpu_reserved,
                "memory": cluster.memory_reserved,
                "gpu": cluster.gpu_reserved,
            }
        )
        return capacity, avail, reserved
