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

    def test_generate_launch_script(self):
        job_id = "ce7dca49-28df-450a-a03b-51b9c2ecc69c"
        path_to_save = "/tmp"
        user_id = "20000"
        gpu_num = 3
        user_script = "sleep infinity"

        script_file = PodTemplate.generate_launch_script(job_id, path_to_save, user_id, gpu_num, user_script)

        # return the container command
        self.assertListEqual(["bash", "/pod/scripts/bootstrap.sh"], script_file)

    def test_pod_template_without_custer_scheduler(self):
        enable_custom_scheduler = False
        pod_template = PodTemplate(job.get_template(), enable_custom_scheduler)

        pod = {"gpuLimit": 2}
        data = pod_template.generate_pod(pod)

        # not eanbled custom scheduler, set the resource limits: spec.containers[].resources.limits
        self.assertEqual(pod["gpuLimit"], data["spec"]["containers"][0]["resources"]["limits"]["nvidia.com/gpu"])
        # metadata.annotations["pod.alpha/DeviceInformation"] should be empty
        self.assertTrue(("annotations" not in data["metadata"]) or ("pod.alpha/DeviceInformation" not in data["metadata"]["annotations"]))

    def test_generate_pod_with_envs(self):
        enable_custom_scheduler = False
        pod_template = PodTemplate(job.get_template(), enable_custom_scheduler)

        pod = {
            "gpuLimit": 2,
            "envs": [{"name": "my_env_name", "value": "my_env_value"}],
        }
        data = pod_template.generate_pod(pod)

        self.assertIn({"name": "my_env_name", "value": "my_env_value"}, data["spec"]["containers"][0]["env"])

    def test_generate_pod_with_labels(self):
        enable_custom_scheduler = False
        pod_template = PodTemplate(job.get_template(), enable_custom_scheduler)

        pod = {
            "gpuLimit": 2,
            "labels": [{"name": "my_label_name", "value": "my_label_value"}],
        }
        data = pod_template.generate_pod(pod)

        self.assertEqual("my_label_value", data["metadata"]["labels"]["my_label_name"])

    def test_pod_template_with_custom_scheduler(self):
        enable_custom_scheduler = True
        pod_template = PodTemplate(job.get_template(), enable_custom_scheduler)

        gpu_num = 2
        pod = {
            "podName": "790a6b30-560f-44a4-a9f0-5d1458dcb0d1-pod-0",
            "gpuLimit": gpu_num,
        }
        data = pod_template.generate_pod(pod)

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
            "gpuLimit": gpu_num,
            "useGPUTopology": True
        }
        data = pod_template.generate_pod(pod)

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

    def test_generate_pods_missing_required_params(self):
        enable_custom_scheduler = True
        pod_template = PodTemplate(job.get_template(), enable_custom_scheduler)

        job.params = {}
        job_description, error = pod_template.generate_pods(job)

        self.assertIsNone(job_description)
        self.assertTrue(error)
        self.assertEqual("Missing required parameters!", error)

    def test_generate_pods(self):
        enable_custom_scheduler = True
        pod_template = PodTemplate(job.get_template(), enable_custom_scheduler)

        job.params = {
            "gid": "20000",
            "uid": "20000",
            "user": "user",
            "mountpoints": [
                {
                    "description": "NFS (remote file share)",
                    "enabled": True,
                    "containerPath": "/home/user",
                    "hostPath": "/dlwsdata/work/user",
                    "name": "homefolder"
                }
            ],
            "image": "indexserveregistry.azurecr.io/deepscale:1.0",
            "userId": "20000",
            "dataPath": "",
            "jobId": "140782a0-7f6d-4039-9801-fd6294c7c88a",
            "isParent": 1,
            "jobType": "training",
            "jobPath": "user/jobs/190627/140782a0-7f6d-4039-9801-fd6294c7c88a",
            "containerUserId": "0",
            "resourcegpu": 1,
            "env": [
            ],
            "enabledatapath": True,
            "runningasroot": True,
            "interactivePorts": [

            ],
            "preemptionAllowed": False,
            "jobtrainingtype": "RegularJob",
            "do_log": False,
            "is_interactive": False,
            "familyToken": "72fc61265bcb4416b68b44c82d120b3b",
            "enableworkpath": True,
            "vcName": "vc1",
            "userName": "user@foo.com",
            "workPath": "user",
            "cmd": "sleep infinity",
            "jobName": "test-job",
            "enablejobpath": True,
            "gpuType": "P40",
            "ssh": True
        }

        pods, error = pod_template.generate_pods(job)

        self.assertFalse(error)
        # generate list of pod yamls
        self.assertTrue(list, type(pods))
        self.assertEqual(1, len(pods))
        self.assertIsNotNone(pods[0]["spec"]["containers"][0]["command"])

        job.params["plugins"] = {
            "blobfuse": [
                {
                    "accountName": "abc",
                    "accountKey": "password",
                    "containerName": "test1",
                    "mountPath": "/blobdata1"
                },
                {
                    "accountName": "abc",
                    "accountKey": "password",
                    "containerName": "test2",
                    "mountPath": "/blobdata2"
                }
            ]
        }

        pods, error = pod_template.generate_pods(job)

        self.assertFalse(error)
        self.assertEqual(2, len(pods))
        self.assertEqual("Secret", pods[1]["kind"])
