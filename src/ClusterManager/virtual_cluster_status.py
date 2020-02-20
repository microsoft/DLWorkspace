#!/usr/bin/env python3

import base64
import collections
import json
import logging
import os
import sys

from cluster_status import ClusterStatus

sys.path.append(os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "../utils"))

from resource_stat import dictionarize, Cpu, Memory, Gpu
from cluster_resource import ClusterResource
from cluster_status import ClusterInfo
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
            logger.exception("Parsing resourceQuota failed for %s",
                             vc,
                             exc_info=True)
        vc_info[vc["vcName"]] = ClusterResource(params=resource_quota)

    return vc_info


class VirtualClusterStatus(object):
    def __init__(self, cluster_status, vc_list, jobs):
        self.cluster_status = cluster_status
        self.vc_info = get_vc_info(vc_list)
        self.jobs = jobs

        self.virtual_cluster = {
            vc_name: ClusterInfo()
            for vc_name in self.vc_info
        }

    def to_dict(self):
        ret = {
            # ClusterInfo.to_dict() calls dictionarize()
            vc_name: cluster_info.to_dict()
            for vc_name, cluster_info in self.virtual_cluster
        }
        return ret

    def compute(self):
        self.__gen_used_resource()

        (
            vc_total,
            vc_used,
            vc_avail,
            vc_unschedulable
        ) = self.__vc_accounting()

        metric_map = {
            "capacity": vc_total,
            "used": vc_used,
            "available": vc_avail,
            "unschedulable": vc_unschedulable,
        }

        self.__gen_gpu_status(metric_map)
        self.__gen_cpu_status(metric_map)
        self.__gen_memory_status(metric_map)

    def __get_vc_usage(self):
        def base64decode(s):
            return base64.b64decode(s.encode("utf-8")).decode("utf-8")

        vc_used = collections.defaultdict(lambda: ClusterResource())
        vc_preemptable_used = collections.defaultdict(lambda: ClusterResource())

        pod_statuses = self.cluster_status.pod_statuses
        node_statuses = self.cluster_status.node_statuses

        # Account all pods on workers
        job_id_to_pods = collections.defaultdict(lambda: list())
        for _, pod_status in pod_statuses.items():
            vc_name = pod_status.get("vc_name")
            if vc_name is None:
                logger.debug("Skip pod %s. Not in vc %s", pod_status, vc_name)
                continue

            node_name = pod_status.get("node_name")
            if node_name is None:
                logger.warning("Skip pod %s in vc %s. node_name is None.",
                               pod_status,
                               vc_name)
                continue

            node_status = node_statuses.get(node_name)
            if node_status is None:
                logger.warning("Skip pod %s in vc %s. node_name %s. "
                               "node_status is None",
                               pod_status,
                               vc_name,
                               node_name)
                continue

            active_worker = node_status.get("labels").get("worker") == "active"
            if not active_worker:
                logger.debug("Skip pod %s in vc %s. node_name %s. "
                             "node_status %s. Not worker node.",
                             pod_status,
                             vc_name,
                             node_name,
                             node_status)
                continue

            pod_res = ClusterResource(
                params={
                    "cpu": pod_status.get("cpu", Cpu()).to_dict(),
                    "memory": pod_status.get("memory", Memory()).to_dict(),
                    "gpu": pod_status.get("gpu", Gpu()).to_dict(),
                }
            )

            vc_used[vc_name] += pod_res

            pod_preemptable_res = ClusterResource(
                params={
                    "preemptable_cpu":
                        pod_status.get("preemptable_cpu", Cpu()).to_dict(),
                    "preemptable_memory":
                        pod_status.get("preemptable_memory", Memory()).to_dict(),
                    "preemptable_gpu":
                        pod_status.get("preemptable_gpu", Gpu()).to_dict(),
                }
            )

            vc_preemptable_used[vc_name] += pod_preemptable_res

            job_id = pod_status.get("job_id")
            if job_id is not None:
                job_id_to_pods[job_id].append(pod_status)

        for job in self.jobs:
            job_params = json.loads(base64decode(job["jobParams"]))

            job_id = job_params.get("jobId")
            if job_id is None:
                logger.warning("Skip job %s", job_id)
                continue

            if job_id in job_id_to_pods:
                logger.debug("Job %s is accounted in k8s pods", job_id)
                continue

            job_res = get_resource_params_from_job_params(job_params)
            vc_used[job["vcName"]] += ClusterResource(params=job_res)
            logger.info("Added job %s resource to vc usage", job_id)

        return vc_used, vc_preemptable_used

    def __vc_accounting(self):
        cluster = self.cluster_status.cluster
        cluster_capacity = ClusterResource(
            params={
                "cpu": cluster.cpu_capacity,
                "memory": cluster.memory_capacity,
                "gpu": cluster.gpu_capacity,
            }
        )
        cluster_available = ClusterResource(
            params={
                "cpu": cluster.cpu_available,
                "memory": cluster.memory_available,
                "gpu": cluster.gpu_available,
            }
        )
        cluster_reserved = ClusterResource(
            params={
                "cpu": cluster.cpu_reserved,
                "memory": cluster.memory_reserved,
                "gpu": cluster.gpu_reserved,
            }
        )

        vc_usage = {
            k: ClusterResource(
                params={
                    "cpu": self.cpu_used,
                    "memory": self.memory_used,
                    "gpu": self.gpu_used,
                }
            )
            for k in self.vc_info
        }

        return calculate_vc_resources(cluster_capacity,
                                      cluster_available,
                                      cluster_reserved,
                                      self.vc_info,
                                      vc_usage)

    def __gen_resource_status(self, r_type, metric_map):
        for metric, vc_resource in metric_map.items():
            self.__dict__["%s_%s" % (r_type, metric)] = {
                vc_name: res.__dict__[r_type]
                for vc_name, res in vc_resource.items()
            }

    def __gen_gpu_status(self, metric_map):
        self.__gen_resource_status("gpu", metric_map)

    def __gen_cpu_status(self, metric_map):
        self.__gen_resource_status("cpu", metric_map)

    def __gen_memory_status(self, metric_map):
        self.__gen_resource_status("memory", metric_map)

    def __set_user_status(self):
        pass

    def __set_available_job_num(self):
        pass