#!/usr/bin/env python3

import logging
import os
import sys

from cluster_status import ClusterStatus

sys.path.append(os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "../utils"))

from resource_stat import dictionarize, Cpu, Memory, Gpu
from cluster_resource import ClusterResource
from quota import calculate_vc_resources

logger = logging.getLogger(__name__)


class VirtualClusterView(object):
    def __init__(self, cluster_status, vc_info):
        self.__cluster_status = cluster_status
        self.__vc_info = vc_info

        self.vc = {
            vc_name: {
                "gpu_capacity": Gpu(),
                "cpu_capacity": Cpu(),
                "memory_capacity": Memory(),

                "available_job_num": 0
            }
            for vc_name in vc_info
        }

        self.gpu_capacity = None
        self.gpu_used = None
        self.gpu_preemptable_used = None
        self.gpu_available = None
        self.gpu_unschedulable = None

        self.cpu_capacity = None
        self.cpu_used = None
        self.cpu_preemptable_used = None
        self.cpu_available = None
        self.cpu_unschedulable = None

        self.memory_capacity = None
        self.memory_used = None
        self.memory_preemptable_used = None
        self.memory_available = None
        self.memory_unschedulable = None

        self.user_status = None
        self.user_status_preemptable = None

        self.available_job_num = None

    def to_dict(self):
        d = {
            k: v
            for k, v in self.__dict__.items()
            if not k.startswith("__")
        }
        return dictionarize(d)

    def compute(self):
        self.__compute_used_resource()

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

        self.__set_gpu_status(metric_map)
        self.__set_cpu_status(metric_map)
        self.__set_memory_status(metric_map)

    def __compute_used_resource(self):
        pass

    def __vc_accounting(self):
        cluster_status = self.__cluster_status
        cluster_capacity = ClusterResource(
            params={
                "cpu": cluster_status.cpu_capacity,
                "memory": cluster_status.memory_capacity,
                "gpu": cluster_status.gpu_capacity,
            }
        )
        cluster_available = ClusterResource(
            params={
                "cpu": cluster_status.cpu_available,
                "memory": cluster_status.memory_available,
                "gpu": cluster_status.gpu_available,
            }
        )
        cluster_reserved = ClusterResource(
            params={
                "cpu": cluster_status.cpu_reserved,
                "memory": cluster_status.memory_reserved,
                "gpu": cluster_status.gpu_reserved,
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
            for k in self.__vc_info
        }

        return calculate_vc_resources(cluster_capacity,
                                      cluster_available,
                                      cluster_reserved,
                                      self.__vc_info,
                                      vc_usage)

    def __set_resource_status(self, r_type, metric_map):
        for metric, vc_resource in metric_map.items():
            self.__dict__["%s_%s" % (r_type, metric)] = {
                vc_name: res.__dict__[r_type].floor
                for vc_name, res in vc_resource.items()
            }

    def __set_gpu_status(self, metric_map):
        self.__set_resource_status("gpu", metric_map)

    def __set_cpu_status(self, metric_map):
        self.__set_resource_status("cpu", metric_map)

    def __set_memory_status(self, metric_map):
        self.__set_resource_status("memory", metric_map)

    def __set_user_status(self):
        pass

    def __set_available_job_num(self):
        pass