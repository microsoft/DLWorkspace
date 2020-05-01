#!/usr/bin/env python3

import argparse
import logging
import requests
import timeit
import urllib.parse

logger = logging.getLogger(__name__)


class JobUtil(object):
    def __init__(self, job_id, gpu, gpu_memory, cpu, memory):
        self.job_id = job_id

        self._gpu = gpu
        self._gpu_memory = gpu_memory
        self._cpu = cpu
        self._memory = memory


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
        "step": step,
    })

    url = urllib.parse.urljoin(prometheus_url,
                               "/prometheus/api/v1/query_range") + "?" + params

    start = timeit.default_timer()
    obj = request_with_error_handling(url)
    elapsed = timeit.default_timer() - start
    logger.info("request spent %.2fs", elapsed)

    if walk_json_field_safe(obj, "status") != "success":
        logger.warning("requesting %s failed, body is %s", url, obj)
        return None

    return obj


def get_task_gpu_percent(prometheus_url, since, end):
    return query_prometheus(
        prometheus_url, "avg(task_gpu_percent) by (job_name, minor_number)",
        since, end, "1m")


def get_task_gpu_mem_percent(prometheus_url, since, end):
    return query_prometheus(
        prometheus_url, "avg(task_gpu_mem_percent) by (job_name, minor_number)",
        since, end, "1m")


def get_task_cpu_percent(prometheus_url, since, end):
    return query_prometheus(
        prometheus_url, "avg(task_cpu_percent) by (job_name)",
        since, end, "1m")


def get_task_mem_usage_byte(prometheus_url, since, end):
    return query_prometheus(
        prometheus_url, "avg(task_mem_usage_byte) by (job_name)",
        since, end, "1m")


def get_job_utils(task_gpu_percent, task_gpu_mem_percent, task_cpu_percent,
                  task_mem_usage_byte):
    """Parse metric lists and constructs a list of JobUtil.

    Args:
        task_gpu_percent: A list of all task_gpu_percent
        task_gpu_mem_percent: A list of all task_gpu_mem_percent
        task_cpu_percent: A list of all task_cpu_percent
        task_mem_usage_byte: A list of all task_mem_usage_byte

    Returns:
        A list of JobUtil
    """
    pass


def run(prometheus_url, restful_url, dry_run):
    pass


def main(params):
    run(params.prometheus_url, params.restful_url, params.dry_run)


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
