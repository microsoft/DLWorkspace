#!/usr/bin/env python3

from unittest import TestCase
from insight import G, gen_insights


def test_node_spec():
    return {
        "max_cpu_per_gpu": 4,
        "max_memory_per_gpu": 100 * G
    }


def test_task_gpu_percent():
    return [{
        "metric": {"job_name": "job0", "uuid": "GPU-0"},
        "values": [[1588630427, "25"],
                   [1588632227, "35"],
                   [1588634027, "30"]]
    }]


def test_task_gpu_mem_percent():
    return [{
        "metric": {"job_name": "job0", "uuid": "GPU-0"},
        "values": [[1588630427, "45"],
                   [1588632227, "45"],
                   [1588634027, "45"]]
    }]


def test_task_cpu_percent():
    return [{
        "metric": {"job_name": "job0", "pod_name": "job0-master"},
        "values": [[1588630427, "150"],
                   [1588632227, "100"],
                   [1588634027, "50"]]
    }]


def test_task_mem_usage_byte():
    return [{
        "metric": {"job_name": "job0", "pod_name": "job0-master"},
        "values": [[1588630427, str(10 * G)],
                   [1588632227, str(10 * G)],
                   [1588634027, str(10 * G)]]
    }]


def test_running_job_ids():
    return ["job0"]


class TestInsight(TestCase):
    def test_gen_insights(self):
        since = 1588630427
        end = 1588634027
        node_spec = test_node_spec()
        task_gpu_percent = test_task_gpu_percent()
        task_gpu_mem_percent = test_task_gpu_mem_percent()
        task_cpu_percent = test_task_cpu_percent()
        task_mem_usage_byte = test_task_mem_usage_byte()
        running_job_ids = test_running_job_ids()

        insights = gen_insights(task_gpu_percent, task_gpu_mem_percent,
                                task_cpu_percent, task_mem_usage_byte,
                                since, end, node_spec, running_job_ids)
        self.assertEqual(len(insights), 1)

        insight = insights[0]

        expected_messages = ["All GPU(s) are active."]
        expected_messages.append(
            "Average active GPU utilization is below "
            "90%. You can take below suggestions to potentially "
            "boost GPU utilization."
        )
        messages = []
        messages.append(
            "Average active GPU memory utilization is below "
            "50%. Try increasing batch size to put more data "
            "onto GPU memory to boost GPU utilization. For a "
            "distributed job, if the model has strict "
            "requirement on the global effective batch size "
            "for convergence, you can consider using a job "
            "with fewer GPUs and bigger batch size per GPU."
        )
        messages.append(
            "The job uses 1.00 CPU cores per active GPU on "
            "average. The maximum CPU cores per GPU you can "
            "use without interfering with other GPUs in this "
            "cluster is 4.00. You can use more CPU cores to "
            "perform data preprocessing to keep GPUs from "
            "starvation. Please consider using/increasing "
            "parallel preprocessing on your input data."
        )
        messages.append(
            "The job uses 10.00G memory per active GPU on "
            "average. The maximum memory per GPU you can "
            "use without interfering with other GPUs in this "
            "cluster is 100.00G. You can preload more input "
            "data into memory to make sure your data pipeline "
            "is never waiting on data loading from "
            "disk/remote."
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
        expected_messages.append(messages)

        expected_insight = {
            "job_id": "job0",
            "since": since,
            "end": end,
            "job_timespan": end - since,
            "num_gpus": 1,
            "num_idle_gpus": 0,
            "num_active_gpus": 1,
            "avg_active_gpu_util": float(30),
            "avg_active_gpu_memory_util": float(45),
            "avg_cpu_per_active_gpu": float(1),
            "avg_memory_per_active_gpu": float(10 * G),
            "max_cpu_per_gpu": 4,
            "max_memory_per_gpu": 100 * G,
            "messages": expected_messages,
        }
        self.assertEqual(expected_insight, insight)
