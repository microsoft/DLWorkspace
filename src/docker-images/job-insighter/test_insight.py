#!/usr/bin/env python3

import markdown_strings as md

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

        expected_diagnostics = md.header("GPU Idleness", 2) + "\n"
        expected_diagnostics += md.bold("All GPU(s) are active.") + "\n\n"

        expected_diagnostics += md.header("Active GPU Utilization", 2) + "\n"
        expected_diagnostics += "Average active GPU utilization over time is 30.00% < 90%. You can try below suggestions to boost GPU utilization:\n"
        suggestions = []
        suggestions.append(
            "Average active GPU memory utilization over time is below "
            "50%. Try increasing batch size to put more data "
            "onto GPU memory to boost GPU utilization. For a "
            "distributed job, if the model has strict "
            "requirement on the global effective batch size "
            "for convergence, you can consider using a job "
            "with fewer GPUs and bigger batch size per GPU."
        )
        suggestions.append(
            "The job uses 1.00 CPU cores per active GPU on average"
            "over time. The maximum CPU cores per GPU you can "
            "use without interfering with other GPUs in this "
            "cluster is 4.00. You can use more CPU cores to "
            "perform data preprocessing to keep GPUs from "
            "starvation. Please consider using/increasing "
            "parallel preprocessing on your input data."
        )
        suggestions.append(
            "The job uses 10.00G memory per active GPU on average"
            "over time. The maximum memory per GPU you can "
            "use without interfering with other GPUs in this "
            "cluster is 100.00G. You can preload more input "
            "data into memory to make sure your data pipeline "
            "is never waiting on data loading from "
            "disk/remote."
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
        expected_diagnostics += md.unordered_list(suggestions) + "\n"
        expected_diagnostics += "\n"

        expected_insight = {
            "job_id": "job0",
            "since": since,
            "end": end,
            "diagnostics": expected_diagnostics,
        }
        self.assertEqual(expected_insight, insight)
