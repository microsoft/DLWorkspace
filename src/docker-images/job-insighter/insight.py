#!/usr/bin/env python3

import argparse
import collections
import json
import logging
import re
import requests
import timeit
import urllib.parse
import time
import markdown_strings as md

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
    url = urllib.parse.urljoin(restful_url, "/Insight") + "?" + params
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


class Insighter(object):
    def __init__(self, job_id, job_util, node_spec, since, end):
        self.job_id = job_id
        self.job_util = job_util
        self.node_spec = node_spec
        self.since = since
        self.end = end

        # Resource usage pattern from job_util
        self.job_timespan = None
        self.num_gpus = None
        self.idle_gpus = None
        self.active_gpus = None

        self.active_gpu_util = None
        self.active_gpu_memory_util = None
        self.cpu_per_active_gpu = None
        self.memory_per_active_gpu = None

        self.max_cpu_per_gpu = None
        self.max_memory_per_gpu = None

        # Generate insight messages
        self.diagnostics = ""

    def export(self):
        """Valid call after generate"""
        return {
            "job_id": self.job_id,
            "since": self.since,
            "end": self.end,
            "diagnostics": self.diagnostics,
        }

    def generate(self):
        # Job time span
        self.gen_job_timespan()

        # Resource average usage aggregation over time for insight
        self.gen_usage_aggregates()

        # Max resource limit for the job
        self.gen_usage_limit()

        # Generate insight diagnostics
        self.gen_diagnostics()

    def gen_job_timespan(self):
        timespans = [timespan(ts) for _, ts in self.job_util["gpu"].items()]
        timespans.extend(
            [timespan(ts) for _, ts in self.job_util["gpu_memory"].items()])
        timespans.extend(
            [timespan(ts) for _, ts in self.job_util["cpu"].items()])
        timespans.extend(
            [timespan(ts) for _, ts in self.job_util["memory"].items()])
        self.job_timespan = min(timespans)

    def gen_usage_aggregates(self):
        gpu, gpu_memory, cpu, memory = self.get_avg_usage_over_time()

        self.num_gpus = len(gpu)
        self.idle_gpus = sorted([u for u, v in gpu.items() if v == 0])
        self.active_gpus = sorted([u for u, v in gpu.items() if v > 0])

        self.active_gpu_util = 0
        self.active_gpu_memory_util = 0
        self.cpu_per_active_gpu = 0
        self.memory_per_active_gpu = 0

        n = len(self.active_gpus)
        if n > 0:
            self.active_gpu_util = \
                sum([gpu[u] for u in self.active_gpus]) / n
            self.active_gpu_memory_util = \
                sum([gpu_memory[u] for u in self.active_gpus]) / n
            self.cpu_per_active_gpu = \
                sum([v for _, v in cpu.items()]) / n
            self.memory_per_active_gpu = \
                sum([v for _, v in memory.items()]) / n

    def gen_usage_limit(self):
        self.max_cpu_per_gpu = self.node_spec.get("max_cpu_per_gpu")
        self.max_memory_per_gpu = self.node_spec.get("max_memory_per_gpu")

    def get_avg_usage_over_time(self):
        gpu = {
            uuid: avg(ts) for uuid, ts in self.job_util["gpu"].items()}
        gpu_memory = {
            uuid: avg(ts) for uuid, ts in self.job_util["gpu_memory"].items()
        }
        cpu = {
            pod_name: avg(ts) / 100
            for pod_name, ts in self.job_util["cpu"].items()
        }
        memory = {
            pod_name: avg(ts)
            for pod_name, ts in self.job_util["memory"].items()
        }
        return gpu, gpu_memory, cpu, memory

    def gen_diagnostics(self):
        insight_timespan_threshold = 10 * 60  # 10 min
        if self.job_timespan < insight_timespan_threshold:
            msg = "Insight will be available when more metric samples are " \
                  "collected.\n"
            self.diagnostics += msg
            return

        # Check idleness
        self.diagnostics += md.header("GPU Idleness", 2) + "\n"
        if len(self.idle_gpus) == self.num_gpus:
            msg = md.bold("All of %s GPU(s) in the job are idle. " %
                          len(self.idle_gpus))
            msg += "Please consider killing the job if you no longer need it.\n"
            self.diagnostics += msg
            return
        elif len(self.idle_gpus) > 0:
            msg = md.bold("There are %s idle GPU(s) in the job.\n" %
                          len(self.idle_gpus))
            c1 = "If you are running a job on all GPUs, please check if the process(es) on the idle GPU(s) have died/hung"
            c2 = "If you do not need all GPUs in the job, please consider killing the job and request a new job with fewer GPUs."
            msg += md.unordered_list([c1, c2]) + "\n"
            self.diagnostics += msg
        else:
            self.diagnostics += md.bold("All GPU(s) are active.") + "\n"
        self.diagnostics += "\n"

        # Check Resource usage for active GPUs
        self.diagnostics += md.header("Active GPU Utilization", 2) + "\n"
        good_gpu_util_threshold = 90
        good_gpu_mem_util_threshold = 50
        if self.active_gpu_util >= good_gpu_util_threshold:
            msg = "Average active GPU utilization over time is good at " \
                  "%.2f%%.\n" % self.active_gpu_util
            self.diagnostics += msg
        else:
            msg = "Average active GPU utilization over time is " \
                  "%.2f%% < %s%%. You can try below suggestions to boost " \
                  "GPU utilization:\n" % \
                  (self.active_gpu_util, good_gpu_util_threshold)

            suggestions = []
            if self.active_gpu_memory_util < good_gpu_mem_util_threshold:
                suggestions.append(
                    "Average active GPU memory utilization over time is below "
                    "%s%%. Try increasing batch size to put more data "
                    "onto GPU memory to boost GPU utilization. For a "
                    "distributed job, if the model has strict "
                    "requirement on the global effective batch size "
                    "for convergence, you can consider using a job "
                    "with fewer GPUs and bigger batch size per GPU."
                    % good_gpu_mem_util_threshold)

            if self.max_cpu_per_gpu is not None and \
                    self.cpu_per_active_gpu < self.max_cpu_per_gpu:
                suggestions.append(
                    "The job uses %.2f CPU cores per active GPU on average"
                    "over time. The maximum CPU cores per GPU you can "
                    "use without interfering with other GPUs in this "
                    "cluster is %.2f. You can use more CPU cores to "
                    "perform data preprocessing to keep GPUs from "
                    "starvation. Please consider using/increasing "
                    "parallel preprocessing on your input data." %
                    (self.cpu_per_active_gpu, self.max_cpu_per_gpu)
                )

            if self.max_memory_per_gpu is not None and \
                    self.memory_per_active_gpu < self.max_memory_per_gpu:
                suggestions.append(
                    "The job uses %.2fG memory per active GPU on average"
                    "over time. The maximum memory per GPU you can "
                    "use without interfering with other GPUs in this "
                    "cluster is %.2fG. You can preload more input "
                    "data into memory to make sure your data pipeline "
                    "is never waiting on data loading from "
                    "disk/remote." % (self.memory_per_active_gpu / G,
                                      self.max_memory_per_gpu / G)
                )

            suggestions.append(
                "Please check if your program is waiting on NFS I/O. "
                "If so, please consider using scalable storage, e.g. "
                "Azure blob."
            )

            suggestions.append(
                "Suggestions above are purely based on average usage over a "
                "time window. Please take a closer look at METRICS tab to "
                "better understand the utilization pattern of GPU, GPU "
                "memory, CPU and memory over time for further optimization."
            )
            msg += md.unordered_list(suggestions) + "\n"
            self.diagnostics += msg + "\n"


def get_job_utils(task_gpu_percent, task_gpu_mem_percent, task_cpu_percent,
                  task_mem_usage_byte):
    """Parse metric lists and constructs a list of JobUtil.

    Args:
        task_gpu_percent: A list of all task_gpu_percent
        task_gpu_mem_percent: A list of all task_gpu_mem_percent
        task_cpu_percent: A list of all task_cpu_percent
        task_mem_usage_byte: A list of all task_mem_usage_byte
        start: Start time in epoch seconds
        end: End time in epoch seconds

    Returns:
        A list of job utils
    """
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

    return jobs


def gen_insights(task_gpu_percent, task_gpu_mem_percent, task_cpu_percent,
                 task_mem_usage_byte, since, end, node_spec, running_job_ids):
    job_utils = get_job_utils(task_gpu_percent, task_gpu_mem_percent,
                              task_cpu_percent, task_mem_usage_byte)

    insights = []
    for job_id, job_util in job_utils.items():
        # Only generate insight for currently running jobs.
        if job_id not in running_job_ids:
            logger.info("skip generating non-running job %s", job_id)
            continue

        try:
            insighter = Insighter(job_id, job_util, node_spec, since, end)
            insighter.generate()
            insights.append(insighter.export())
        except:
            logger.exception("failed to generate insight from %s", job_util)

    return insights


def upload_insights(insights, restful_url, dry_run):
    for insight in insights:
        job_id = insight.get("job_id")
        try:
            if dry_run:
                logger.info("dry run. logging insight for job %s: %s", job_id,
                            insight)
                continue

            resp = set_job_insight(restful_url, job_id, insight)
            if resp.status_code != 200:
                logger.error("failed to upload insight for job %s. %s", job_id,
                             resp.text)
            else:
                logger.info("successfully uploaded insight for job %s", job_id)
        except:
            logger.exception("failed to upload insight for %s", job_id)


def run(prometheus_url, mins_ago, restful_url, dry_run):
    now = datetime.now()
    since = int(datetime.timestamp(now - timedelta(minutes=mins_ago)))
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
    while True:
        try:
            run(params.prometheus_url, params.mins_ago, params.restful_url,
                params.dry_run)
        except:
            logger.exception("failed in current run of job insight")

        logger.info("sleep for %s seconds before next run.", params.sleep_time)
        time.sleep(params.sleep_time)


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
    parser.add_argument("--mins_ago",
                        "-a",
                        default=15,
                        type=int,
                        help="Collect metrics since minutes ago. Default: 15")
    parser.add_argument("--restful_url",
                        "-r",
                        required=True,
                        help="Restful API url, e.g. http://localhost:5000")
    parser.add_argument("--dry_run",
                        "-d",
                        action="store_true",
                        help="Do not write to database if specified")
    parser.add_argument("--sleep_time",
                        "-s",
                        default=300,
                        type=int,
                        help="Sleep interval in seconds between runs. "
                             "Default: 300")

    args = parser.parse_args()

    main(args)
