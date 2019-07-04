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
    def generate_launch_cmd(role, user_alias, job_path, worker_num, cmd):
        # change ssh folder permission here because the setup permission
        #  script in launch_ps_job function may have race condition with init_user.sh script.
        # results in no such user error
        if role == "ps":
            launchCMD = """
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
            launchCMD = """
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
        return launchCMD

    def generate_pod(self, job, pod):
        # TODO
        distJobParam = pod

        role = distJobParam["distRole"]
        localJobPath = os.path.join(config["storage-mount-path"], "work/", distJobParam["distJobPath"])
        userAlias = distJobParam["user"]
        idx = distJobParam["distRoleIdx"]

        job_path = distJobParam["jobPath"]
        worker_num = distJobParam["numpsworker"]
        cmd = distJobParam["cmd"]
        launchCMD = DistPodTemplate.generate_launch_cmd(role, userAlias, job_path, worker_num, cmd)

        launchScriptPath = os.path.join(localJobPath, "launch-%s-%s%d.sh" % (distJobParam["jobId"], role, idx))
        # TODO need to set up user for distribute jobs
        with open(launchScriptPath, 'w') as f:
            f.write(launchCMD)
        f.close()

        launchScriptInContainer = "bash /job/launch-%s-%s%d.sh" % (distJobParam["jobId"], role, idx)

        distJobParam["LaunchCMD"] = '["bash", "-c", "bash /dlws/init_user.sh &> /job/init_user_script.log && runuser -l ${DLWS_USER_NAME} -c \'%s\'"]' % launchScriptInContainer

        distJobParam["jobNameLabel"] = ''.join(e for e in distJobParam["jobName"] if e.isalnum())

        jobPath = "work/" + distJobParam["distJobPath"]
        workPath = "work/" + distJobParam["workPath"]
        dataPath = "storage/" + distJobParam["dataPath"]

        distJobParam["hostjobPath"] = os.path.join(config["storage-mount-path"], jobPath)
        distJobParam["hostworkPath"] = os.path.join(config["storage-mount-path"], workPath)
        distJobParam["hostdataPath"] = os.path.join(config["storage-mount-path"], dataPath)

        if "mountpoints" not in distJobParam:
            distJobParam["mountpoints"] = []

        distJobParam["mountpoints"].append({"name": "job", "containerPath": "/job", "hostPath": distJobParam["hostjobPath"]})
        distJobParam["mountpoints"].append({"name": "work", "containerPath": "/work", "hostPath": distJobParam["hostworkPath"]})
        distJobParam["mountpoints"].append({"name": "data", "containerPath": "/data", "hostPath": distJobParam["hostdataPath"]})

        for idx in range(len(distJobParam["mountpoints"])):
            if "name" not in distJobParam["mountpoints"][idx]:
                distJobParam["mountpoints"][idx]["name"] = str(uuid.uuid4()).replace("-", "")

        distJobParam["pod_ip_range"] = job.get_pod_ip_range()
        distJobParam["usefreeflow"] = job.is_freeflow_enabled()

        distJobParam["numworker"] = int(distJobParam["numpsworker"])
        distJobParam["numps"] = int(distJobParam["numps"])

        random.seed(datetime.datetime.now())
        if "hostNetwork" in distJobParam and distJobParam["hostNetwork"]:
            distJobParam["sshPort"] = random.randint(40000, 49999)
        else:
            distJobParam["sshPort"] = int(random.random() * 1000 + 3000)

        assignedRack = job.get_rack()
        if assignedRack is not None:
            if "nodeSelector" not in distJobParam:
                distJobParam["nodeSelector"] = {}
            distJobParam["nodeSelector"]["rack"] = assignedRack

        if "gpuType" in distJobParam:
            if "nodeSelector" not in distJobParam:
                distJobParam["nodeSelector"] = {}
            distJobParam["nodeSelector"]["gpuType"] = distJobParam["gpuType"]

        job_description = self.template.render(job=distJobParam)

        return job_description

    def generate_pods(self, job):
        # TODO
        jobParams = job.params

        pods = []

        nums = {"ps": int(jobParams["numps"]), "worker": int(jobParams["numpsworker"])}
        for role in ["ps", "worker"]:
            for idx in range(nums[role]):
                distJobParam = copy.deepcopy(jobParams)

                distJobParam["distId"] = "%s%d" % (role, idx)
                distJobParam["distRole"] = role
                distJobParam["distRoleIdx"] = idx

                # TODO
                distJobParam["distJobPath"] = os.path.join(job.job_path, distJobParam["distId"])
                localJobPath = os.path.join(config["storage-mount-path"], "work/", distJobParam["distJobPath"])
                if not os.path.exists(localJobPath):
                    if "userId" in distJobParam:
                        mkdirsAsUser(localJobPath, distJobParam["userId"])
                    else:
                        mkdirsAsUser(localJobPath, 0)

                pod_template = DistPodTemplate(job.get_dist_template())
                job_description = pod_template.generate_pod(job, distJobParam)

                pods.append(job_description)

        return pods