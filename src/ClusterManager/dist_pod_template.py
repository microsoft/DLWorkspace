import os
import sys
import uuid
import datetime
import json
import copy
import yaml
from jinja2 import Template
from job import Job

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../utils"))
from config import config
from osUtils import mkdirsAsUser
from pod_template_utils import enable_cpu_config


class DistPodTemplate():
    def __init__(self, template, enable_custom_scheduler=False, secret_templates=None):
        self.template = template
        self.enable_custom_scheduler = enable_custom_scheduler
        self.secret_templates = secret_templates

    def generate_pod(self, pod):
        assert(isinstance(self.template, Template))

        dist_id = pod["distId"]
        job_id = pod["jobId"]
        job_path = pod["jobPath"]

        pod["podName"] = "{}-{}".format(job_id, dist_id)

        if (pod["distRole"] == "worker"):
            pod["gpuLimit"] = pod["resourcegpu"]
        else:
            pod["gpuLimit"] = 0

        if "envs" not in pod:
            pod["envs"] = []
        pod["envs"].append({"name": "DLWS_ROLE_NAME", "value": pod["distRole"]})
        pod["envs"].append({"name": "DLWS_ROLE_IDX", "value": pod["distRoleIdx"]})

        if "labels" not in pod:
            pod["labels"] = []
        pod["labels"].append({"name": "distRole", "value": pod["distRole"]})
        pod["labels"].append({"name": "distRoleIdx", "value": pod["distRoleIdx"]})

        pod_yaml = self.template.render(job=pod)
        pod_obj = yaml.full_load(pod_yaml)
        pod_obj["spec"]["containers"][0]["env"].append({"name": "DLWS_LAUNCH_CMD", "value": pod["cmd"]})
        return pod_obj

    def generate_pods(self, job):
        """
        Return (pods, errors)
        """
        assert(isinstance(job, Job))
        params = job.params

        if any(required_field not in params for required_field in
               [
                   "jobtrainingtype",
                   "jobName",
                   "jobPath",
                   "workPath",
                   "dataPath",
                   "cmd",
                   "userId",
                   "resourcegpu",
                   "userName",
               ]):
            return None, "Missing required parameters!"
        assert(params["jobtrainingtype"] == "PSDistJob")

        vc_without_shared_storage = job.get_vc_without_shared_storage()

        job.job_path = params["jobPath"]
        job.work_path = params["workPath"]
        job.data_path = params["dataPath"]
        # TODO user's mountpoints first, but should after 'job_path'
        job.add_mountpoints(job.job_path_mountpoint())
        # TODO: Refactor special VC dependency
        if params["vcName"] not in vc_without_shared_storage:
            job.add_mountpoints({"name": "home", "containerPath": "/home/{}".format(
                job.get_alias()), "hostPath": job.get_homefolder_hostpath(), "enabled": True})
        if "mountpoints" in params:
            job.add_mountpoints(params["mountpoints"])
        # TODO: Refactor special VC dependency
        if params["vcName"] not in vc_without_shared_storage:
            job.add_mountpoints(job.work_path_mountpoint())
            job.add_mountpoints(job.data_path_mountpoint())
        job.add_mountpoints(job.vc_custom_storage_mountpoints())
        job.add_mountpoints(job.vc_storage_mountpoints())
        job.add_mountpoints(job.infiniband_mountpoints())
        params["mountpoints"] = job.mountpoints
        params["init-container"] = os.environ["INIT_CONTAINER_IMAGE"]

        params["user_email"] = params["userName"]
        params["homeFolderHostpath"] = job.get_homefolder_hostpath()
        params["pod_ip_range"] = job.get_pod_ip_range()
        params["usefreeflow"] = job.is_freeflow_enabled()
        params["jobNameLabel"] = ''.join(e for e in params["jobName"] if e.isalnum())
        params["rest-api"] = job.get_rest_api_url()

        if "nodeSelector" not in params:
            params["nodeSelector"] = {}
        if "gpuType" in params:
            params["nodeSelector"]["gpuType"] = params["gpuType"]

        # Set up VC dedicated node usage
        vc_node_hard_assignment = job.get_vc_node_hard_assignment()
        if isinstance(vc_node_hard_assignment, dict):
            vc = params["vcName"]
            # TODO: Fix the case where CPU worker exists in a GPU pool
            if vc in vc_node_hard_assignment and \
                    vc_node_hard_assignment[vc] is True:
                params["nodeSelector"]["vc"] = vc
            else:
                params["nodeSelector"]["vc"] = "default"

        assignedRack = job.get_rack()
        if assignedRack is not None:
            params["nodeSelector"]["rack"] = assignedRack

        params["numworker"] = int(params["numpsworker"])
        params["numps"] = int(params["numps"])

        if "envs" not in params:
            params["envs"] = []
        params["envs"].append({"name": "DLWS_NUM_GPU_PER_WORKER", "value": params["resourcegpu"]})

        params["envs"].append({"name": "DLWS_WORKER_NUM", "value": params["numworker"]})

        job.add_plugins(job.get_plugins())
        params["plugins"] = job.plugins

        # Set NCCL_IB_DISABLE=1 if specified
        nccl_ib_disable = job.get_nccl_ib_disable()
        if nccl_ib_disable is not None and nccl_ib_disable is True:
            params["nccl_ib_disable"] = True

        pods = []
        nums = {"ps": int(params["numps"]), "worker": int(params["numpsworker"])}
        for role in ["ps", "worker"]:
            for idx in range(nums[role]):
                pod = copy.deepcopy(params)
                pod["distRole"] = role
                pod["distRoleIdx"] = idx
                pod["distId"] = "%s%d" % (role, idx)
                pod = enable_cpu_config(pod, job.cluster)
                # mount /pod
                local_pod_path = job.get_hostpath(job.job_path, "%s-%d" % (role, idx))
                pod["mountpoints"].append({"name": "pod", "containerPath": "/pod", "hostPath": local_pod_path, "enabled": True})

                pods.append(pod)

        k8s_pods = []
        for pod in pods:
            k8s_pod = self.generate_pod(pod)
            k8s_pods.append(k8s_pod)

        return k8s_pods, None

    # TODO: Merge with pod_template.py
    def generate_secrets(self, job):
        """generate_plugin_secrets must be called after generate_pods"""
        assert (isinstance(job, Job))
        params = job.params

        if params is None:
            return []

        if "plugins" not in params:
            return []

        plugins = params["plugins"]
        if not isinstance(plugins, dict):
            return []

        # Create secret config for each plugins
        k8s_secrets = []
        for plugin, plugin_config in plugins.items():
            if plugin == "blobfuse" and isinstance(plugin_config, list):
                for bf in plugin_config:
                    k8s_secret = self.generate_blobfuse_secret(bf)
                    k8s_secrets.append(k8s_secret)
            elif plugin == "imagePull" and isinstance(plugin_config, list):
                for image_pull in plugin_config:
                    k8s_secret = self.generate_image_pull_secret(image_pull)
                    k8s_secrets.append(k8s_secret)
        return k8s_secrets

    def generate_blobfuse_secret(self, plugin):
        assert self.secret_templates is not None
        assert "blobfuse" in self.secret_templates
        secret_template = self.secret_templates["blobfuse"]
        assert isinstance(secret_template, Template)

        secret_yaml = secret_template.render(plugin=plugin)
        return yaml.full_load(secret_yaml)

    def generate_image_pull_secret(self, plugin):
        assert self.secret_templates is not None
        assert "imagePull" in self.secret_templates
        secret_template = self.secret_templates["imagePull"]
        assert isinstance(secret_template, Template)

        secret_yaml = secret_template.render(plugin=plugin)
        return yaml.full_load(secret_yaml)

