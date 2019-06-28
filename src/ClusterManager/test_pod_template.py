import unittest
import json
import yaml
import sys
import os
from job import Job, JobSchema
from pod_template import PodTemplate

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../utils"))
from config import config

VALID_JOB_ATTRIBUTES = {
    "cluster": config,
    "jobId": "ce7dca49-28df-450a-a03b-51b9c2ecc69c",
    "userName": "user@foo.com",
    "jobPath": "user_alias/jobs/date/job_id"
}

job, errors = JobSchema().load(VALID_JOB_ATTRIBUTES)
assert(not errors)


class TestPodTemplate(unittest.TestCase):

    def test_pod_template_without_custer_scheduler(self):
        enable_custom_scheduler = False
        pod_template = PodTemplate(job.get_template(), enable_custom_scheduler)

        pod = {"resourcegpu": 2}
        pod_yaml = pod_template.generate_pod_yaml(pod)
        data = yaml.load(pod_yaml)

        # not eanbled custom scheduler, set the resource limits: spec.containers[].resources.limits
        self.assertEqual(pod["resourcegpu"], data["spec"]["containers"][0]["resources"]["limits"]["nvidia.com/gpu"])
        # metadata.annotations["pod.alpha/DeviceInformation"] should be empty
        self.assertTrue(("annotations" not in data["metadata"]) or ("pod.alpha/DeviceInformation" not in data["metadata"]["annotations"]))

    def test_pod_template_with_custom_scheduler(self):
        enable_custom_scheduler = True
        pod_template = PodTemplate(job.get_template(), enable_custom_scheduler)

        gpu_num = 2
        pod = {
            "podName": "790a6b30-560f-44a4-a9f0-5d1458dcb0d1-pod-0",
            "resourcegpu": gpu_num,
        }
        pod_yaml = pod_template.generate_pod_yaml(pod)
        data = yaml.load(pod_yaml)

        # eanbled custom scheduler would clear the resource limits: spec.containers[].resources.limits
        self.assertEqual(0, data["spec"]["containers"][0]["resources"]["limits"]["nvidia.com/gpu"])

        # metadata.annotations["pod.alpha/DeviceInformation"] should be set
        # annotations = data["metadata"]["annotations"]
        device_annotation = json.loads(data["metadata"]["annotations"]["pod.alpha/DeviceInformation"])
        self.assertEqual(gpu_num, device_annotation["runningcontainer"][pod["podName"]]["requests"]["alpha.gpu/numgpu"])
        # disabled topology
        self.assertEqual(0, device_annotation["requests"]["alpha.gpu/gpu-generate-topology"])

    def test_pod_template_with_custom_scheduler_use_topology(self):
        enable_custom_scheduler = True
        pod_template = PodTemplate(job.get_template(), enable_custom_scheduler)

        gpu_num = 2
        pod = {
            "podName": "790a6b30-560f-44a4-a9f0-5d1458dcb0d1-pod-0",
            "resourcegpu": gpu_num,
            "useGPUTopology": True
        }
        pod_yaml = pod_template.generate_pod_yaml(pod)
        data = yaml.load(pod_yaml)

        # eanbled custom scheduler, clear the resource limits: spec.containers[].resources.limits
        self.assertEqual(0, data["spec"]["containers"][0]["resources"]["limits"]["nvidia.com/gpu"])

        # metadata.annotations["pod.alpha/DeviceInformation"] should be set:
        # {
        #    "requests":{
        #       "alpha.gpu/gpu-generate-topology":1
        #    },
        #    "runningcontainer":{
        #       "790a6b30-560f-44a4-a9f0-5d1458dcb0d1-pod-0":{
        #          "requests":{
        #             "alpha.gpu/numgpu":2
        #          }
        #       }
        #    },
        #    "podname":"790a6b30-560f-44a4-a9f0-5d1458dcb0d1-pod-0"
        # }

        # annotations = data["metadata"]["annotations"]
        device_annotation = json.loads(data["metadata"]["annotations"]["pod.alpha/DeviceInformation"])
        self.assertEqual(gpu_num, device_annotation["runningcontainer"][pod["podName"]]["requests"]["alpha.gpu/numgpu"])
        # enabled topology
        self.assertEqual(1, device_annotation["requests"]["alpha.gpu/gpu-generate-topology"])
