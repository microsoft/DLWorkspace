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

import re

import thread
import threading
import random

import logging
import logging.config


nvidiaDriverPath = config["nvidiaDriverPath"]



def printlog(msg):
    print "%s - %s" % (datetime.datetime.utcnow().strftime("%x %X"),msg)

def LoadJobParams(jobParamsJsonStr):
    return json.loads(jobParamsJsonStr)

def cmd_exec(cmdStr):
    try:
        output = subprocess.check_output(["bash","-c", cmdStr])
    except Exception as e:
        print e
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
                f.write(jobParams["cmd"] + "\n")
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


        jobParams["userNameLabel"] = getAlias(jobParams["userName"])
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

            template = ENV.get_template(os.path.abspath(jobTemp))
            job_description = template.render(job=jobParams)
            jobDescriptionList.append(job_description)

            if ("interactivePort" in jobParams and len(jobParams["interactivePort"].strip()) > 0):
                ports = [p.strip() for p in re.split(",|;",jobParams["interactivePort"]) if len(p.strip()) > 0 and p.strip().isdigit()]
                for portNum in ports:
                    jobParams["serviceId"] = "interactive-" + jobParams["podName"] + "-" + portNum
                    jobParams["port"] = portNum
                    jobParams["port-name"] = "interactive"
                    jobParams["port-type"] = "TCP"

                    serviceTemplate = ENV.get_template(os.path.join(jobTempDir,"KubeSvc.yaml.template"))

                    stemplate = ENV.get_template(serviceTemplate)
                    interactiveMeta = stemplate.render(svc=jobParams)
                    jobDescriptionList.append(interactiveMeta)


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
        print e
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

                    distJobParam["distJobPath"] = os.path.join(distJobParam["jobPath"],distJobParam["distId"])

                    if "workPath" not in distJobParam or len(distJobParam["workPath"].strip()) == 0: 
                        dataHandler.SetJobError(distJobParam["jobId"],"ERROR: work-path does not exist")
                        return False

                    if "dataPath" not in distJobParam or len(distJobParam["dataPath"].strip()) == 0: 
                        dataHandler.SetJobError(distJobParam["jobId"],"ERROR: data-path does not exist")
                        return False

                    jobPath,workPath,dataPath = GetStoragePath(distJobParam["distJobPath"],distJobParam["workPath"],distJobParam["dataPath"])

                    localJobPath = os.path.join(config["storage-mount-path"],jobPath)
                    if not os.path.exists(localJobPath):
                        if "userId" in distJobParam:
                            mkdirsAsUser(localJobPath,distJobParam["userId"])
                        else:
                            mkdirsAsUser(localJobPath,0)


                    distJobParam["LaunchCMD"] = ""
                    if "cmd" not in distJobParam:
                        distJobParam["cmd"] = ""

################One choice is that we only wait for certain time.            
#                    launchCMD = """
##!/bin/bash
#mkdir -p /opt
#echo "[DLWorkspace System]: Waiting for all containers are ready..."
## wait for at most 10 mins. 
#for i in {1..200}; do
#    if [ ! -f /opt/run_dist_job ] || [ ! -f /opt/run_dist_job.sh ]; then
#        sleep 3
#    else
#        break
#    fi
#done
#if [ ! -f /opt/run_dist_job ] || [ ! -f /opt/run_dist_job.sh ]; then
#    echo "[DLWorkspace System]: Waiting for containers: timeout! Restarting..."
#    exit 1
#else
#    echo "[DLWorkspace System]: All containers are ready, launching training job..."
#    chmod +x /opt/run_dist_job.sh
#    /opt/run_dist_job.sh
#fi
#"""

                    if role == "ps":
                        launchCMD = """
#!/bin/bash
mkdir -p /opt
cp -r /sshkey/.ssh /root
chown -R root:root /root/.ssh
echo export LD_PRELOAD=$LD_PRELOAD >> /etc/default/ssh
echo export VNET_PREFIX=$VNET_PREFIX >> /etc/default/ssh
service ssh restart

echo "[DLWorkspace System]: Waiting for all containers are ready..."
while [ ! -f /opt/run_dist_job ] || [ ! -f /opt/run_dist_job.sh ]; do
    sleep 3
done
echo "[DLWorkspace System]: All containers are ready, launching training job..."
chmod +x /opt/run_dist_job.sh
/opt/run_dist_job.sh
"""
                    else:
                        launchCMD = """
#!/bin/bash
mkdir -p /opt
cp -r /sshkey/.ssh /root
chown -R root:root /root/.ssh
echo export LD_PRELOAD=$LD_PRELOAD >> /etc/default/ssh
echo export VNET_PREFIX=$VNET_PREFIX >> /etc/default/ssh
service ssh restart
sleep infinity
"""



                    launchScriptPath = os.path.join(localJobPath,"launch-%s-%s%d.sh" % (distJobParam["jobId"],role,i))
                    with open(launchScriptPath, 'w') as f:
                        f.write(launchCMD)
                    f.close()        
                    distJobParam["LaunchCMD"] = "[\"bash\", \"/job/launch-%s-%s%d.sh\"]" % (distJobParam["jobId"],role,i)



                    distJobParam["jobNameLabel"] = ''.join(e for e in distJobParam["jobName"] if e.isalnum())
                    distJobParam["userNameLabel"] = getAlias(jobParams["userName"])
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

                    userAlias = getAlias(jobParams["userName"])
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
                    distJobParam["containerPort"] = int(random.random()*1000+3000)

                    if assignedRack is not None:
                        if "nodeSelector" not in distJobParam:
                            distJobParam["nodeSelector"] = {}
                        distJobParam["nodeSelector"]["rack"] = assignedRack

                    template = ENV.get_template(os.path.abspath(jobTemp))
                    job_description = template.render(job=distJobParam)

                    jobDescriptionList.append(job_description)

                    distJobParams[role].append(distJobParam)


                    if (role == "ps" and "interactivePort" in distJobParam and len(distJobParam["interactivePort"].strip()) > 0):
                        ports = [p.strip() for p in re.split(",|;",distJobParam["interactivePort"]) if len(p.strip()) > 0 and p.strip().isdigit()]

                        distJobParam["podName"] = distJobParam["jobId"]+"-"+distJobParam["distId"]

                        for portNum in ports:
                            distJobParam["serviceId"] = "interactive-" + distJobParam["podName"] + "-" + portNum
                            distJobParam["port"] = portNum
                            distJobParam["port-name"] = "interactive"
                            distJobParam["port-type"] = "TCP"

                            serviceTemplate = ENV.get_template(os.path.join(jobTempDir,"KubeSvc.yaml.template"))

                            stemplate = ENV.get_template(serviceTemplate)
                            interactiveMeta = stemplate.render(svc=distJobParam)
                            jobDescriptionList.append(interactiveMeta)


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
        jobMeta["LaunchCMD"] = jobParams["LaunchCMD"]
        jobMeta["distJobParams"] = distJobParams

        jobMetaStr = base64.b64encode(json.dumps(jobMeta))
        dataHandler.UpdateJobTextField(jobParams["jobId"],"jobMeta",jobMetaStr)
    except Exception as e:
        print e
        ret["error"] = str(e)
        retries = dataHandler.AddandGetJobRetries(jobParams["jobId"])
        if retries >= 5:
            dataHandler.UpdateJobTextField(jobParams["jobId"],"jobStatus","error")
            dataHandler.UpdateJobTextField(jobParams["jobId"],"errorMsg","Cannot submit job!" + str(e))

    return ret

def KillJob(job):
    dataHandler = DataHandler()
    result, detail = k8sUtils.GetJobStatus(job["jobId"])
    dataHandler.UpdateJobTextField(job["jobId"],"jobStatusDetail",base64.b64encode(json.dumps(detail)))
    logging.info("Killing job %s, with status %s, %s" %(job["jobId"], result,detail))
    if "jobDescriptionPath" in job and job["jobDescriptionPath"] is not None:
        jobDescriptionPath = os.path.join(config["storage-mount-path"], job["jobDescriptionPath"])
        if os.path.isfile(jobDescriptionPath):
            if k8sUtils.kubectl_delete(jobDescriptionPath) == 0:
                dataHandler.UpdateJobTextField(job["jobId"],"jobStatus","killed")
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
    dataHandler.ApproveJob(job["jobId"])
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
        launch_ps_dist_job(jobParams)
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

        if "interactivePort" in jobParams:
            serviceAddress = k8sUtils.GetServiceAddress(job["jobId"])
            serviceAddress = base64.b64encode(json.dumps(serviceAddress))
            dataHandler.UpdateJobTextField(job["jobId"],"endpoints",serviceAddress)

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

def UpdateDistJobStatus(job):
    dataHandler = DataHandler()
    jobParams = json.loads(base64.b64decode(job["jobParams"]))

    if "userId" not in jobParams:
        jobParams["userId"]    = "0"

    jobPath,workPath,dataPath = GetStoragePath(jobParams["jobPath"],jobParams["workPath"],jobParams["dataPath"])
    localJobPath = os.path.join(config["storage-mount-path"],jobPath)
    logPath = os.path.join(localJobPath,"logs/joblog.txt")
    

    result, detail = k8sUtils.GetJobStatus(job["jobId"])
    dataHandler.UpdateJobTextField(job["jobId"],"jobStatusDetail",base64.b64encode(detail))

    logging.info("job %s status: %s,%s" % (job["jobId"], result, json.dumps(detail)))
    
    jobDescriptionPath = os.path.join(config["storage-mount-path"], job["jobDescriptionPath"]) if "jobDescriptionPath" in job else None


    jobId = jobParams["jobId"]
    workerPodInfo = k8sUtils.GetPod("distRole=worker,run=" + jobId)
    psPodInfo = k8sUtils.GetPod("distRole=ps,run=" + jobId)
    if "items" in workerPodInfo and len(workerPodInfo["items"]) == int(jobParams["numpsworker"]) and "items" in psPodInfo and len(psPodInfo["items"]) == int(jobParams["numps"]):
        if job["jobStatus"] == "scheduling" :
            launch_ps_dist_job(jobParams)
        if job["jobStatus"] == "running":
            result, detail = GetDistJobStatus(job["jobId"])
            dataHandler.UpdateJobTextField(job["jobId"],"jobStatusDetail",base64.b64encode(detail))

            printlog("job %s status: %s" % (job["jobId"], result))
    
            jobDescriptionPath = os.path.join(config["storage-mount-path"], job["jobDescriptionPath"]) if "jobDescriptionPath" in job else None

            if result.strip() == "Succeeded":
                joblog_manager.extract_job_log(job["jobId"],logPath,jobParams["userId"])
                dataHandler.UpdateJobTextField(job["jobId"],"jobStatus","finished")
                if jobDescriptionPath is not None and os.path.isfile(jobDescriptionPath):
                    k8sUtils.kubectl_delete(jobDescriptionPath) 

            elif result.strip() == "Running":
                joblog_manager.extract_job_log(job["jobId"],logPath,jobParams["userId"])
                if job["jobStatus"] != "running":
                    dataHandler.UpdateJobTextField(job["jobId"],"jobStatus","running")
                if "interactivePort" in jobParams:
                    serviceAddress = k8sUtils.GetServiceAddress(job["jobId"])
                    serviceAddress = base64.b64encode(json.dumps(serviceAddress))
                    dataHandler.UpdateJobTextField(job["jobId"],"endpoints",serviceAddress)

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

            if result.strip() != "Unknown" and job["jobId"] in UnusualJobs:
                del UnusualJobs[job["jobId"]]

    pass




def run_dist_cmd_on_pod(podId, cmd, outputfile):
    remotecmd = "exec %s -- %s" % (podId,cmd)
    print remotecmd
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


def launch_ps_dist_job(jobParams):
    try:
        jobId = jobParams["jobId"]
        workerPodInfo = k8sUtils.GetPod("distRole=worker,run=" + jobId)
        psPodInfo = k8sUtils.GetPod("distRole=ps,run=" + jobId)
        if "items" in workerPodInfo and len(workerPodInfo["items"]) == int(jobParams["numpsworker"]) and "items" in psPodInfo and len(psPodInfo["items"]) == int(jobParams["numps"]):
            podStatus = [k8sUtils.check_pod_status(pod) for pod in  workerPodInfo["items"] + psPodInfo["items"] ]
            if all([status == "Running" for status in podStatus]):
                ps_pod_names = [pod["metadata"]["name"] for pod in psPodInfo["items"]]
                worker_pod_names = [pod["metadata"]["name"] for pod in workerPodInfo["items"]]

                ps_pod_ips = [pod["status"]["podIP"] for pod in psPodInfo["items"]]
                worker_pod_ips = [pod["status"]["podIP"] for pod in workerPodInfo["items"]]

                worker_gpu_num = [pod["spec"]["containers"][0]["resources"]["requests"]["nvidia.com/gpu"] for pod in workerPodInfo["items"]]

                ps_num = len(psPodInfo["items"])
                worker_num = len(workerPodInfo["items"])

                ps_ports = [int(item["metadata"]["labels"]["distPort"]) for item in psPodInfo["items"]]
                worker_ports = [int(item["metadata"]["labels"]["distPort"]) for item in workerPodInfo["items"]]

                #port range: 30000~31000
                #rndList = range(max(1000,ps_num + worker_num))
                #random.shuffle(rndList)
                #ps_ports = [rndList[i] + 30000 for i in range(ps_num)]
                #worker_ports = [rndList[i + ps_num] + 30000 for i in range(worker_num)]

                ps_hosts = ",".join(["%s:%s" % (ps_pod_ips[i],ps_ports[i]) for i in range(ps_num)])
                worker_hosts = ",".join(["%s:%s" % (worker_pod_ips[i],worker_ports[i]) for i in range(worker_num)])

                ps_files = ["/tmp/" + str(uuid.uuid4()) for i in range(ps_num)]
                worker_files = ["/tmp/" + str(uuid.uuid4()) for i in range(worker_num)]

                #ps_cmd = ["%s --ps_hosts=%s --worker_hosts=%s --job_name=ps --task_index=%d 2>&1 | tee %s" % (jobParams["cmd"], ps_hosts,worker_hosts,i,ps_files[i]) for i in range(ps_num)]
                #worker_cmd = ["%s --ps_hosts=%s --worker_hosts=%s --job_name=worker --task_index=%d 2>&1 | tee %s" % (jobParams["cmd"], ps_hosts,worker_hosts,i,worker_files[i]) for i in range(worker_num)]

                ps_cmd = ["%s 2>&1 | tee %s" % (jobParams["cmd"], ps_files[i]) for i in range(ps_num)]
                worker_cmd = ["%s 2>&1 | tee %s" % (jobParams["cmd"], worker_files[i]) for i in range(worker_num)]


                hostfilecontent = ""
                for workerip,workergpu in zip(worker_pod_ips,worker_gpu_num):
                    hostfilecontent += "%s  slots=%s\n" %(workerip,workergpu)

                error_flag = False
                for i in range(ps_num):
                    os.system("mkdir -p %s" % ps_files[i])
                    psfile = os.path.join(ps_files[i],"run_dist_job.sh")
                    with open(psfile, 'w') as f:
                        f.write(ps_cmd[i] + "\n")
                    f.close()        
                    if "userId" in jobParams:
                        os.system("chown -R %s %s" % (jobParams["userId"], psfile))
                    remotecmd = "cp %s %s:/opt/run_dist_job.sh" % (psfile,ps_pod_names[i])
                    k8sUtils.kubectl_exec(remotecmd)


                    os.system("mkdir -p %s" % ps_files[i])
                    psfile = os.path.join(ps_files[i],"hostfile")
                    with open(psfile, 'w') as f:
                        f.write(hostfilecontent + "\n")
                    f.close()        
                    if "userId" in jobParams:
                        os.system("chown -R %s %s" % (jobParams["userId"], psfile))
                    remotecmd = "cp %s %s:/opt/hostfile" % (psfile,ps_pod_names[i])
                    k8sUtils.kubectl_exec(remotecmd)

                    os.system("mkdir -p %s" % ps_files[i])
                    psfile = os.path.join(ps_files[i],"taskindex")
                    with open(psfile, 'w') as f:
                        f.write(str(i) + "\n")
                    f.close()        
                    if "userId" in jobParams:
                        os.system("chown -R %s %s" % (jobParams["userId"], psfile))
                    remotecmd = "cp %s %s:/opt/taskindex" % (psfile,ps_pod_names[i])
                    k8sUtils.kubectl_exec(remotecmd)

                    k8sUtils.kubectl_exec("exec %s touch /opt/run_dist_job" % ps_pod_names[i])
                    output = k8sUtils.kubectl_exec("exec %s ls /opt/run_dist_job" % ps_pod_names[i])
                    if (output == ""):
                        error_flag = True   

                for i in range(worker_num):
                    os.system("mkdir -p %s" % worker_files[i])
                    workerfile = os.path.join(worker_files[i],"run_dist_job.sh")
                    with open(workerfile, 'w') as f:
                        f.write(worker_cmd[i] + "\n")
                    f.close()    
                    if "userId" in jobParams:
                        os.system("chown -R %s %s" % (jobParams["userId"], workerfile))
                    remotecmd = "cp %s %s:/opt/run_dist_job.sh" % (workerfile,worker_pod_names[i])
                    k8sUtils.kubectl_exec(remotecmd)


                    os.system("mkdir -p %s" % worker_files[i])
                    workerfile = os.path.join(worker_files[i],"hostfile")
                    with open(workerfile, 'w') as f:
                        f.write(hostfilecontent + "\n")
                    f.close()    
                    if "userId" in jobParams:
                        os.system("chown -R %s %s" % (jobParams["userId"], workerfile))
                    remotecmd = "cp %s %s:/opt/hostfile" % (workerfile,worker_pod_names[i])
                    k8sUtils.kubectl_exec(remotecmd)


                    os.system("mkdir -p %s" % worker_files[i])
                    workerfile = os.path.join(worker_files[i],"taskindex")
                    with open(workerfile, 'w') as f:
                        f.write(str(i) + "\n")
                    f.close()    
                    if "userId" in jobParams:
                        os.system("chown -R %s %s" % (jobParams["userId"], workerfile))
                    remotecmd = "cp %s %s:/opt/taskindex" % (workerfile,worker_pod_names[i])
                    k8sUtils.kubectl_exec(remotecmd)


                    k8sUtils.kubectl_exec("exec %s touch /opt/run_dist_job" % worker_pod_names[i])
                    output = k8sUtils.kubectl_exec("exec %s ls /opt/run_dist_job" % worker_pod_names[i])
                    if (output == ""):
                        error_flag = True     
                if not error_flag:
                    dataHandler = DataHandler()
                    dataHandler.UpdateJobTextField(jobParams["jobId"],"jobStatus","running")

                #ps_threads = [Kube_RemoteCMD_Thread(jobId,ps_pod_names[i],ps_cmd[i],ps_logfiles[i]) for i in range(ps_num)]
                #worker_threads = [Kube_RemoteCMD_Thread(jobId,worker_pod_names[i],worker_cmd[i],worker_logfiles[i]) for i in range(worker_num)]
                
                #for t in ps_threads:
                #    t.start()

                #for t in worker_threads:
                #    t.start()


                #while (True):
                    #for t in ps_threads:
                    #    print t.isAlive()
                    #time.sleep(5)

                #cmd = "test"
                #thread.start_new_thread( run_dist_cmd_on_pod,
                #(workerPodInfo["items"][0]["metadata"]["name"], cmd) )
    except Exception as e:
        print e



def create_log( logdir = '/var/log/dlworkspace' ):
    if not os.path.exists( logdir ):
        os.system("mkdir -p " + logdir )
    with open('logging.yaml') as f:
        logging_config = yaml.load(f)
        f.close()
        logging_config["handlers"]["file"]["filename"] = logdir+"/jobmanager.log"
        logging.config.dictConfig(logging_config)


def Run():

    while True:

        try:
            config["racks"] = k8sUtils.get_node_labels("rack")
            config["skus"] = k8sUtils.get_node_labels("sku")
        except Exception as e:
            print e

        try:
            dataHandler = DataHandler()
            pendingJobs = dataHandler.GetPendingJobs()
            printlog("updating status for %d jobs" % len(pendingJobs))
            for job in pendingJobs:
                try:
                    print "Processing job: %s, status: %s" % (job["jobId"], job["jobStatus"])
                    if job["jobStatus"] == "queued":
                        SubmitJob(job)
                    elif job["jobStatus"] == "killing":
                        KillJob(job)
                    elif job["jobStatus"] == "scheduling" or job["jobStatus"] == "running" :
                        UpdateJobStatus(job)
                    elif job["jobStatus"] == "unapproved" :
                        AutoApproveJob(job)
                except Exception as e:
                    print e
        except Exception as e:
            print e

        time.sleep(1)

if __name__ == '__main__':
    Run()
    #print k8sUtils.get_pod_events("d493d41c-45ea-4e85-8ca4-01c3533cd727")
