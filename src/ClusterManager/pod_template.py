import os
import sys
import json
import yaml
from jinja2 import Template
from job import Job
import copy


sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../utils"))
from osUtils import mkdirsAsUser


class PodTemplate():
    def __init__(self, template, deployment_template=None, enable_custom_scheduler=False, secret_template=None):
        self.template = template
        self.deployment_template = deployment_template
        self.enable_custom_scheduler = enable_custom_scheduler
        self.secret_template = secret_template

    @staticmethod
    def generate_launch_script(job_id, path_to_save, user_id, gpu_num, user_script):
        if not os.path.exists(path_to_save):
            mkdirsAsUser(path_to_save, user_id)

        file_name = "job_command.sh"
        launch_script_file = os.path.join(path_to_save, file_name)
        with open(launch_script_file, 'w') as f:
            f.write(user_script)
        os.system("sudo chown %s %s" % (user_id, launch_script_file))
        luanch_cmd = ["bash", "/pod/scripts/bootstrap.sh"]
        return luanch_cmd


    def generate_deployment(self, pod):
        assert(isinstance(self.template, Template))
        pod_yaml = self.deployment_template.render(job=pod)
        return yaml.full_load(pod_yaml)


    def generate_pod(self, pod):
        assert(isinstance(self.template, Template))
        if self.enable_custom_scheduler:
            if "useGPUTopology" in pod and pod["useGPUTopology"]:
                gpu_topology_flag = 1
            else:
                # for cases when desired topology is explictly given or not desired
                gpu_topology_flag = 0
            pod_name = pod["podName"]
            request_gpu = int(pod["gpuLimit"])

            podInfo = {
                "podname": pod_name,
                "requests": {
                    "alpha.gpu/gpu-generate-topology": gpu_topology_flag
                },
                "runningcontainer": {
                    pod_name: {
                        "requests": {"alpha.gpu/numgpu": request_gpu}
                    },
                },
            }

            if "annotations" not in pod:
                pod["annotations"] = {}
            pod["annotations"]["pod.alpha/DeviceInformation"] = "'" + json.dumps(podInfo) + "'"
            # gpu requests specified through annotation
            pod["gpuLimit"] = 0

        pod_yaml = self.template.render(job=pod)
        return yaml.full_load(pod_yaml)

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

        job.job_path = params["jobPath"]
        job.work_path = params["workPath"]
        job.data_path = params["dataPath"]
        # TODO user's mountpoints first, but should after 'job_path'
        job.add_mountpoints(job.job_path_mountpoint())
        job.add_mountpoints({"name": "home", "containerPath": "/home/{}".format(job.get_alias()), "hostPath": job.get_homefolder_hostpath(), "enabled": True})
        if "mountpoints" in params:
            job.add_mountpoints(params["mountpoints"])
        job.add_mountpoints(job.work_path_mountpoint())
        job.add_mountpoints(job.data_path_mountpoint())
        job.add_mountpoints(job.vc_custom_storage_mountpoints())
        job.add_mountpoints(job.vc_storage_mountpoints())
        params["mountpoints"] = job.mountpoints

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

        # CPU job should be assigned to CPU node if there is any available in the cluster
        config = job.cluster
        enable_cpuworker = config.get("enable_cpuworker", False)
        default_cpurequest = config.get("default_cpurequest")
        default_cpulimit = config.get("default_cpulimit")
        default_memoryrequest = config.get("default_memoryrequest")
        default_memorylimit = config.get("default_memorylimit")

        if enable_cpuworker and int(params["resourcegpu"]) == 0:
            params["nodeSelector"]["cpuworker"] = "active"
            if "cpurequest" not in params and default_cpurequest is not None:
                params["cpurequest"] = default_cpurequest
            if "cpulimit" not in params and default_cpulimit is not None:
                params["cpulimit"] = default_cpulimit
            if "memoryrequest" not in params and default_memoryrequest is not None:
                params["memoryrequest"] = default_memoryrequest
            if "memorylimit" not in params and default_memorylimit is not None:
                params["memorylimit"] = default_memorylimit

        local_pod_path = job.get_hostpath(job.job_path, "master")
        params["LaunchCMD"] = PodTemplate.generate_launch_script(params["jobId"], local_pod_path, params["userId"], params["resourcegpu"], params["cmd"])

        if "envs" not in params:
            params["envs"] =[]

        job.add_plugins(job.get_plugins())
        params["plugins"] = job.plugins

        pods = []
        if all(hyper_parameter in params for hyper_parameter in ["hyperparametername", "hyperparameterstartvalue", "hyperparameterendvalue", "hyperparameterstep"]):
            env_name = params["hyperparametername"]
            start = int(params["hyperparameterstartvalue"])
            end = int(params["hyperparameterendvalue"])
            step = int(params["hyperparameterstep"])

            for idx, val in enumerate(range(start, end, step)):
                pod = copy.deepcopy(params)
                params["envs"].append({"name": "DLWS_ROLE_NAME", "value": "master"})
                params["envs"].append({"name": "DLWS_NUM_GPU_PER_WORKER", "value": params["resourcegpu"]})
                pod["podName"] = "{0}-pod-{1}".format(job.job_id, idx)
                pod["envs"].append({"name": env_name, "value": val})
                pods.append(pod)
        else:
            pod = copy.deepcopy(params)
            pod["envs"].append({"name": "DLWS_ROLE_NAME", "value": "master"})
            pod["envs"].append({"name": "DLWS_NUM_GPU_PER_WORKER", "value": params["resourcegpu"]})
            pod["podName"] = job.job_id
            pods.append(pod)


        k8s_pods = []
        for idx,pod in enumerate(pods):
            pod["numps"] = 0
            pod["numworker"] = 1
            pod["fragmentGpuJob"] = True
            if "gpuLimit" not in pod:
                pod["gpuLimit"] = pod["resourcegpu"]


            if params["jobtrainingtype"] == "InferenceJob":
                pod["gpuLimit"] = 0

            # mount /pod
            pod_path = job.get_hostpath(job.job_path, "master")
            pod["mountpoints"].append({"name": "pod", "containerPath": "/pod", "hostPath": pod_path, "enabled": True})

            k8s_pod = self.generate_pod(pod)
            k8s_pods.append(k8s_pod)

        if params["jobtrainingtype"] == "InferenceJob":
            pod = copy.deepcopy(params)
            pod["numps"] = 0
            pod["numworker"] = 1
            pod["fragmentGpuJob"] = True
            if "gpuLimit" not in pod:
                pod["gpuLimit"] = pod["resourcegpu"]

            pod["envs"].append({"name": "DLWS_ROLE_NAME", "value": "inferenceworker"})
            pod["envs"].append({"name": "DLWS_NUM_GPU_PER_WORKER", "value": 1})

            pod_path = job.get_hostpath(job.job_path, "master")
            pod["mountpoints"].append({"name": "pod", "containerPath": "/pod", "hostPath": pod_path, "enabled": True})


            pod["podName"] = job.job_id
            pod["deployment_replicas"] = params["resourcegpu"]
            pod["gpu_per_pod"] = 1
            k8s_deployment = self.generate_deployment(pod)
            k8s_pods.append(k8s_deployment)

        return k8s_pods, None

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
        for plugin, config in plugins.items():
            if plugin == "blobfuse" and isinstance(plugins["blobfuse"], list):
                for bf in plugins["blobfuse"]:
                    k8s_secret = self.generate_secret(bf)
                    k8s_secrets.append(k8s_secret)
        return k8s_secrets

    def generate_secret(self, plugin):
        assert self.secret_template is not None
        assert isinstance(self.template, Template)
        secret_yaml = self.secret_template.render(plugin=plugin)
        return yaml.full_load(secret_yaml)
