#!/usr/bin/env python3

import urllib.parse
import argparse
import requests
import yaml

PROMETHEUS_API_V1_QUERY = "/prometheus/api/v1/query"
PROMETHEUS_API_V1_QUERY_RANGE = "/prometheus/api/v1/query_range"


def mark(func):
    # Mark the metric candidates to be exposed on dashboard
    return func


def exist(func):
    # Mark the metrics that have been exposed on dashboard
    return func


class PrometheusMetric(object):
    def __init__(self, url):
        self.url = url

    def format_url_query(self, query):
        arg = urllib.parse.urlencode({"query": query})
        return urllib.parse.urljoin(self.url, PROMETHEUS_API_V1_QUERY) \
            + "?" + arg

    def get_response(self, query):
        return requests.get(self.format_url_query(query))

    def get_scalar(self, query):
        resp = self.get_response(query)
        return float(resp.json()["data"]["result"][0]["value"][1])

    def get_vector(self, query):
        resp = self.get_response(query)
        d = {}
        for result in resp.json()["data"]["result"]:
            key = list(result["metric"].values())[0]
            val = float(result["value"][1])
            d[key] = val
        return d

    # Cluster
    @mark
    def get_cluster_gpu_util(self):
        return self.get_scalar("avg(task_gpu_percent)")

    @exist
    def get_cluster_gpu_allocated(self):
        return self.get_scalar("count(task_gpu_percent)")

    @mark
    def get_cluster_gpu_usage(self):
        return self.get_scalar("sum(task_gpu_percent)")

    @mark
    def get_cluster_cpu_usage(self):
        return self.get_scalar("sum(task_cpu_percent)")

    @mark
    def get_cluster_memory_usage(self):
        return self.get_scalar("sum(task_mem_usage_byte)")

    # Node
    @mark
    def get_node_gpu_util(self):
        return self.get_vector("avg(task_gpu_percent) by (instance)")

    @exist
    def get_node_gpu_allocated(self):
        return self.get_vector("count(task_gpu_percent) by (instance)")

    @mark
    def get_node_gpu_usage(self):
        return self.get_vector("sum(task_gpu_percent) by (instance)")

    @mark
    def get_node_cpu_usage(self):
        return self.get_vector("sum(task_cpu_percent) by (instance)")

    @mark
    def get_node_memory_usage(self):
        return self.get_vector("sum(task_mem_usage_byte) by (instance)")

    # VC
    @mark
    def get_vc_gpu_util(self):
        return self.get_vector("avg(task_gpu_percent) by (vc_name)")

    @exist
    def get_vc_gpu_allocated(self):
        return self.get_vector("count(task_gpu_percent) by (vc_name)")

    @mark
    def get_vc_gpu_usage(self):
        return self.get_vector("sum(task_gpu_percent) by (vc_name)")

    @mark
    def get_vc_cpu_usage(self):
        return self.get_vector("sum(task_cpu_percent) by (vc_name)")

    @mark
    def get_vc_memory_usage(self):
        return self.get_vector("sum(task_mem_usage_byte) by (vc_name)")

    # User
    @mark
    def get_user_gpu_util(self):
        return self.get_vector("avg(task_gpu_percent) by (username)")

    @exist
    def get_user_gpu_allocated(self):
        return self.get_vector("count(task_gpu_percent) by (username)")

    @mark
    def get_user_gpu_usage(self):
        return self.get_vector("sum(task_gpu_percent) by (username)")

    @mark
    def get_user_cpu_usage(self):
        return self.get_vector("sum(task_cpu_percent) by (username)")

    @mark
    def get_user_memory_usage(self):
        return self.get_vector("sum(task_mem_usage_byte) by (username)")

    # Job
    @mark
    def get_job_gpu_util(self):
        return self.get_vector("avg(task_gpu_percent) by (job_name)")

    @exist
    def get_job_gpu_allocated(self):
        return self.get_vector("count(task_gpu_percent) by (job_name)")

    @mark
    def get_job_gpu_usage(self):
        return self.get_vector("sum(task_gpu_percent) by (job_name)")

    @mark
    def get_job_cpu_usage(self):
        return self.get_vector("sum(task_cpu_percent) by (job_name)")

    @mark
    def get_job_memory_usage(self):
        return self.get_scalar("sum(task_mem_usage_byte) by (job_name)")

    # Pod
    @mark
    def get_pod_gpu_util(self):
        return self.get_vector("avg(task_gpu_percent) by (pod_name)")

    @exist
    def get_pod_gpu_allocated(self):
        return self.get_vector("count(task_gpu_percent) by (pod_name)")

    @mark
    def get_pod_gpu_usage(self):
        return self.get_vector("sum(task_gpu_percent) by (pod_name)")

    @mark
    def get_pod_cpu_usage(self):
        return self.get_vector("sum(task_cpu_percent) by (pod_name)")

    @mark
    def get_pod_memory_usage(self):
        return self.get_vector("sum(task_mem_usage_byte) by (pod_name)")

    # Others
    @exist
    def get_cluster_gpu_total(self):
        return self.get_scalar("sum(k8s_node_gpu_total)")

    @exist
    def get_vc_gpu_total(self):
        return self.get_vector("sum(k8s_vc_gpu_total) by (vc_name)")


class Insighter(object):
    def __init__(self, url):
        metric = PrometheusMetric(url)

        self.cluster_gpu_util = metric.get_cluster_gpu_util()
        self.cluster_gpu_total = metric.get_cluster_gpu_total()
        self.cluster_gpu_allocated = metric.get_cluster_gpu_allocated()
        self.cluster_gpu_usage = metric.get_cluster_gpu_usage()
        self.cluster_cpu_usage = metric.get_cluster_cpu_usage()
        self.cluster_memory_usage = metric.get_cluster_memory_usage()

        self.vc_gpu_util = metric.get_vc_gpu_util()
        self.vc_gpu_total = metric.get_vc_gpu_total()
        self.vc_gpu_allocated = metric.get_vc_gpu_allocated()
        self.vc_gpu_usage = metric.get_vc_gpu_usage()
        self.vc_cpu_usage = metric.get_vc_cpu_usage()
        self.vc_memory_usage = metric.get_vc_memory_usage()

        self.node_gpu_util = metric.get_node_gpu_util()
        self.node_gpu_allocated = metric.get_node_gpu_allocated()
        self.node_gpu_usage = metric.get_node_gpu_usage()
        self.node_cpu_usage = metric.get_node_cpu_usage()
        self.node_memory_usage = metric.get_node_memory_usage()

        self.user_gpu_util = metric.get_user_gpu_util()
        self.user_gpu_allocated = metric.get_user_gpu_allocated()
        self.user_gpu_usage = metric.get_user_gpu_usage()
        self.user_cpu_usage = metric.get_user_cpu_usage()
        self.user_memory_usage = metric.get_user_memory_usage()

        self.job_gpu_util = metric.get_job_gpu_util()
        self.job_gpu_allocated = metric.get_job_gpu_allocated()
        self.job_gpu_usage = metric.get_job_gpu_usage()
        self.job_cpu_usage = metric.get_job_cpu_usage()
        self.job_memory_usage = metric.get_job_memory_usage()

        self.pod_gpu_util = metric.get_pod_gpu_util()
        self.pod_gpu_allocated = metric.get_pod_gpu_allocated()
        self.pod_gpu_usage = metric.get_pod_gpu_usage()
        self.pod_cpu_usage = metric.get_pod_cpu_usage()
        self.pod_memory_usage = metric.get_pod_memory_usage()

    def __repr__(self):
        return "%s" % yaml.dump(self.__dict__, default_flow_style=False)


def main(args):
    # Now
    r = Insighter(args.prometheus_url)
    print(r)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prometheus_url",
                        "-p",
                        default="http://127.0.0.1:9091",
                        help="Prometheus url, eg: http://127.0.0.1:9091")

    args = parser.parse_args()

    main(args)
