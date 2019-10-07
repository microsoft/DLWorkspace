import os
import sys
import uuid
import datetime
import random
import json
import copy
import yaml
from jinja2 import Template
from job import Job

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../utils"))
from config import config
from osUtils import mkdirsAsUser


class DistPodTemplate():
    def __init__(self, template, enable_custom_scheduler=False):
        self.template = template
        self.enable_custom_scheduler = enable_custom_scheduler

    @staticmethod
    def generate_launch_script(dist_role, dist_role_idx, user_id, job_path, cmd):
        # change ssh folder permission here because the setup permission
        #  script in launch_ps_job function may have race condition with init_user.sh script.
        # results in no such user error

        local_pod_path = os.path.join(config["storage-mount-path"], "work/", job_path, "{}-{}".format(dist_role, dist_role_idx))
        if not os.path.exists(local_pod_path):
            mkdirsAsUser(local_pod_path, user_id)
        file_name = "job_command.sh"
        launch_script_file = os.path.join(local_pod_path, file_name)
        with open(launch_script_file, 'w') as f:
            f.write(cmd)
        f.close()

        launchCMD = ["bash", "/pod/scripts/bootstrap.sh"]
        return launchCMD

    def generate_pod(self, pod):
        assert(isinstance(self.template, Template))

        dist_id = pod["distId"]
        job_id = pod["jobId"]
        job_path = pod["jobPath"]

        pod["podName"] = "{}-{}".format(job_id, dist_id)

        random.seed(datetime.datetime.now())
        if "hostNetwork" in pod and pod["hostNetwork"]:
            pod["sshPort"] = random.randint(40000, 49999)
        else:
            pod["sshPort"] = int(random.random() * 1000 + 3000)

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
        pod["labels"].append({"name": "sshPort", "value": pod["sshPort"]})

        cmd = pod["cmd"]
        pod["LaunchCMD"] = DistPodTemplate.generate_launch_script(pod["distRole"], pod["distRoleIdx"], pod["userId"], job_path, cmd)

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
        assert(params["jobtrainingtype"] == "PSDistJob")

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
        assignedRack = job.get_rack()
        if assignedRack is not None:
            params["nodeSelector"]["rack"] = assignedRack

        params["numworker"] = int(params["numpsworker"])
        params["numps"] = int(params["numps"])

        if "envs" not in params:
            params["envs"] = []
        params["envs"].append({"name": "DLWS_NUM_GPU_PER_WORKER", "value": params["resourcegpu"]})

        if "hostNetwork" in params and params["hostNetwork"]:
            params["envs"].append({"name": "DLWS_HOST_NETWORK", "value": "enable"})
        params["envs"].append({"name": "DLWS_WORKER_NUM", "value": params["numworker"]})

        pods = []
        nums = {"ps": int(params["numps"]), "worker": int(params["numpsworker"])}
        for role in ["ps", "worker"]:
            for idx in range(nums[role]):
                pod = copy.deepcopy(params)
                pod["distRole"] = role
                pod["distRoleIdx"] = idx
                pod["distId"] = "%s%d" % (role, idx)
                # mount /pod
                local_pod_path = job.get_hostpath(job.job_path, "%s-%d" % (role, idx))
                pod["mountpoints"].append({"name": "pod", "containerPath": "/pod", "hostPath": local_pod_path, "enabled": True})


                pods.append(pod)

        k8s_pods = []
        for pod in pods:
            k8s_pod = self.generate_pod(pod)
            k8s_pods.append(k8s_pod)

        return k8s_pods, None
