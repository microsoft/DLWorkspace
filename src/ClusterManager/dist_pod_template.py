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
    def generate_launch_script(dist_id, job_id, user_alias, job_path, worker_num, cmd):
        # change ssh folder permission here because the setup permission
        #  script in launch_ps_job function may have race condition with init_user.sh script.
        # results in no such user error
        if dist_id.startswith("ps"):
            script = """
#!/bin/bash
echo "[DLWorkspace System]: Waiting for all containers are ready..."
while [ ! -f /opt/run_dist_job ]; do
    sleep 3
done

sudo chmod 600 -R /home/{0}/.ssh &>/dev/null;
sudo chmod 700 /home/{0}/.ssh &>/dev/null;
sudo chown -R {0} /home/{0}/.ssh &>/dev/null;

sudo mkdir -p /root/.ssh  &>/dev/null ;
sudo ln -s /home/{0}/.ssh/config /root/.ssh/config  &>/dev/null;
sudo mkdir -p /opt  &>/dev/null;
sudo ln -s /job/hostfile /opt/hostfile &>/dev/null;

JOB_DIR='/home/{1}'
WORKER_NUM={2}
echo $JOB_DIR $WORKER_NUM

all_workers_ready=false
while [ "$all_workers_ready" != true ]
do
    # update it to false if any woker is not ready
    all_workers_ready=true

    for i in $(seq 0 $(( ${{WORKER_NUM}} - 1)) )
    do
        worker="worker${{i}}"
        file="$JOB_DIR/${{worker}}/WORKER_READY"
        #echo $file

        if [ ! -f $file ]; then
        echo "${{worker}} not ready!"
        all_workers_ready=false
        sleep 10
        fi
    done
done

echo "[DLWorkspace System]: All containers are ready, launching training job..."
{3}
""".format(user_alias, job_path, worker_num, cmd)
        else:
            script = """
while [ ! -f /opt/run_dist_job ]; do
    sleep 3
done
sudo chmod 600 -R /home/{0}/.ssh &>/dev/null;
sudo chmod 700 /home/{0}/.ssh &>/dev/null;
sudo chown -R {0} /home/{0}/.ssh  &>/dev/null;
sudo mkdir -p /root/.ssh  &>/dev/null;
sudo ln -s /home/{0}/.ssh/config /root/.ssh/config &>/dev/null;
sudo mkdir -p /opt && sudo ln -s /job/hostfile /opt/hostfile  &>/dev/null;

# TODO mark the worker as 'READY', better to change to '/pod/READY' later
sudo touch /job/WORKER_READY

sleep infinity
""".format(user_alias)

        local_job_path = os.path.join(config["storage-mount-path"], "work/", job_path, dist_id)
        file_name = "launch-%s-%s.sh" % (job_id, dist_id)
        launch_script_file = os.path.join(local_job_path, file_name)
        with open(launch_script_file, 'w') as f:
            f.write(script)
        f.close()

        launchScriptInContainer = "bash /job/launch-%s-%s.sh" % (job_id, dist_id)

        launchCMD = '["bash", "-c", "bash /dlws/init_user.sh &> /job/init_user_script.log && runuser -l ${DLWS_USER_NAME} -c \'%s\'"]' % launchScriptInContainer
        return launchCMD

    def generate_pod(self, pod):
        assert(isinstance(self.template, Template))

        dist_id = pod["distId"]
        job_id = pod["jobId"]
        user_alias = pod["user"]
        job_path = pod["jobPath"]
        worker_num = pod["numpsworker"]
        cmd = pod["cmd"]

        pod["LaunchCMD"] = DistPodTemplate.generate_launch_script(dist_id, job_id, user_alias, job_path, worker_num, cmd)

        random.seed(datetime.datetime.now())
        if "hostNetwork" in pod and pod["hostNetwork"]:
            pod["sshPort"] = random.randint(40000, 49999)
        else:
            pod["sshPort"] = int(random.random() * 1000 + 3000)

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

        pods = []
        nums = {"ps": int(params["numps"]), "worker": int(params["numpsworker"])}
        for role in ["ps", "worker"]:
            for idx in range(nums[role]):
                pod = copy.deepcopy(params)

                pod["distId"] = "%s%d" % (role, idx)
                pod["distRole"] = role
                pod["distRoleIdx"] = idx

                # TODO refine later
                dist_job_path = os.path.join(job.job_path, pod["distId"])
                for mp in pod["mountpoints"]:
                    if mp["name"] == "job":
                        mp["hostPath"] = mp["hostPath"] + "/" + pod["distId"]

                local_job_path = os.path.join(config["storage-mount-path"], "work/", dist_job_path)
                if not os.path.exists(local_job_path):
                    mkdirsAsUser(local_job_path, pod["userId"])

                pods.append(pod)

        k8s_pods = []
        for pod in pods:
            k8s_pod = self.generate_pod(pod)
            k8s_pods.append(k8s_pod)

        return k8s_pods, None
