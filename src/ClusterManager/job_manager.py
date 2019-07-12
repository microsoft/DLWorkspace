import json
import os
import time
import argparse
import uuid
import subprocess
import sys
import datetime
import copy
import traceback


sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../storage"))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../utils"))

from JobRestAPIUtils import GetJobTotalGpu
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
from job import Job, JobSchema
from pod_template import PodTemplate
from dist_pod_template import DistPodTemplate
from job_deployer import JobDeployer



def SubmitJob(job):
    ret = {}
    dataHandler = DataHandler()

    try:
        job["cluster"] = config
        job_object, errors = JobSchema().load(job)
        # TODO assert job_object is a Job
        assert(isinstance(job_object, Job))

        job_object.params = json.loads(base64.b64decode(job["jobParams"]))

        # inject gid, uid and user
        # TODO it should return only one entry
        user_info = dataHandler.GetIdentityInfo(job_object.params["userName"])[0]
        job_object.params["gid"] = user_info["gid"]
        job_object.params["uid"] = user_info["uid"]
        job_object.params["user"] = job_object.get_alias()

        enable_custom_scheduler = job_object.is_custom_scheduler_enabled()
        if job_object.params["jobtrainingtype"] == "RegularJob":
            pod_template = PodTemplate(job_object.get_template(), enable_custom_scheduler)
        elif job_object.params["jobtrainingtype"] == "PSDistJob":
            pod_template = DistPodTemplate(job_object.get_template())
        else:
            dataHandler.SetJobError(job_object.job_id, "ERROR: invalid jobtrainingtype: %s" % job_object.params["jobtrainingtype"])
            return False

        pods, error = pod_template.generate_pods(job_object)
        if error:
            dataHandler.SetJobError(job_object.job_id, "ERROR: %s" % error)
            return False

        job_description = "\n---\n".join([yaml.dump(pod) for pod in pods])
        job_description_path = "jobfiles/" + time.strftime("%y%m%d") + "/" + job_object.job_id + "/" + job_object.job_id + ".yaml"
        local_jobDescriptionPath = os.path.realpath(os.path.join(config["storage-mount-path"], job_description_path))
        if not os.path.exists(os.path.dirname(local_jobDescriptionPath)):
            os.makedirs(os.path.dirname(os.path.realpath(local_jobDescriptionPath)))
        with open(local_jobDescriptionPath, 'w') as f:
            f.write(job_description)

        job_deployer = JobDeployer()
        try:
            pods = job_deployer.create_pods(pods)
            ret["output"] = "Created pods: {}".format([pod.metedata.name for pod in pods])
        except Exception as e:
            ret["output"] = "Error: %s" % e.message
            logging.error(e, exc_info=True)

        ret["jobId"] = job_object.job_id

        dataHandler.UpdateJobTextField(job_object.job_id, "jobStatus", "scheduling")
        dataHandler.UpdateJobTextField(job_object.job_id, "jobDescriptionPath", job_description_path)
        dataHandler.UpdateJobTextField(job_object.job_id, "jobDescription", base64.b64encode(job_description))
        dataHandler.UpdateJobTextField(job_object.job_id, "lastUpdated", datetime.datetime.now().isoformat())

        jobMeta = {}
        jobMeta["jobDescriptionPath"] = job_description_path
        jobMeta["jobPath"] = job_object.job_path
        jobMeta["workPath"] = job_object.work_path
        # the command of the first container
        jobMeta["LaunchCMD"] = pods[0]["spec"]["containers"][0]["command"]

        jobMetaStr = base64.b64encode(json.dumps(jobMeta))
        dataHandler.UpdateJobTextField(job_object.job_id, "jobMeta", jobMetaStr)
    except Exception as e:
        logging.error("Submit job failed: %s" % job, exc_info=True)
        ret["error"] = str(e)
        retries = dataHandler.AddandGetJobRetries(job["jobId"])
        if retries >= 5:
            dataHandler.UpdateJobTextField(job["jobId"], "jobStatus", "error")
            dataHandler.UpdateJobTextField(job["jobId"], "errorMsg", "Cannot submit job!" + str(e))
    dataHandler.Close()
    return ret


def KillJob(job, desiredState="killed"):
    dataHandler = DataHandler()
    result, detail = k8sUtils.GetJobStatus(job["jobId"])
    dataHandler.UpdateJobTextField(job["jobId"], "jobStatusDetail", base64.b64encode(json.dumps(detail)))
    logging.info("Killing job %s, with status %s, %s" % (job["jobId"], result, detail))

    job_deployer = JobDeployer()
    errors = job_deployer.delete_job(job["jobId"])

    if len(errors) == 0:
        dataHandler.UpdateJobTextField(job["jobId"], "jobStatus", desiredState)
        dataHandler.UpdateJobTextField(job["jobId"], "lastUpdated", datetime.datetime.now().isoformat())
        dataHandler.Close()
        return True
    else:
        dataHandler.UpdateJobTextField(job["jobId"], "jobStatus", "error")
        dataHandler.UpdateJobTextField(job["jobId"], "lastUpdated", datetime.datetime.now().isoformat())
        dataHandler.Close()
        logging.error("Kill job failed with errors: {}".format(errors))
        return False


# TODO remove it latter
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
    # TODO: All jobs are currently auto-approved. We need to allow
    # configuring different policies for different VC.
    ApproveJob(job)

    # This block is kept here for reference of the original code.
    # cluster_status = get_cluster_status()
    # jobUser = getAlias(job["userName"])
    # jobParams = json.loads(base64.b64decode(job["jobParams"]))
    # jobGPU = GetJobTotalGpu(jobParams)
    #
    # currentGPU = 0
    # for user in cluster_status["user_status"]:
    #     if user["userName"] == jobUser:
    #         currentGPU = int(user["userGPU"])
    #
    # if True or currentGPU == 0 or currentGPU + jobGPU <= 4:
    #     ApproveJob(job)


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
                    logging.exception("launch ps distributed job failed")
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
        logging.warning("Job %s fails, cleaning...", job["jobId"])
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
                logging.warning("Job %s fails for more than 5 times, abort", job["jobId"])
                dataHandler.UpdateJobTextField(job["jobId"],"jobStatus","error")
                dataHandler.UpdateJobTextField(job["jobId"],"errorMsg","cannot launch the job.")
                if jobDescriptionPath is not None and os.path.isfile(jobDescriptionPath):
                    k8sUtils.kubectl_delete(jobDescriptionPath)
            else:
                logging.warning("Job %s fails in Kubernetes, delete and re-submit the job. Retries %d", job["jobId"] , retries)
                SubmitJob(job)
    elif result.strip() == "PendingHostPort":
        logging.warning("Cannot find host ports for job :%s, re-launch the job with different host ports ", job["jobId"])

        SubmitJob(job)

    if result.strip() != "Unknown" and job["jobId"] in UnusualJobs:
        del UnusualJobs[job["jobId"]]

    dataHandler.Close()


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
def start_ssh_server(pod_name, user_name, host_network=False, ssh_port=22):
    '''Setup the ssh server in container, and return the listening port.'''
    bash_script = "sudo bash -c 'apt-get update && apt-get install -y openssh-server && cd /home/" + user_name + " && (chown " + user_name + " -R .ssh; chmod 600 -R .ssh/*; chmod 700 .ssh; true) && service ssh restart'"

    # ssh_port = 22

    # modify the script for HostNewtork
    if host_network:
        # if the ssh_port is default value 22, randomly choose one
        if ssh_port == 22:
            ssh_port = random.randint(40000, 49999)
        # bash_script = "sed -i '/^Port 22/c Port "+str(ssh_port)+"' /etc/ssh/sshd_config && "+bash_script
        # TODO refine the script later
        bash_script = "sudo bash -c 'apt-get update && apt-get install -y openssh-server && sed -i \"s/^Port 22/Port " + str(ssh_port) + "/\" /etc/ssh/sshd_config && cd /home/" + user_name + " && (chown " + user_name + " -R .ssh; chmod 600 -R .ssh/*; chmod 700 .ssh; true) && service ssh restart'"

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
        ssh_port = pod["metadata"]["labels"]["sshPort"]
        # quit if can't setup ssh server
        ssh_port = start_ssh_server(pod_name, user_name, host_network, ssh_port)

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
        ssh_port = pod["metadata"]["labels"]["sshPort"]
        role = pod["metadata"]["labels"]["distRole"]
        role_idx = pod["metadata"]["labels"]["distRoleIdx"]

        # TODO hostNetwork
        if host_network:
            sshconfigstr += (ssh_config % (role + "-"+str(role_idx), pod_ip, str(ssh_port), user_name) + "\n")
        else:
            sshconfigstr += (ssh_config % (role + "-"+str(role_idx), pod_ip, 22, user_name) + "\n")

    # config ssh client
    for [idx, pod] in enumerate(pods["items"]):
        pod_name = pod["metadata"]["name"]
        bash_script = "cat > /home/" + user_name + "/.ssh/config <<EOF " + sshconfigstr + "\nEOF"
        logging.info("override ssh client config: %s", bash_script)
        k8sUtils.kubectl_exec("exec %s -- bash -c \'%s\' ; chown -R %s /home/%s/.ssh/config" % (pod_name, bash_script,user_name,user_name))

        # fix ~/.ssh/ folder permission
        k8sUtils.kubectl_exec("exec %s -- chmod 600 -R /home/%s/.ssh; chmod 700 /home/%s/.ssh; chown -R %s /home/%s/.ssh/config" % (pod_name,user_name,user_name,user_name,user_name))

    # generate hostfile
    hostfilecontent = ""
    for [_, pod] in enumerate(pods["items"]):
        role = pod["metadata"]["labels"]["distRole"]
        if role == "ps":
            continue
        role_idx = pod["metadata"]["labels"]["distRoleIdx"]
        worker_gpu_num = pod["spec"]["containers"][0]["resources"]["requests"]["nvidia.com/gpu"]
        hostfilecontent += "%s  slots=%s\n" % ("worker-"+str(role_idx), worker_gpu_num)
    tmp_hostfile = "/tmp/" + job_id + ".hostfile"
    with open(tmp_hostfile, 'w') as f:
        f.write(hostfilecontent + "\n")
    # write the hostfile
    for [idx, pod] in enumerate(pods["items"]):
        pod_name = pod["metadata"]["name"]
        remotecmd = "cp %s %s:/job/hostfile" % (tmp_hostfile, pod_name)
        k8sUtils.kubectl_exec(remotecmd)


    for [idx, pod] in enumerate(pods["items"]):
        pod_name = pod["metadata"]["name"]
        k8sUtils.kubectl_exec("exec %s touch /opt/run_dist_job" % pod_name)


    # execute user command
    #k8sUtils.kubectl_exec("exec %s -- bash -c 'runuser -l ${DLWS_USER_NAME} <<EOF_USER_SCRIPT %s \nEOF_USER_SCRIPT'" % (pod_name, jobParams["cmd"]))

    # update job status
    dataHandler = DataHandler()
    dataHandler.UpdateJobTextField(job_id, "jobStatus", "running")
    dataHandler.Close()

def create_log( logdir = '/var/log/dlworkspace' ):
    if not os.path.exists( logdir ):
        os.system("mkdir -p " + logdir )
    with open('logging.yaml') as f:
        logging_config = yaml.full_load(f)
        f.close()
        logging_config["handlers"]["file"]["filename"] = logdir+"/jobmanager.log"
        logging.config.dictConfig(logging_config)


def JobInfoSorter(elem):
    return elem["sortKey"]


def TakeJobActions(jobs):
    dataHandler = DataHandler()
    vcList = dataHandler.ListVCs()
    clusterStatus, dummy = dataHandler.GetClusterStatus()
    dataHandler.Close()

    globalTotalRes = ResourceInfo(clusterStatus["gpu_capacity"])
    globalReservedRes = ResourceInfo(clusterStatus["gpu_unschedulable"])

    localResInfo = ResourceInfo()
    globalResInfo = ResourceInfo.Difference(globalTotalRes, globalReservedRes)

    for vc in vcList:
        vcTotalRes = ResourceInfo(json.loads(vc["quota"]), vc["vcName"])
        clusterTotalRes = ResourceInfo(clusterStatus["gpu_capacity"], vc["vcName"])
        clusterReservedRes = ResourceInfo(clusterStatus["gpu_unschedulable"], vc["vcName"])
        vcReservedRes = clusterReservedRes.GetFraction(vcTotalRes, clusterTotalRes)
        localResInfo.Add(ResourceInfo.Difference(vcTotalRes, vcReservedRes))

    jobsInfo = []
    for job in jobs:
        if job["jobStatus"] == "queued" or job["jobStatus"] == "scheduling" or job["jobStatus"] == "running":
            singleJobInfo = {}
            singleJobInfo["job"] = job
            singleJobInfo["jobParams"] = json.loads(base64.b64decode(job["jobParams"]))
            jobGpuType = "any"
            if "gpuType" in singleJobInfo["jobParams"]:
                jobGpuType = singleJobInfo["jobParams"]["gpuType"]
            singleJobInfo["localResInfo"] = ResourceInfo({jobGpuType : GetJobTotalGpu(singleJobInfo["jobParams"])}, job["vcName"])
            singleJobInfo["globalResInfo"] = ResourceInfo({jobGpuType : GetJobTotalGpu(singleJobInfo["jobParams"])})
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
        elif sji["jobParams"]["preemptionAllowed"] and (sji["job"]["jobStatus"] == "scheduling" or sji["job"]["jobStatus"] == "running") and sji["allowed"] == False:
            KillJob(sji["job"], "queued")
            logging.info("TakeJobActions : pre-empting job : %s : %s : %s" % (sji["jobParams"]["jobName"], sji["jobParams"]["jobId"], sji["sortKey"]))

    logging.info("TakeJobActions : job desired actions taken")


def Run():

    while True:

        try:
            config["racks"] = k8sUtils.get_node_labels("rack")
            config["skus"] = k8sUtils.get_node_labels("sku")
        except Exception as e:
            logging.exception("get node labels failed")

        try:
            dataHandler = DataHandler()
            try:
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
                        elif job["jobStatus"] == "scheduling" or job["jobStatus"] == "running":
                            UpdateJobStatus(job)
                        elif job["jobStatus"] == "unapproved":
                            AutoApproveJob(job)
                    except Exception as e:
                        logging.info(e)
            except Exception as e:
                logging.exception("process pending job failed")
            finally:
                dataHandler.Close()
        except Exception as e:
            logging.exception("close data handler failed")

        time.sleep(1)


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s',
            level=logging.INFO)
    Run()
    #print k8sUtils.get_pod_events("d493d41c-45ea-4e85-8ca4-01c3533cd727")
