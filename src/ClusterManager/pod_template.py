#!/usr/bin/env python3

import os
import sys
import yaml
import copy

from job import Job

from jinja2 import Template

sys.path.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../utils"))

from pod_template_utils import enable_cpu_config
from mountpoint import make_mountpoint


class JobTemplate(object):
    def __init__(self, template, secret_templates=None):
        self.template = template
        self.secret_templates = secret_templates

    def generate_params(self, job):
        """
        Return (pods, errors)
        """
        assert (isinstance(job, Job))
        params = job.params

        if any(required_field not in params for required_field in [
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

        # Add NFS mountpoints before hostPath mountpoints.
        # mountpoints added by NFS mountpoint should not appear in hostPath
        # mountpoints again.
        if "job_mountpoints" in params:
            for mountpoint_params in params["job_mountpoints"]:
                job.add_job_mountpoints(make_mountpoint(mountpoint_params))
        job.add_job_mountpoints(job.mountpoints_for_job())

        vc_without_shared_storage = job.get_vc_without_shared_storage()

        job.job_path = params["jobPath"]
        job.work_path = params["workPath"]
        job.data_path = params["dataPath"]
        # TODO user's mountpoints first, but should after 'job_path'
        job.add_mountpoints(job.job_path_mountpoint())
        # TODO: Refactor special VC dependency
        if params["vcName"] not in vc_without_shared_storage:
            job.add_mountpoints({
                "name":
                "home",
                "containerPath":
                "/home/{}".format(job.get_alias()),
                "hostPath":
                job.get_homefolder_hostpath(),
                "enabled":
                True
            })

        if "mountpoints" in params:
            job.add_mountpoints(params["mountpoints"])
        # TODO: Refactor special VC dependency
        if params["vcName"] not in vc_without_shared_storage:
            job.add_mountpoints(job.work_path_mountpoint())
            job.add_mountpoints(job.data_path_mountpoint())
        job.add_mountpoints(job.vc_custom_storage_mountpoints())
        job.add_mountpoints(job.vc_storage_mountpoints())

        params["job_mountpoints"] = [
            mp.to_dict() for mp in job.job_mountpoints
        ]
        params["mountpoints"] = job.mountpoints
        params["init-container"] = os.environ["INIT_CONTAINER_IMAGE"]

        params["user_email"] = params["userName"]
        params["homeFolderHostpath"] = job.get_homefolder_hostpath()
        params["pod_ip_range"] = job.get_pod_ip_range()
        params["jobNameLabel"] = ''.join(e for e in params["jobName"]
                                         if e.isalnum())

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

        if "envs" not in params:
            params["envs"] = []

        params["envs"].append({
            "name": "DLWS_NUM_GPU_PER_WORKER",
            "value": str(params["resourcegpu"])
        })
        params["envs"].append({
            "name": "DLTS_NUM_GPU_PER_WORKER",
            "value": str(params["resourcegpu"])
        })

        job.add_plugins(job.get_plugins())
        params["plugins"] = job.plugins

        # Set NCCL_IB_DISABLE=1 if specified
        nccl_ib_disable = job.get_nccl_ib_disable()
        if nccl_ib_disable is not None and nccl_ib_disable is True:
            params["nccl_ib_disable"] = True

        return params, None

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
        for plugin, plugin_config in list(plugins.items()):
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


class RegularJobTemplate(JobTemplate):
    def __init__(self, template, secret_templates=None):
        super(RegularJobTemplate, self).__init__(template, secret_templates)

    def generate_pods(self, job):
        """
        Return (pods, errors)
        """
        params, errors = self.generate_params(job)
        if errors is not None:
            return None, errors

        pod_yaml = self.template.render(job=params)
        # because user's cmd can be multiple lines, should add after yaml load
        pod_obj = yaml.full_load(pod_yaml)
        pod_obj["spec"]["containers"][0]["env"].append({
            "name": "DLTS_LAUNCH_CMD",
            "value": params["cmd"]
        })

        return [pod_obj], None

    def generate_params(self, job):
        params, error = super(RegularJobTemplate, self).generate_params(job)

        params = enable_cpu_config(params, job.cluster)

        params["podName"] = job.job_id
        params["role_name"] = "master"

        params["numps"] = 0
        params["numworker"] = 1
        params["fragmentGpuJob"] = True
        if "gpuLimit" not in params:
            params["gpuLimit"] = params["resourcegpu"]

        return params, None


class InferenceJobTemplate(JobTemplate):
    def __init__(self,
                 template,
                 deployment_template=None,
                 secret_templates=None):
        self.deployment_template = deployment_template
        super(InferenceJobTemplate, self).__init__(template, secret_templates)

    def generate_pods(self, job):
        """
        Return (pods, errors)
        """
        params, errors = self.generate_params(job)
        if errors is not None:
            return None, errors

        k8s_pods = []

        pod_yaml = self.template.render(job=params)
        pod_obj = yaml.full_load(pod_yaml)
        # because user's cmd can be multiple lines, should add after yaml load
        pod_obj["spec"]["containers"][0]["env"].append({
            "name": "DLTS_LAUNCH_CMD",
            "value": params["cmd"]
        })
        k8s_pods.append(pod_obj)

        deployment_params = copy.deepcopy(params)

        deployment_params["deployment_replicas"] = params["resourcegpu"]
        deployment_params["LaunchCMD"] = params["cmd"]

        deployment_yaml = self.deployment_template.render(
            job=deployment_params)
        deployment_obj = yaml.full_load(deployment_yaml)
        # because user's cmd can be multiple lines, should add after yaml load
        deployment_obj["spec"]["template"]["spec"]["containers"][0][
            "env"].append({
                "name": "DLTS_LAUNCH_CMD",
                "value": params["cmd"]
            })
        k8s_pods.append(deployment_obj)

        return k8s_pods, None

    def generate_params(self, job):
        params, error = super(InferenceJobTemplate, self).generate_params(job)

        params = enable_cpu_config(params, job.cluster)

        params["role_name"] = "master"
        params["podName"] = job.job_id

        params["numps"] = 0
        params["numworker"] = 1
        params["fragmentGpuJob"] = True
        params["gpuLimit"] = 0

        return params, None


class DistributeJobTemplate(JobTemplate):
    def __init__(self, template, secret_templates=None):
        super(DistributeJobTemplate, self).__init__(template, secret_templates)

    def generate_pod(self, pod):
        assert (isinstance(self.template, Template))

        dist_id = pod["distId"]
        job_id = pod["jobId"]
        job_path = pod["jobPath"]

        pod["podName"] = "{}-{}".format(job_id, dist_id)

        if (pod["role_name"] == "worker"):
            pod["gpuLimit"] = pod["resourcegpu"]
        else:
            pod["gpuLimit"] = 0

        if "envs" not in pod:
            pod["envs"] = []
        pod["envs"].append({"name": "DLWS_ROLE_IDX", "value": pod["role_idx"]})

        pod_yaml = self.template.render(job=pod)
        pod_obj = yaml.full_load(pod_yaml)
        pod_obj["spec"]["containers"][0]["env"].append({
            "name": "DLTS_LAUNCH_CMD",
            "value": pod["cmd"]
        })
        return pod_obj

    def generate_pods(self, job):
        """
        Return (pods, errors)
        """
        params, errors = self.generate_params(job)
        if errors is not None:
            return None, errors

        pods = []
        nums = {
            "ps": int(params["numps"]),
            "worker": int(params["numpsworker"])
        }
        for role in ["ps", "worker"]:
            for idx in range(nums[role]):
                pod = copy.deepcopy(params)
                pod["role_name"] = role
                pod["role_idx"] = str(idx)
                pod["distId"] = "%s%d" % (role, idx)
                pod = enable_cpu_config(pod, job.cluster)
                # ps should use the default 1 CPU and 0 memory configuration
                if role == "ps":
                    pod.pop("cpurequest", None)
                    pod.pop("cpulimit", None)
                    pod.pop("memoryrequest", None)
                    pod.pop("memorylimit", None)

                pods.append(pod)

        k8s_pods = []
        for pod in pods:
            k8s_pod = self.generate_pod(pod)
            k8s_pods.append(k8s_pod)

        return k8s_pods, None

    def generate_params(self, job):
        params, error = super(DistributeJobTemplate, self).generate_params(job)

        if error is not None:
            return params, error

        job.add_mountpoints(job.infiniband_mountpoints())

        params["numworker"] = int(params["numpsworker"])
        params["numps"] = int(params["numps"])

        params["envs"].append({
            "name": "DLWS_WORKER_NUM",
            "value": str(params["numworker"])
        })

        return params, None
