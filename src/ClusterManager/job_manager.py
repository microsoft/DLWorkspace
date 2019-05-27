import json
import os
import time
import argparse
import uuid
import subprocess
import sys
import datetime
import copy


sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../storage"))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../utils"))

from jobs_tensorboard import GenTensorboardMeta
import k8sUtils
import joblog_manager
from osUtils import mkdirsAsUser

import yaml
from jinja2 import Environment, FileSystemLoader, Template
from config import config, GetStoragePath, GetWorkPath
from DataHandler import DataHandler
from node_manager import create_log
from node_manager import get_cluster_status
import base64
from ResourceInfo import ResourceInfo

import re

import thread
import threading
import random

import logging
import logging.config


nvidiaDriverPath = config["nvidiaDriverPath"]



def printlog(msg):
    print("%s - %s" % (datetime.datetime.utcnow().strftime("%x %X"),msg))

def LoadJobParams(jobParamsJsonStr):
    return json.loads(jobParamsJsonStr)

def cmd_exec(cmdStr):
    try:
        output = subprocess.check_output(["bash","-c", cmdStr])
    except Exception as e:
        print(e)
        output = ""
    return output






def SubmitJob(job):
    jobParams = json.loads(base64.b64decode(job["jobParams"]))
    if jobParams["jobtrainingtype"] == "RegularJob":
        SubmitRegularJob(job)
    elif jobParams["jobtrainingtype"] == "PSDistJob":
        SubmitPSDistJob(job)

def CheckMountPoints(mplist, mp):
    ret = True
    for item in mplist:
        if item["name"] == mp["name"] or item["containerPath"] == mp["containerPath"] or item["hostPath"] == mp["hostPath"]:
            ret = False
    return ret

def SubmitRegularJob(job):
    ret = {}
    dataHandler = DataHandler()

    try:
        jobParams = json.loads(base64.b64decode(job["jobParams"]))

        jobParams["pvc_job"] = "jobs-" + jobParams["jobId"]
        jobParams["pvc_work"] = "work-" + jobParams["jobId"]
        jobParams["pvc_data"] = "storage-" + jobParams["jobId"]


        if "jobPath" not in jobParams or len(jobParams["jobPath"].strip()) == 0:
            dataHandler.SetJobError(jobParams["jobId"],"ERROR: job-path does not exist")
            return False

        if "workPath" not in jobParams or len(jobParams["workPath"].strip()) == 0:
            dataHandler.SetJobError(jobParams["jobId"],"ERROR: work-path does not exist")
            return False

        #if "dataPath" not in jobParams or len(jobParams["dataPath"].strip()) == 0:
        #    dataHandler.SetJobError(jobParams["jobId"],"ERROR: data-path does not exist")
        #    return False


        jobPath,workPath,dataPath = GetStoragePath(jobParams["jobPath"],jobParams["workPath"],jobParams["dataPath"])


        localJobPath = os.path.join(config["storage-mount-path"],jobPath)

        if not os.path.exists(localJobPath):
            if "userId" in jobParams:
                mkdirsAsUser(localJobPath,jobParams["userId"])
                mkdirsAsUser(os.path.join(localJobPath,"models"),jobParams["userId"])
            else:
                mkdirsAsUser(localJobPath,"0")
                mkdirsAsUser(os.path.join(localJobPath,"models"),"0")

        jobParams["LaunchCMD"] = ""
        if "cmd" not in jobParams:
            jobParams["cmd"] = ""

        if isinstance(jobParams["cmd"], basestring) and not jobParams["cmd"] == "":
            launchScriptPath = os.path.join(localJobPath,"launch-%s.sh" % jobParams["jobId"])
            with open(launchScriptPath, 'w') as f:
                f.write("#!/bin/bash -x\n")
                f.write("mkdir /opt; \n")
                f.write("echo 'localhost slots=%s' | tee -a /opt/hostfile; \n" % jobParams["resourcegpu"])
                # TODO refine it later
                f.write("bash /dlws/init_user.sh && runuser -l ${DLWS_USER_NAME} -c '%s'\n" % jobParams["cmd"])
            f.close()
            if "userId" in jobParams:
                os.system("chown -R %s %s" % (jobParams["userId"], launchScriptPath))
            jobParams["LaunchCMD"] = "[\"bash\", \"/job/launch-%s.sh\"]" % jobParams["jobId"]


        jobParams["jobDescriptionPath"] = "jobfiles/" + time.strftime("%y%m%d") + "/" + jobParams["jobId"] + "/" + jobParams["jobId"] + ".yaml"

        jobParams["jobNameLabel"] = ''.join(e for e in jobParams["jobName"] if e.isalnum())

        ENV = Environment(loader=FileSystemLoader("/"))

        jobTempDir = os.path.join(config["root-path"],"Jobs_Templete")
        jobTemp = os.path.join(jobTempDir, "RegularJob.yaml.template")

        jobParams["hostjobPath"] = os.path.join(config["storage-mount-path"], jobPath)
        jobParams["hostworkPath"] = os.path.join(config["storage-mount-path"], workPath)
        jobParams["hostdataPath"] = os.path.join(config["storage-mount-path"], dataPath)
        jobParams["nvidiaDriverPath"] = nvidiaDriverPath


        jobParams["rest-api"] = config["rest-api"]

        if "mountpoints" not in jobParams:
            jobParams["mountpoints"] = []
        for onemount in jobParams["mountpoints"]:
            onemount["name"] = onemount["containerPath"].replace("/","")

        # mp = {"name":"nvidia-driver","containerPath":"/usr/local/nvidia","hostPath":nvidiaDriverPath, "enabled":True}
        # if CheckMountPoints(jobParams["mountpoints"],mp):
        #    jobParams["mountpoints"].append(mp)

        mp = {"name":"job","containerPath":"/job","hostPath":jobParams["hostjobPath"], "enabled":True}
        if CheckMountPoints(jobParams["mountpoints"],mp):
            jobParams["mountpoints"].append(mp)

        mp = {"name":"work","containerPath":"/work","hostPath":jobParams["hostworkPath"], "enabled":True}
        if CheckMountPoints(jobParams["mountpoints"],mp):
            jobParams["mountpoints"].append(mp)

        mp = {"name":"data","containerPath":"/data","hostPath":jobParams["hostdataPath"], "enabled":True}
        if CheckMountPoints(jobParams["mountpoints"],mp):
            jobParams["mountpoints"].append(mp)

        userAlias = getAlias(jobParams["userName"])

        mp = {"name":"sshkey","containerPath":"/home/%s/.ssh" % userAlias,"hostPath":os.path.join(config["storage-mount-path"], GetWorkPath(userAlias)+"/.ssh"), "readOnly":True, "enabled":True}
        if CheckMountPoints(jobParams["mountpoints"],mp):
            jobParams["mountpoints"].append(mp)

        for idx in range(len(jobParams["mountpoints"])):
            if "name" not in jobParams["mountpoints"][idx]:
                jobParams["mountpoints"][idx]["name"] = str(uuid.uuid4()).replace("-","")


        jobParams["pod_ip_range"] = config["pod_ip_range"]
        if "usefreeflow" in config:
            jobParams["usefreeflow"] = config["usefreeflow"]
        else:
            jobParams["usefreeflow"] = False

        print ("Render Job: %s" % jobParams)
        jobDescriptionList = []

        pods = []
        if "hyperparametername" in jobParams and "hyperparameterstartvalue" in jobParams and "hyperparameterendvalue" in jobParams and "hyperparameterstep" in jobParams:
            i = int(jobParams["hyperparameterstartvalue"])
            end = int(jobParams["hyperparameterendvalue"])
            step = int(jobParams["hyperparameterstep"])
            c = 0
            while (i <= end):
                pod = {}
                pod["podName"] = jobParams["jobId"]+"-pod-"+str(c)
                pod["envs"] = [{"name":jobParams["hyperparametername"],"value":i}]
                i += step
                c += 1
                pods.append(pod)
        else:
                pod = {}
                pod["podName"] = jobParams["jobId"]
                pod["envs"] = []
                pods.append(pod)

        if "env" not in jobParams:
            jobParams["env"] = []
        jobParams["commonenv"] = copy.copy(jobParams["env"])


        for pod in pods:
            jobParams["podName"] = pod["podName"]
            jobParams["env"] = jobParams["commonenv"] + pod["envs"]

            if "kube_custom_scheduler" in config and config["kube_custom_scheduler"]:
                container = {}
                container["requests"] = {"alpha.gpu/numgpu" : int(jobParams["resourcegpu"])}
                podInfo = {}
                podInfo["podname"] = jobParams["podName"]
                if "useGPUTopology" in jobParams and jobParams["useGPUTopology"]:
                    # add topology constraints explicitly - for testing
                    # if (jobParams["resourcegpu"] >= 2):
                    #     # both cards in same inner group
                    #     container["requests"]["alpha/grpresource/gpugrp1/0/gpugrp0/0/gpu/0/cards"] = 1
                    #     container["requests"]["alpha/grpresource/gpugrp1/0/gpugrp0/0/gpu/1/cards"] = 1
                    # if (jobParams["resourcegpu"] >= 3):
                    #     container["requests"]["alpha/grpresource/gpugrp1/0/gpugrp0/1/gpu/2/cards"] = 1
                    # if (jobParams["resourcegpu"] >= 4):
                    #     container["requests"]["alpha/grpresource/gpugrp1/0/gpugrp0/1/gpu/3/cards"] = 1
                    # if (jobParams["resourcegpu"] >= 5):
                    #     container["requests"]["alpha/grpresource/gpugrp1/1/gpugrp0/2/gpu/4/cards"] = 1
                    # if (jobParams["resourcegpu"] >= 6):
                    #     container["requests"]["alpha/grpresource/gpugrp1/1/gpugrp0/2/gpu/5/cards"] = 1
                    # if (jobParams["resourcegpu"] >= 7):
                    #     container["requests"]["alpha/grpresource/gpugrp1/1/gpugrp0/3/gpu/6/cards"] = 1
                    # if (jobParams["resourcegpu"] >= 8):
                    #     container["requests"]["alpha/grpresource/gpugrp1/1/gpugrp0/3/gpu/7/cards"] = 1
                    podInfo["requests"] = {"alpha.gpu/gpu-generate-topology" : 1}
                else:
                    # for cases when desired topology is explictly given or not desired
                    podInfo["requests"] = {"alpha.gpu/gpu-generate-topology" : 0}
                podInfo["runningcontainer"] = {jobParams["podName"] : container}

                if "annotations" not in jobParams:
                    jobParams["annotations"] = {}
                jobParams["annotations"]["pod.alpha/DeviceInformation"] = "'" + json.dumps(podInfo) + "'"
                jobParams["resourcegpu"] = 0 # gpu requests specified through annotation

                if "gpuType" in jobParams:
                    if "nodeSelector" not in jobParams:
                        jobParams["nodeSelector"] = {}
                    jobParams["nodeSelector"]["gpuType"] = jobParams["gpuType"]

            # inject gid, uid and user
            # TODO it should return only one entry
            user_info = dataHandler.GetIdentityInfo(jobParams["userName"])[0]
            jobParams["gid"] = user_info["gid"]
            jobParams["uid"] = user_info["uid"]
            jobParams["user"] = userAlias

            template = ENV.get_template(os.path.abspath(jobTemp))
            job_description = template.render(job=jobParams)
            jobDescriptionList.append(job_description)

        jobDescription = "\n---\n".join(jobDescriptionList)

        jobDescriptionPath = os.path.join(config["storage-mount-path"], jobParams["jobDescriptionPath"])
        if not os.path.exists(os.path.dirname(os.path.realpath(jobDescriptionPath))):
            os.makedirs(os.path.dirname(os.path.realpath(jobDescriptionPath)))
        if os.path.isfile(jobDescriptionPath):
            output = k8sUtils.kubectl_delete(jobDescriptionPath)

        with open(jobDescriptionPath, 'w') as f:
            f.write(jobDescription)

        output = k8sUtils.kubectl_create(jobDescriptionPath)
        logging.info("Submitted job %s to k8s, returned with status %s" %(job["jobId"], output))

        ret["output"] = output

        ret["jobId"] = jobParams["jobId"]


        if "userName" not in jobParams:
            jobParams["userName"] = ""

        dataHandler.UpdateJobTextField(jobParams["jobId"],"jobStatus","scheduling")
        dataHandler.UpdateJobTextField(jobParams["jobId"],"jobDescriptionPath",jobParams["jobDescriptionPath"])
        dataHandler.UpdateJobTextField(jobParams["jobId"],"jobDescription",base64.b64encode(jobDescription))


        jobMeta = {}
        jobMeta["jobDescriptionPath"] = jobParams["jobDescriptionPath"]
        jobMeta["jobPath"] = jobParams["jobPath"]
        jobMeta["workPath"] = jobParams["workPath"]
        jobMeta["jobPath"] = jobParams["jobPath"]
        jobMeta["LaunchCMD"] = jobParams["LaunchCMD"]

        jobMetaStr = base64.b64encode(json.dumps(jobMeta))
        dataHandler.UpdateJobTextField(jobParams["jobId"],"jobMeta",jobMetaStr)
    except Exception as e:
        print(e)
        ret["error"] = str(e)
        retries = dataHandler.AddandGetJobRetries(jobParams["jobId"])
        if retries >= 5:
            dataHandler.UpdateJobTextField(jobParams["jobId"],"jobStatus","error")
            dataHandler.UpdateJobTextField(jobParams["jobId"],"errorMsg","Cannot submit job!" + str(e))

    return ret



def SubmitPSDistJob(job):
    ret = {}
    dataHandler = DataHandler()

    try:
        jobParams = json.loads(base64.b64decode(job["jobParams"]))
        jobParams["rest-api"] = config["rest-api"]
        distJobParams = {}
        distJobParams["ps"] = []
        distJobParams["worker"] = []
        assignedRack = None
        if len(config["racks"]) > 0:
            assignedRack = random.choice(config["racks"])

        userAlias = getAlias(jobParams["userName"])

        if jobParams["jobtrainingtype"] == "PSDistJob":
            jobDescriptionList = []
            nums = {"ps":int(jobParams["numps"]),"worker":int(jobParams["numpsworker"])}
            for role in ["ps","worker"]:
                for i in range(nums[role]):
                    distJobParam=copy.deepcopy(jobParams)
                    distJobParam["distId"] = "%s%d" % (role,i)
                    distJobParam["distRole"] = role

                    if "jobPath" not in distJobParam or len(distJobParam["jobPath"].strip()) == 0:
                        dataHandler.SetJobError(distJobParam["jobId"],"ERROR: job-path does not exist")
                        return False
                    if "workPath" not in distJobParam or len(distJobParam["workPath"].strip()) == 0:
                        dataHandler.SetJobError(distJobParam["jobId"],"ERROR: work-path does not exist")
                        return False
                    if "dataPath" not in distJobParam or len(distJobParam["dataPath"].strip()) == 0:
                        dataHandler.SetJobError(distJobParam["jobId"],"ERROR: data-path does not exist")
                        return False
                    distJobParam["distJobPath"] = os.path.join(distJobParam["jobPath"],distJobParam["distId"])
                    jobPath,workPath,dataPath = GetStoragePath(distJobParam["distJobPath"],distJobParam["workPath"],distJobParam["dataPath"])

                    localJobPath = os.path.join(config["storage-mount-path"],jobPath)
                    if not os.path.exists(localJobPath):
                        if "userId" in distJobParam:
                            mkdirsAsUser(localJobPath,distJobParam["userId"])
                        else:
                            mkdirsAsUser(localJobPath,0)

                    # TODO ???
                    if "cmd" not in distJobParam:
                        distJobParam["cmd"] = ""

                    distJobParam["LaunchCMD"] = '["bash", "-c", "bash /dlws/init_user.sh && runuser -l ${DLWS_USER_NAME} -c \'sleep infinity\'"]'

                    distJobParam["jobNameLabel"] = ''.join(e for e in distJobParam["jobName"] if e.isalnum())
                    ENV = Environment(loader=FileSystemLoader("/"))

                    jobTempDir = os.path.join(config["root-path"],"Jobs_Templete")
                    jobTemp = os.path.join(jobTempDir, "DistJob.yaml.template")

                    distJobParam["hostjobPath"] = os.path.join(config["storage-mount-path"], jobPath)
                    distJobParam["hostworkPath"] = os.path.join(config["storage-mount-path"], workPath)
                    distJobParam["hostdataPath"] = os.path.join(config["storage-mount-path"], dataPath)
                    distJobParam["nvidiaDriverPath"] = nvidiaDriverPath

                    if "mountpoints" not in distJobParam:
                        distJobParam["mountpoints"] = []

                    # distJobParam["mountpoints"].append({"name":"nvidia-driver","containerPath":"/usr/local/nvidia","hostPath":nvidiaDriverPath})
                    distJobParam["mountpoints"].append({"name":"job","containerPath":"/job","hostPath":distJobParam["hostjobPath"]})
                    distJobParam["mountpoints"].append({"name":"work","containerPath":"/work","hostPath":distJobParam["hostworkPath"]})
                    distJobParam["mountpoints"].append({"name":"data","containerPath":"/data","hostPath":distJobParam["hostdataPath"]})


                    distJobParam["mountpoints"].append({"name":"rootsshkey","containerPath":"/sshkey/.ssh","hostPath":os.path.join(config["storage-mount-path"], GetWorkPath(userAlias)+"/.ssh"), "readOnly":True, "enabled":True})


                    for idx in range(len(distJobParam["mountpoints"])):
                        if "name" not in distJobParam["mountpoints"][idx]:
                            distJobParam["mountpoints"][idx]["name"] = str(uuid.uuid4()).replace("-","")


                    distJobParam["pod_ip_range"] = config["pod_ip_range"]
                    if "usefreeflow" in config:
                        distJobParam["usefreeflow"] = config["usefreeflow"]
                    else:
                        distJobParam["usefreeflow"] = False

                    distJobParam["numworker"] = int(jobParams["numpsworker"])
                    distJobParam["numps"] = int(jobParams["numps"])



                    random.seed(datetime.datetime.now())
                    if "hostNetwork" in jobParams and jobParams["hostNetwork"]:
                        distJobParam["containerPort"] = random.randint(40001, 49999)
                    else:
                        distJobParam["containerPort"] = int(random.random()*1000+3000)

                    if assignedRack is not None:
                        if "nodeSelector" not in distJobParam:
                            distJobParam["nodeSelector"] = {}
                        distJobParam["nodeSelector"]["rack"] = assignedRack

                    if "gpuType" in distJobParam:
                        if "nodeSelector" not in distJobParam:
                            distJobParam["nodeSelector"] = {}
                        distJobParam["nodeSelector"]["gpuType"] = distJobParam["gpuType"]

                    # inject gid, uid and user
                    # TODO it should return only one entry
                    user_info = dataHandler.GetIdentityInfo(jobParams["userName"])[0]
                    distJobParam["gid"] = user_info["gid"]
                    distJobParam["uid"] = user_info["uid"]
                    distJobParam["user"] = userAlias

                    template = ENV.get_template(os.path.abspath(jobTemp))
                    job_description = template.render(job=distJobParam)

                    jobDescriptionList.append(job_description)

                    distJobParams[role].append(distJobParam)


            jobParams["jobDescriptionPath"] = "jobfiles/" + time.strftime("%y%m%d") + "/" + jobParams["jobId"] + "/" + jobParams["jobId"] + ".yaml"
            jobDescription = "\n---\n".join(jobDescriptionList)


        jobDescriptionPath = os.path.join(config["storage-mount-path"], jobParams["jobDescriptionPath"])
        if not os.path.exists(os.path.dirname(os.path.realpath(jobDescriptionPath))):
            os.makedirs(os.path.dirname(os.path.realpath(jobDescriptionPath)))
        if os.path.isfile(jobDescriptionPath):
            output = k8sUtils.kubectl_delete(jobDescriptionPath)

        with open(jobDescriptionPath, 'w') as f:
            f.write(jobDescription)

        output = k8sUtils.kubectl_create(jobDescriptionPath)

        ret["output"] = output

        ret["jobId"] = jobParams["jobId"]


        if "userName" not in jobParams:
            jobParams["userName"] = ""

        dataHandler.UpdateJobTextField(jobParams["jobId"],"jobStatus","scheduling")
        dataHandler.UpdateJobTextField(jobParams["jobId"],"jobDescriptionPath",jobParams["jobDescriptionPath"])
        dataHandler.UpdateJobTextField(jobParams["jobId"],"jobDescription",base64.b64encode(jobDescription))


        jobMeta = {}
        jobMeta["jobDescriptionPath"] = jobParams["jobDescriptionPath"]
        jobMeta["jobPath"] = jobParams["jobPath"]
        jobMeta["workPath"] = jobParams["workPath"]
        jobMeta["jobPath"] = jobParams["jobPath"]
        jobMeta["LaunchCMD"] = jobParams["cmd"]
        jobMeta["distJobParams"] = distJobParams

        jobMetaStr = base64.b64encode(json.dumps(jobMeta))
        dataHandler.UpdateJobTextField(jobParams["jobId"],"jobMeta",jobMetaStr)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(e)
        ret["error"] = str(e)
        retries = dataHandler.AddandGetJobRetries(jobParams["jobId"])
        if retries >= 5:
            dataHandler.UpdateJobTextField(jobParams["jobId"],"jobStatus","error")
            dataHandler.UpdateJobTextField(jobParams["jobId"],"errorMsg","Cannot submit job!" + str(e))

    return ret

def KillJob(job, desiredState="killed"):
    dataHandler = DataHandler()
    result, detail = k8sUtils.GetJobStatus(job["jobId"])
    dataHandler.UpdateJobTextField(job["jobId"],"jobStatusDetail",base64.b64encode(json.dumps(detail)))
    logging.info("Killing job %s, with status %s, %s" %(job["jobId"], result,detail))
    if "jobDescriptionPath" in job and job["jobDescriptionPath"] is not None:
        jobDescriptionPath = os.path.join(config["storage-mount-path"], job["jobDescriptionPath"])
        if os.path.isfile(jobDescriptionPath):
            if k8sUtils.kubectl_delete(jobDescriptionPath) == 0:
                dataHandler.UpdateJobTextField(job["jobId"],"jobStatus", desiredState)
                return True
            else:
                dataHandler.UpdateJobTextField(job["jobId"],"errorMsg","Cannot delete job from Kubernetes Cluster!")
    else:
        dataHandler.UpdateJobTextField(job["jobId"],"errorMsg","Cannot find job description file!")

    dataHandler.UpdateJobTextField(job["jobId"],"jobStatus","error")
    return False


def getAlias(username):
    if "@" in username:
        username = username.split("@")[0].strip()

    if "/" in username:
        username = username.split("/")[1].strip()

    return username


def ApproveJob(job):
    dataHandler = DataHandler()
    dataHandler.UpdateJobTextField(job["jobId"], "jobStatus", "queued")
    dataHandler.Close()
    return True



def AutoApproveJob(job):
    cluster_status = get_cluster_status()
    jobUser = getAlias(job["userName"])
    jobParams = json.loads(base64.b64decode(job["jobParams"]))
    jobGPU = int(jobParams["resourcegpu"])

    currentGPU = 0
    for user in cluster_status["user_status"]:
        if user["userName"] == jobUser:
            currentGPU = int(user["userGPU"])

    if True or currentGPU == 0 or currentGPU + jobGPU <= 4:
        ApproveJob(job)


UnusualJobs = {}

def UpdateJobStatus(job):
    dataHandler = DataHandler()
    jobParams = json.loads(base64.b64decode(job["jobParams"]))

    if job["jobStatus"] == "scheduling" and jobParams["jobtrainingtype"] == "PSDistJob":
        # launch user command only all pods are ready
        result, detail = k8sUtils.GetJobStatus(job["jobId"])
        if result in ["Failed", "Succeeded"]:
            # TODO shoudn't be here, update status
            dataHandler.UpdateJobTextField(job["jobId"], "jobStatus", result)
            pass
        else:
            # previously status is 'scheduling', and now all pods are ready
            # TODO check all pods are ready
            if k8sUtils.all_pod_ready(job["jobId"]):
                try:
                    launch_ps_dist_job(jobParams)
                except Exception as e:
                    print(e)
            return

    jobPath,workPath,dataPath = GetStoragePath(jobParams["jobPath"],jobParams["workPath"],jobParams["dataPath"])
    localJobPath = os.path.join(config["storage-mount-path"],jobPath)
    logPath = os.path.join(localJobPath,"logs/joblog.txt")


    result, detail = k8sUtils.GetJobStatus(job["jobId"])
    dataHandler.UpdateJobTextField(job["jobId"],"jobStatusDetail",base64.b64encode(json.dumps(detail)))

    logging.info("job %s status: %s,%s" % (job["jobId"], result, json.dumps(detail)))

    jobDescriptionPath = os.path.join(config["storage-mount-path"], job["jobDescriptionPath"]) if "jobDescriptionPath" in job else None
    if "userId" not in jobParams:
        jobParams["userId"]    = "0"
    if result.strip() == "Succeeded":
        joblog_manager.extract_job_log(job["jobId"],logPath,jobParams["userId"])
        dataHandler.UpdateJobTextField(job["jobId"],"jobStatus","finished")
        if jobDescriptionPath is not None and os.path.isfile(jobDescriptionPath):
            k8sUtils.kubectl_delete(jobDescriptionPath)

    elif result.strip() == "Running":
        if job["jobStatus"] != "running":
            dataHandler.UpdateJobTextField(job["jobId"],"jobStatus","running")

    elif result.strip() == "Failed":
        printlog("Job %s fails, cleaning..." % job["jobId"])
        joblog_manager.extract_job_log(job["jobId"],logPath,jobParams["userId"])
        dataHandler.UpdateJobTextField(job["jobId"],"jobStatus","failed")
        dataHandler.UpdateJobTextField(job["jobId"],"errorMsg",detail)
        if jobDescriptionPath is not None and os.path.isfile(jobDescriptionPath):
            k8sUtils.kubectl_delete(jobDescriptionPath)

    elif result.strip() == "Unknown":
        if job["jobId"] not in UnusualJobs:
            UnusualJobs[job["jobId"]] = datetime.datetime.now()
        elif (datetime.datetime.now() - UnusualJobs[job["jobId"]]).seconds > 300:
            del UnusualJobs[job["jobId"]]
            retries = dataHandler.AddandGetJobRetries(job["jobId"])
            if retries >= 5:
                printlog("Job %s fails for more than 5 times, abort" % job["jobId"])
                dataHandler.UpdateJobTextField(job["jobId"],"jobStatus","error")
                dataHandler.UpdateJobTextField(job["jobId"],"errorMsg","cannot launch the job.")
                if jobDescriptionPath is not None and os.path.isfile(jobDescriptionPath):
                    k8sUtils.kubectl_delete(jobDescriptionPath)
            else:
                printlog("Job %s fails in Kubernetes, delete and re-submit the job. Retries %d" % (job["jobId"] , retries))
                SubmitJob(job)
    elif result.strip() == "PendingHostPort":
        printlog("Cannot find host ports for job :%s, re-launch the job with different host ports " % (job["jobId"]))

        SubmitJob(job)

    if result.strip() != "Unknown" and job["jobId"] in UnusualJobs:
        del UnusualJobs[job["jobId"]]



def run_dist_cmd_on_pod(podId, cmd, outputfile):
    remotecmd = "exec %s -- %s" % (podId,cmd)
    print(remotecmd)
    k8sUtils.kubectl_exec_output_to_file(remotecmd,outputfile)



class Kube_RemoteCMD_Thread(threading.Thread):
    def __init__(self, jobId, podId, cmd, outputfile):
        threading.Thread.__init__(self)
        self.jobId = jobId
        self.podId = podId
        self.cmd = cmd
        self.outputfile = outputfile
    def run(self):
        run_dist_cmd_on_pod(self.podId, self.cmd, self.outputfile)


# TODO remove duplicate code later
def is_ssh_server_ready(pod_name):
    bash_script = "sudo service ssh status"
    output = k8sUtils.kubectl_exec("exec %s %s" % (pod_name, " -- " + bash_script))
    if output == "":
        return False
    return True

# TODO remove duplicate code later
def query_ssh_port(pod_name):
    bash_script = "grep ^Port /etc/ssh/sshd_config | cut -d' ' -f2"
    ssh_port = k8sUtils.kubectl_exec("exec %s %s" % (pod_name, " -- " + bash_script))
    return int(ssh_port)

# TODO remove duplicate code later
def start_ssh_server(pod_name, user_name, ssh_port=22, host_network=False):
    '''Setup the ssh server in container, and return the listening port.'''
    bash_script = "sudo bash -c 'apt-get update && apt-get install -y openssh-server && cd /home/" + user_name + " && mkdir -p ssh && chmod 700 ssh && cat .ssh/id_rsa.pub >> ssh/authorized_keys && chmod 600 ssh/authorized_keys && sed -i \"s/^[#]*AuthorizedKeysFile.*/AuthorizedKeysFile      %h\/ssh\/authorized_keys/\" /etc/ssh/sshd_config && service ssh restart'"

    # ssh_port = 22

    # modify the script for HostNewtork
    # if the ssh_port is default value 22, randomly choose one
    if host_network and ssh_port==22:
        ssh_port = random.randint(40001, 49999)
        # bash_script = "sed -i '/^Port 22/c Port "+str(ssh_port)+"' /etc/ssh/sshd_config && "+bash_script
        # TODO refine the script later
        bash_script = "sudo bash -c 'apt-get update && apt-get install -y openssh-server && sed -i \"s/^Port 22/c Port " + str(ssh_port) + "/\" /etc/ssh/sshd_config && cd /home/" + user_name + " && mkdir -p ssh && chmod 700 ssh && cat .ssh/id_rsa.pub >> ssh/authorized_keys && chmod 600 ssh/authorized_keys && sed -i \"s/^[#]*AuthorizedKeysFile.*/AuthorizedKeysFile      %h\/ssh\/authorized_keys/\" /etc/ssh/sshd_config && service ssh restart'"

    # TODO setup reasonable timeout
    # output = k8sUtils.kubectl_exec("exec %s %s" % (jobId, " -- " + bash_script), 1)
    output = k8sUtils.kubectl_exec("exec %s %s" % (pod_name, " -- " + bash_script))
    if output == "":
        raise Exception("Failed to setup ssh server in container. JobId: %s " % pod_name)
    return ssh_port


def launch_ps_dist_job(jobParams):
    job_id = jobParams["jobId"]
    pods = k8sUtils.GetPod("run=" + job_id)

    # if any pod is not up, return
    if "items" not in pods or len(pods["items"]) != (int(jobParams["numpsworker"]) + int(jobParams["numps"])):
        return
    # if any pod is not ready, return
    pod_status = [k8sUtils.check_pod_status(pod) for pod in pods["items"]]
    if any([status != "Running" for status in pod_status]):
        return

    user_name = getAlias(jobParams["userName"])
    if "hostNetwork" in jobParams and jobParams["hostNetwork"]:
        host_network = True
    else:
        host_network = False

    # setup ssh server
    for [idx, pod] in enumerate(pods["items"]):
        pod_name = pod["metadata"]["name"]
        dist_port = pod["metadata"]["labels"]["distPort"]
        # quit if can't setup ssh server
        ssh_port = start_ssh_server(pod_name, user_name, dist_port, host_network)

    # generate ssh config
    ssh_config = """
Host %s
  HostName %s
  Port %s
  User %s
  StrictHostKeyChecking no
  UserKnownHostsFile /dev/null
                """
    sshconfigstr = ""
    for [idx, pod] in enumerate(pods["items"]):
        pod_ip = pod["status"]["podIP"]
        dist_port = pod["metadata"]["labels"]["distPort"]
        role = pod["metadata"]["labels"]["distRole"]

        # TODO hostNetwork
        if host_network:
            sshconfigstr += (ssh_config % (role + "-"+str(idx), pod_ip, str(dist_port), user_name) + "\n")
        else:
            sshconfigstr += (ssh_config % (role + "-"+str(idx), pod_ip, 22, user_name) + "\n")

    # config ssh client
    for [idx, pod] in enumerate(pods["items"]):
        pod_name = pod["metadata"]["name"]
        # TODO need to handle the config override problem
        bash_script = "cat > /home/" + user_name + "/.ssh/config <<EOF " + sshconfigstr + "\nEOF"
        print("override ssh client config: %s" % bash_script)
        k8sUtils.kubectl_exec("exec %s -- bash -c \'%s\'" % (pod_name, bash_script))

    # execute user command
    k8sUtils.kubectl_exec("exec %s -- runuser -l ${DLWS_USER_NAME} <<EOF %s \nEOF" % (pod_name, jobParams["cmd"]))

    # update job status
    dataHandler = DataHandler()
    dataHandler.UpdateJobTextField(job_id, "jobStatus", "running")


def create_log( logdir = '/var/log/dlworkspace' ):
    if not os.path.exists( logdir ):
        os.system("mkdir -p " + logdir )
    with open('logging.yaml') as f:
        logging_config = yaml.load(f)
        f.close()
        logging_config["handlers"]["file"]["filename"] = logdir+"/jobmanager.log"
        logging.config.dictConfig(logging_config)


def JobInfoSorter(elem):
    return elem["sortKey"]


def TakeJobActions(jobs):
    dataHandler = DataHandler()
    vcList = dataHandler.ListVCs()
    dataHandler.Close()

    localResInfo = ResourceInfo()
    globalResInfo = ResourceInfo()

    for vc in vcList:
        localResInfo.Add(ResourceInfo(vc["vcName"], json.loads(vc["quota"])))
        globalResInfo.Add(ResourceInfo("", json.loads(vc["quota"])))

    jobsInfo = []
    for job in jobs:
        if job["jobStatus"] == "queued" or job["jobStatus"] == "scheduling" or job["jobStatus"] == "running":
            singleJobInfo = {}
            singleJobInfo["job"] = job
            singleJobInfo["jobParams"] = json.loads(base64.b64decode(job["jobParams"]))
            jobGpuType = "any"
            if "gpuType" in singleJobInfo["jobParams"]:
                jobGpuType = singleJobInfo["jobParams"]["gpuType"]
            singleJobInfo["localResInfo"] = ResourceInfo.FromTypeAndCount(job["vcName"], jobGpuType, singleJobInfo["jobParams"]["resourcegpu"])
            singleJobInfo["globalResInfo"] = ResourceInfo.FromTypeAndCount("", jobGpuType, singleJobInfo["jobParams"]["resourcegpu"])
            singleJobInfo["sortKey"] = str(job["jobTime"])
            if singleJobInfo["jobParams"]["preemptionAllowed"]:
                singleJobInfo["sortKey"] = "1_" + singleJobInfo["sortKey"]
            else:
                singleJobInfo["sortKey"] = "0_" + singleJobInfo["sortKey"]
            singleJobInfo["allowed"] = False
            jobsInfo.append(singleJobInfo)

    jobsInfo.sort(key=JobInfoSorter)

    logging.info("TakeJobActions : local resources : %s" % (localResInfo.CategoryToCountMap))
    logging.info("TakeJobActions : global resources : %s" % (globalResInfo.CategoryToCountMap))

    for sji in jobsInfo:
        logging.info("TakeJobActions : job : %s : %s : %s" % (sji["jobParams"]["jobName"], sji["localResInfo"].CategoryToCountMap, sji["sortKey"]))
        if sji["jobParams"]["preemptionAllowed"]:
            localResInfo.UnblockResourceCategory(sji["localResInfo"])

        if (localResInfo.CanSatisfy(sji["localResInfo"])):
            localResInfo.Subtract(sji["localResInfo"])
            globalResInfo.Subtract(sji["globalResInfo"])
            sji["allowed"] = True
            logging.info("TakeJobActions : local assignment : %s : %s" % (sji["jobParams"]["jobName"], sji["localResInfo"].CategoryToCountMap))
        elif not sji["jobParams"]["preemptionAllowed"]:
            localResInfo.BlockResourceCategory(sji["localResInfo"]) #FIFO scheduling

    #logging.info("TakeJobActions : local resources : %s" % (localResInfo.CategoryToCountMap))
    #logging.info("TakeJobActions : global resources : %s" % (globalResInfo.CategoryToCountMap))

    for sji in jobsInfo:
        if (sji["jobParams"]["preemptionAllowed"] and sji["allowed"] == False):
            if globalResInfo.CanSatisfy(sji["globalResInfo"]):
                logging.info("TakeJobActions : job : %s : %s" % (sji["jobParams"]["jobName"], sji["globalResInfo"].CategoryToCountMap))
                # Strict FIFO policy not required for global (bonus) tokens since these jobs are anyway pre-emptible.
                globalResInfo.Subtract(sji["globalResInfo"])
                sji["allowed"] = True
                logging.info("TakeJobActions : global assignment : %s : %s" % (sji["jobParams"]["jobName"], sji["globalResInfo"].CategoryToCountMap))

    logging.info("TakeJobActions : global resources : %s" % (globalResInfo.CategoryToCountMap))

    for sji in jobsInfo:
        if sji["job"]["jobStatus"] == "queued" and sji["allowed"] == True:
            SubmitJob(sji["job"])
            logging.info("TakeJobActions : submitting job : %s : %s : %s" % (sji["jobParams"]["jobName"], sji["jobParams"]["jobId"], sji["sortKey"]))
        elif (sji["job"]["jobStatus"] == "scheduling" or sji["job"]["jobStatus"] == "running") and sji["allowed"] == False:
            KillJob(sji["job"], "queued")
            logging.info("TakeJobActions : pre-empting job : %s : %s : %s" % (sji["jobParams"]["jobName"], sji["jobParams"]["jobId"], sji["sortKey"]))

    logging.info("TakeJobActions : job desired actions taken")


def Run():

    while True:

        try:
            config["racks"] = k8sUtils.get_node_labels("rack")
            config["skus"] = k8sUtils.get_node_labels("sku")
        except Exception as e:
            print(e)

        try:
            dataHandler = DataHandler()
            pendingJobs = dataHandler.GetPendingJobs()
            TakeJobActions(pendingJobs)

            pendingJobs = dataHandler.GetPendingJobs()
            logging.info("Updating status for %d jobs" % len(pendingJobs))
            for job in pendingJobs:
                try:
                    logging.info("Processing job: %s, status: %s" % (job["jobId"], job["jobStatus"]))
                    if job["jobStatus"] == "killing":
                        KillJob(job, "killed")
                    elif job["jobStatus"] == "pausing":
                        KillJob(job, "paused")
                    elif job["jobStatus"] == "scheduling" or job["jobStatus"] == "running" :
                        UpdateJobStatus(job)
                    elif job["jobStatus"] == "unapproved" :
                        AutoApproveJob(job)
                except Exception as e:
                    logging.info(e)
        except Exception as e:
            print(str(e))

        time.sleep(1)


if __name__ == '__main__':
    Run()
    #print k8sUtils.get_pod_events("d493d41c-45ea-4e85-8ca4-01c3533cd727")
