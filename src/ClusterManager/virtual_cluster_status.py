#!/usr/bin/env python3

import collections
import json
import logging
import os
import sys

sys.path.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../utils"))

from resource_stat import Cpu, Memory, Gpu
from cluster_resource import ClusterResource
from cluster_status import ClusterStatus, get_jobs_without_pods
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
            logger.exception("Parsing resourceQuota failed for %s", vc)
        vc_info[vc["vcName"]] = ClusterResource(params=resource_quota)
    return vc_info


class VirtualClusterStatus(ClusterStatus):
    def __init__(self, vc_name, vc_info, cluster_status, node_statuses,
                 vc_pod_statuses, vc_jobs):
        self.vc_name = vc_name
        self.vc_info = vc_info
        self.cluster_status = cluster_status
        self.vc_pod_statuses = vc_pod_statuses
        self.vc_jobs = vc_jobs
        self.vc_jobs_without_pods = collections.defaultdict(lambda: list())
        for _vc_name in self.vc_info:
            _vc_jobs = self.vc_jobs.get(_vc_name, [])
            _vc_pod_statuses = vc_pod_statuses.get(_vc_name, {})
            self.vc_jobs_without_pods[_vc_name] = get_jobs_without_pods(
                _vc_jobs, _vc_pod_statuses)

        pod_statuses = self.vc_pod_statuses.get(self.vc_name, {})
        jobs = self.vc_jobs.get(self.vc_name, [])
        super(VirtualClusterStatus, self).__init__(node_statuses, pod_statuses,
                                                   jobs)

        self.exclusion.append("cluster_status")
        self.exclusion.append("vc_info")
        self.exclusion.append("vc_pod_statuses")
        self.exclusion.append("vc_jobs")
        self.exclusion.append("vc_jobs_without_pods")
        # node_status is the same as the one in cluster_status
        self.exclusion.append("node_status")

    def gen_resource_status(self):
        vc_metrics_map = self.__get_vc_metrics_map()
        for r_type in ["cpu", "memory", "gpu"]:
            for metric, vc_metrics in vc_metrics_map.items():
                vc_metric = vc_metrics.get(self.vc_name)
                if vc_metric is None:
                    continue

                self.__dict__["%s_%s" % (r_type, metric)] = \
                    vc_metric.__dict__[r_type]

    def __get_vc_metrics_map(self):
        capacity, avail, reserved = self.__get_cluster_resource_count()
        vc_used, vc_preemptable_used = self.__get_vc_used(
            self.vc_pod_statuses, self.vc_jobs_without_pods)

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
                pod_res = ClusterResource(
                    params={
                        "cpu": pod_status.get("cpu", Cpu()).to_dict(),
                        "memory": pod_status.get("memory", Memory()).to_dict(),
                        "gpu": pod_status.get("gpu", Gpu()).to_dict(),
                    })
                vc_used[vc_name] += pod_res

                pod_preemptable_res = ClusterResource(
                    params={
                        "cpu":
                            pod_status.get("preemptable_cpu", Cpu()).to_dict(),
                        "memory":
                            pod_status.get("preemptable_memory", Memory()
                                          ).to_dict(),
                        "gpu":
                            pod_status.get("preemptable_gpu", Gpu()).to_dict(),
                    })
                vc_preemptable_used[vc_name] += pod_preemptable_res

            # Account all jobs without pods in vc
            jobs_without_pods = vc_jobs_without_pods.get(vc_name, [])
            for job in jobs_without_pods:
                job_params = job["jobParams"]
                job_res_params = get_resource_params_from_job_params(job_params)
                job_res = ClusterResource(params=job_res_params)

                preemption_allowed = job_params.get("preemptionAllowed", False)
                if not preemption_allowed:
                    vc_used[vc_name] += job_res
                else:
                    vc_preemptable_used[vc_name] += job_res
                logger.info("Added job %s resource %s to the usage of vc %s",
                            job, job_res, vc_name)

        return vc_used, vc_preemptable_used

    def __get_cluster_resource_count(self):
        cluster = self.cluster_status
        capacity = ClusterResource(
            params={
                "cpu": cluster.cpu_capacity,
                "memory": cluster.memory_capacity,
                "gpu": cluster.gpu_capacity,
            })
        avail = ClusterResource(
            params={
                "cpu": cluster.cpu_available,
                "memory": cluster.memory_available,
                "gpu": cluster.gpu_available,
            })
        reserved = ClusterResource(
            params={
                "cpu": cluster.cpu_reserved,
                "memory": cluster.memory_reserved,
                "gpu": cluster.gpu_reserved,
            })
        return capacity, avail, reserved


class VirtualClusterStatusesFactory(object):
    def __init__(self, cluster_status, vc_list):
        self.cluster_status = cluster_status
        self.vc_info = get_vc_info(vc_list)

    def make(self):
        try:
            vc_pod_statuses = self.__get_vc_pod_statuses()
            vc_jobs = self.__get_vc_jobs()

            vc_statuses = {
                vc_name:
                VirtualClusterStatus(vc_name, self.vc_info, self.cluster_status,
                                     self.cluster_status.node_statuses,
                                     vc_pod_statuses, vc_jobs)
                for vc_name in self.vc_info
            }
        except:
            logger.exception("Failed to make vc statuses")
            vc_statuses = None

        return vc_statuses

    def __get_vc_pod_statuses(self):
        pod_statuses = self.cluster_status.pod_statuses
        vc_pod_statuses = {vc_name: {} for vc_name in self.vc_info}
        for name, pod_status in pod_statuses.items():
            pod_vc = pod_status.get("vc_name")
            if pod_vc in self.vc_info:
                vc_pod_statuses[pod_vc][name] = pod_status
        return vc_pod_statuses

    def __get_vc_jobs(self):
        jobs = self.cluster_status.jobs
        vc_jobs = {vc_name: [] for vc_name in self.vc_info}
        for job in jobs:
            job_vc = job.get("vcName")
            if job_vc in self.vc_info:
                vc_jobs[job_vc].append(job)
        return vc_jobs
