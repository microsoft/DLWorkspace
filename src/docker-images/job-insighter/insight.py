#!/usr/bin/env python3

import argparse
import collections
import json
import logging
import re
import requests
import timeit
import urllib.parse

from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


G = 2**30


def to_byte(data):
    data = str(data).lower()
    number = float(re.findall(r"[-+]?[0-9]*[.]?[0-9]+", data)[0])
    if "ki" in data:
        return number * 2**10
    elif "mi" in data:
        return number * 2**20
    elif "gi" in data:
        return number * 2**30
    elif "ti" in data:
        return number * 2**40
    elif "pi" in data:
        return number * 2**50
    elif "ei" in data:
        return number * 2**60
    elif "k" in data:
        return number * 10**3
    elif "m" in data:
        return number * 10**6
    elif "g" in data:
        return number * 10**9
    elif "t" in data:
        return number * 10**12
    elif "p" in data:
        return number * 10**15
    elif "e" in data:
        return number * 10**18
    else:
        return number


def walk_json_field_safe(obj, *fields):
    """ for example a=[{"a": {"b": 2}}]
    walk_json_field_safe(a, 0, "a", "b") will get 2
    walk_json_field_safe(a, 0, "not_exist") will get None
    """
    try:
        for f in fields:
            obj = obj[f]
        return obj
    except:
        return None


def request_with_error_handling(url, timeout=180):
    try:
        response = requests.get(url, allow_redirects=True, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.exception(e)
        return None


def query_prometheus(prometheus_url, query, since, end, step):
    params = urllib.parse.urlencode({
        "query": query,
        "start": str(since),
        "end": str(end),
        "step": str(step),
    })

    url = urllib.parse.urljoin(prometheus_url,
                               "/prometheus/api/v1/query_range") + "?" + params

    start = timeit.default_timer()
    obj = request_with_error_handling(url)
    elapsed = timeit.default_timer() - start
    logger.info("requesting %s took %.2fs", url, elapsed)

    if walk_json_field_safe(obj, "status") != "success":
        logger.warning("requesting %s failed, body is %s", url, obj)
        return None

    return walk_json_field_safe(obj, "data", "result")


def get_task_gpu_percent(prometheus_url, since, end, step):
    return query_prometheus(
        prometheus_url, "avg(task_gpu_percent) by (job_name, uuid)",
        since, end, step)


def get_task_gpu_mem_percent(prometheus_url, since, end, step):
    return query_prometheus(
        prometheus_url, "avg(task_gpu_mem_percent) by (job_name, uuid)",
        since, end, step)


def get_task_cpu_percent(prometheus_url, since, end, step):
    return query_prometheus(
        prometheus_url, "avg(task_cpu_percent) by (job_name, pod_name)",
        since, end, step)


def get_task_mem_usage_byte(prometheus_url, since, end, step):
    return query_prometheus(
        prometheus_url, "avg(task_mem_usage_byte) by (job_name, pod_name)",
        since, end, step)


def get_vc_info(restful_url):
    params = urllib.parse.urlencode({
        "userName": "Administrator",
    })
    url = urllib.parse.urljoin(restful_url, "/ListVCs") + "?" + params
    obj = request_with_error_handling(url)
    return walk_json_field_safe(obj, "result")


def get_node_spec(vc_info):
    try:
        metadata = walk_json_field_safe(vc_info, 0, "resourceMetadata")
        meta = json.loads(metadata)

        # This is assuming that the cluster is homogeneous, i.e. only 1 type
        # of machine.
        gpu_meta = next(iter(meta["gpu"].values()))
        gpu_per_node = int(gpu_meta.get("per_node"))

        cpu_meta = next(iter(meta["cpu"].values()))
        cpu_per_node = float(cpu_meta.get("per_node"))
        cpu_schedulable_ratio = float(cpu_meta.get("schedulable_ratio", 1))
        max_cpu_per_gpu = cpu_per_node * cpu_schedulable_ratio / gpu_per_node

        mem_meta = next(iter(meta["memory"].values()))
        mem_per_node = to_byte(mem_meta["per_node"])
        mem_schedulable_ratio = float(mem_meta.get("schedulable_ratio", 1))
        max_memory_per_gpu = mem_per_node * mem_schedulable_ratio / gpu_per_node
    except:
        logger.exception("Failed to get max resource per gpu.")
        max_cpu_per_gpu = max_memory_per_gpu = None

    return {
        "max_cpu_per_gpu": max_cpu_per_gpu,
        "max_memory_per_gpu": max_memory_per_gpu
    }


def get_vc_running_job_ids(restful_url, vc_name):
    running_job_ids = []
    try:
        params = urllib.parse.urlencode({
            "userName": "Administrator",
            "vcName": vc_name,
            "jobOwner": "all",
            "num": 0,
        })
        url = urllib.parse.urljoin(restful_url, "/ListJobsV2") + "?" + params
        obj = request_with_error_handling(url)

        jobs = walk_json_field_safe(obj, "runningJobs")
        running_job_ids = [job.get("jobId") for job in jobs]
    except:
        logger.exception("Failed to get running job ids for vc %s.", vc_name)

    return running_job_ids


def get_running_job_ids(restful_url, vc_info):
    running_job_ids = []
    for vc in vc_info:
        vc_running_job_ids = \
            get_vc_running_job_ids(restful_url, vc.get("vcName"))
        running_job_ids.extend(vc_running_job_ids)
    return running_job_ids


def set_job_insight(restful_url, job_id, insight):
    params = urllib.parse.urlencode({
        "jobId": job_id,
        "userName": "Administrator",
    })
    url = urllib.parse.urljoin(restful_url, "/JobInsight") + "?" + params
    resp = requests.post(url, data=json.dumps(insight))
    return resp


def avg(ts):
    """Calculates the average of the timeseries.

    Args:
        ts: A timeseries list of [time, value].

    Returns:
        Average of the timeseries.
    """
    return sum([float(v[1]) for v in ts]) / len(ts)


def timespan(ts):
    """Calculates the time span of the timeseries.

    Args:
        ts: A timeseries list of [time, value].

    Returns:
        The time span of the timeseries.
    """
    return ts[-1][0] - ts[0][0]


class JobUtil(object):
    def __init__(self, job_id, utils, since, end):
        self.job_id = job_id
        self.since = since
        self.end = end

        # Calculate average usage
        self.gpu = {
            uuid: avg(ts) for uuid, ts in utils["gpu"].items()
        }
        self.gpu_memory = {
            uuid: avg(ts) for uuid, ts in utils["gpu_memory"].items()
        }
        self.cpu = {
            pod_name: avg(ts) / 100 for pod_name, ts in utils["cpu"].items()
        }
        self.memory = {
            pod_name: avg(ts) for pod_name, ts in utils["memory"].items()
        }

        # Compute time span
        timespans = [timespan(ts) for _, ts in utils["gpu"].items()]
        timespans.extend(
            [timespan(ts) for _, ts in utils["gpu_memory"].items()])
        timespans.extend([timespan(ts) for _, ts in utils["cpu"].items()])
        timespans.extend([timespan(ts) for _, ts in utils["memory"].items()])
        self.timespan = min(timespans)

    def __repr__(self):
        return str(self.__dict__)


class Insight(object):
    def __init__(self, job_util, node_spec):
        self.job_id = job_util.job_id
        self.since = job_util.since
        self.end = job_util.end

        # Resource usage pattern from job_util
        self.job_timespan = job_util.timespan
        self.num_gpus = len(job_util.gpu)
        self.idle_gpus = sorted([u for u, v in job_util.gpu.items() if v == 0])
        self.active_gpus = sorted([u for u, v in job_util.gpu.items() if v > 0])

        self.active_gpu_util = 0
        self.active_gpu_memory_util = 0
        self.cpu_per_active_gpu = 0
        self.memory_per_active_gpu = 0

        n = len(self.active_gpus)
        if n > 0:
            self.active_gpu_util = \
                sum([job_util.gpu[u] for u in self.active_gpus]) / n
            self.active_gpu_memory_util = \
                sum([job_util.gpu_memory[u] for u in self.active_gpus]) / n
            self.cpu_per_active_gpu = \
                sum([v for _, v in job_util.cpu.items()]) / n
            self.memory_per_active_gpu = \
                sum([v for _, v in job_util.memory.items()]) / n

        # Maximum CPU and memory per GPU based on node_spec
        self.max_cpu_per_gpu = node_spec.get("max_cpu_per_gpu")
        self.max_memory_per_gpu = node_spec.get("max_memory_per_gpu")

        # Generate insight messages
        self.messages = []
        self.gen_messages()

    def export(self):
        return {
            "since": self.since,
            "end": self.end,
            "job_timespan": self.job_timespan,
            "num_gpus": self.num_gpus,
            "num_idle_gpus": len(self.idle_gpus),
            "num_active_gpus": len(self.active_gpus),
            "avg_active_gpu_util": self.active_gpu_util,
            "avg_active_gpu_memory_util": self.active_gpu_memory_util,
            "avg_cpu_per_active_gpu": self.cpu_per_active_gpu,
            "avg_memory_per_active_gpu": self.memory_per_active_gpu,
            "max_cpu_per_gpu": self.max_cpu_per_gpu,
            "max_memory_per_gpu": self.max_memory_per_gpu,
            "messages": self.messages,
        }

    def gen_messages(self):
        if self.job_timespan < 600:
            self.messages.append("Insight will be available when more metric "
                                 "samples are collected for the job.")
            return

        # Check idleness
        if len(self.idle_gpus) == self.num_gpus:
            self.messages.append(
                "All of %s GPU(s) in the job are idle. Please consider killing "
                "the job if you do not need it any more." % len(self.idle_gpus))
            return
        elif len(self.idle_gpus) > 0:
            self.messages.append(
                "There are %s idle GPU(s) in the job. If you are running a "
                "job on all GPUs, please check if your job is hanging. If you "
                "do not need all GPUs in the job, please consider killing the "
                "job and request a new job with smaller number of GPUs." %
                len(self.idle_gpus))
        else:
            self.messages.append("All GPU(s) are active.")

        # Check Resource usage for active GPUs
        good_gpu_util_threshold = 90
        good_gpu_mem_util_threshold = 50
        if self.active_gpu_util >= good_gpu_util_threshold:
            self.messages.append("Average active GPU utilization "
                                 "is good at %.2f%%." % self.active_gpu_util)
        else:
            self.messages.append(
                "Average active GPU utilization is below "
                "%s%%. You can take below suggestions to potentially "
                "boost GPU utilization." % good_gpu_util_threshold)

            messages = []
            if self.active_gpu_memory_util < good_gpu_mem_util_threshold:
                messages.append(
                    "Average active GPU memory utilization is below "
                    "%s%%. Try increasing batch size to put more data "
                    "onto GPU memory to boost GPU utilization. For a "
                    "distributed job, if the model has strict "
                    "requirement on the global effective batch size "
                    "for convergence, you can consider using a job "
                    "with fewer GPUs and bigger batch size per GPU."
                    % good_gpu_mem_util_threshold)

            if self.max_cpu_per_gpu is not None and \
                    self.cpu_per_active_gpu < self.max_cpu_per_gpu:
                messages.append(
                    "The job uses %.2f CPU cores per active GPU on "
                    "average. The maximum CPU cores per GPU you can "
                    "use without interfering with other GPUs in this "
                    "cluster is %.2f. You can use more CPU cores to "
                    "perform data preprocessing to keep GPUs from "
                    "starvation. Please consider using/increasing "
                    "parallel preprocessing on your input data." %
                    (self.cpu_per_active_gpu, self.max_cpu_per_gpu)
                )

            if self.max_memory_per_gpu is not None and \
                    self.memory_per_active_gpu < self.max_memory_per_gpu:
                messages.append(
                    "The job uses %.2fG memory per active GPU on "
                    "average. The maximum memory per GPU you can "
                    "use without interfering with other GPUs in this "
                    "cluster is %.2fG. You can preload more input "
                    "data into memory to make sure your data pipeline "
                    "is never waiting on data loading from "
                    "disk/remote." % (self.memory_per_active_gpu / G,
                                      self.max_memory_per_gpu / G)
                )

            messages.append(
                "Please take a closer look at METRICS tab to "
                "understand the utilization pattern of GPU, GPU "
                "memory, CPU and memory throughout time. You can "
                "try further optimization based on the "
                "utilization pattern of different resources. "
                "It could also be possible that storage read "
                "throughput is a bottleneck."
            )

            self.messages.append(messages)


def get_job_utils(task_gpu_percent, task_gpu_mem_percent, task_cpu_percent,
                  task_mem_usage_byte, since, end):
    """Parse metric lists and constructs a list of JobUtil.

    Args:
        task_gpu_percent: A list of all task_gpu_percent
        task_gpu_mem_percent: A list of all task_gpu_mem_percent
        task_cpu_percent: A list of all task_cpu_percent
        task_mem_usage_byte: A list of all task_mem_usage_byte
        start: Start time in epoch seconds
        end: End time in epoch seconds

    Returns:
        A list of JobUtil
    """
    job_utils = []

    jobs = collections.defaultdict(
        lambda: collections.defaultdict(
            lambda: collections.defaultdict()))

    for item in task_gpu_percent:
        metric = item["metric"]
        job_id = metric["job_name"]
        uuid = metric["uuid"]
        jobs[job_id]["gpu"][uuid] = item["values"]

    for item in task_gpu_mem_percent:
        metric = item["metric"]
        job_id = metric["job_name"]
        if job_id in jobs:  # Only collect metric for jobs in task_gpu_percent
            uuid = metric["uuid"]
            jobs[job_id]["gpu_memory"][uuid] = item["values"]

    for item in task_cpu_percent:
        metric = item["metric"]
        job_id = metric["job_name"]
        if job_id in jobs:  # Only collect metric for jobs in task_gpu_percent
            pod_name = metric["pod_name"]
            jobs[job_id]["cpu"][pod_name] = item["values"]

    for item in task_mem_usage_byte:
        metric = item["metric"]
        job_id = metric["job_name"]
        if job_id in jobs:  # Only collect metric for jobs in task_gpu_percent
            pod_name = metric["pod_name"]
            jobs[job_id]["memory"][pod_name] = item["values"]

    for job_id, utils in jobs.items():
        try:
            job_utils.append(JobUtil(job_id, utils, since, end))
        except:
            logger.exception("failed to create JobUtil: %s, %s", job_id, utils)

    return job_utils


def upload_insights(insights, restful_url, dry_run):
    for insight in insights:
        job_id = insight.job_id
        try:
            job_insight = insight.export()
            if dry_run:
                logger.info("dry run. logging insight for job %s: %s", job_id,
                            job_insight)
                continue

            resp = set_job_insight(restful_url, job_id, job_insight)
            if resp.status_code != 200:
                logger.error("failed to upload insight for job %s. %s", job_id,
                             resp.text)
            else:
                logger.info("successfully uploaded insight for job %s", job_id)
        except:
            logger.exception("failed to upload insight for %s", job_id)


def gen_insights(task_gpu_percent, task_gpu_mem_percent, task_cpu_percent,
                 task_mem_usage_byte, since, end, node_spec, running_job_ids):
    job_utils = get_job_utils(task_gpu_percent, task_gpu_mem_percent,
                              task_cpu_percent, task_mem_usage_byte, since, end)

    insights = []
    for job_util in job_utils:
        # Only generate insight for currently running jobs.
        if job_util.job_id not in running_job_ids:
            logger.info("skip generating non-running job %s", job_util.job_id)
            continue

        try:
            insights.append(Insight(job_util, node_spec))
        except:
            logger.exception("failed to generate insight from %s", job_util)

    return insights


def run(prometheus_url, hours_ago, restful_url, dry_run):
    now = datetime.now()
    since = int(datetime.timestamp(now - timedelta(hours=hours_ago)))
    end = int(datetime.timestamp(now))
    step = "1m"

    task_gpu_percent = get_task_gpu_percent(prometheus_url, since, end, step)
    if task_gpu_percent is None:
        logger.error("task_gpu_percent is None, skipping ...")
        return

    task_gpu_mem_percent = get_task_gpu_mem_percent(prometheus_url, since, end,
                                                    step)
    if task_gpu_mem_percent is None:
        logger.error("task_gpu_mem_percent is None, skipping ...")
        return

    task_cpu_percent = get_task_cpu_percent(prometheus_url, since, end, step)
    if task_cpu_percent is None:
        logger.error("task_cpu_percent is None, skipping ...")
        return

    task_mem_usage_byte = get_task_mem_usage_byte(prometheus_url, since, end,
                                                  step)
    if task_mem_usage_byte is None:
        logger.error("task_mem_usage_byte is None, skipping ...")
        return

    vc_info = get_vc_info(restful_url)
    node_spec = get_node_spec(vc_info)
    running_job_ids = get_running_job_ids(restful_url, vc_info)

    insights = gen_insights(task_gpu_percent, task_gpu_mem_percent,
                            task_cpu_percent, task_mem_usage_byte, since, end,
                            node_spec, running_job_ids)
    upload_insights(insights, restful_url, dry_run)


def main(params):
    try:
        run(params.prometheus_url, params.hours_ago, params.restful_url,
            params.dry_run)
    except:
        logger.exception("failed in current run of job insight")


if __name__ == "__main__":
    logging.basicConfig(
        format=
        "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s - %(message)s",
        level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--prometheus_url",
                        "-p",
                        required=True,
                        help="Prometheus url, eg: http://localhost:9091")
    parser.add_argument("--hours_ago",
                        "-a",
                        default=1,
                        type=int,
                        help="Collect metrics since hours ago. Default: 1")
    parser.add_argument("--restful_url",
                        "-r",
                        required=True,
                        help="Restful API url, e.g. http://localhost:5000")
    parser.add_argument("--dry_run",
                        "-d",
                        action="store_true",
                        help="Do not write to database if specified")

    args = parser.parse_args()

    main(args)
