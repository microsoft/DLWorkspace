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
import notify

import yaml
from jinja2 import Environment, FileSystemLoader, Template
from config import config, GetStoragePath, GetWorkPath
from DataHandler import DataHandler
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
from job_role import JobRole

from cluster_manager import setup_exporter_thread, manager_iteration_histogram


def all_pods_not_existing(job_id):
    job_deployer = JobDeployer()
    job_roles = JobRole.get_job_roles(job_id)
    statuses = [job_role.status() for job_role in job_roles]
    logging.info("Job: {}, status: {}".format(job_id, statuses))
    return all([status == "NotFound" for status in statuses])


def SubmitJob(job):
    # check if existing any pod with label: run=job_id
    assert("jobId" in job)
    job_id = job["jobId"]
    if not all_pods_not_existing(job_id):
        logging.warning("Waiting until previously pods are cleaned up! Job {}".format(job_id))
        job_deployer = JobDeployer()
        errors = job_deployer.delete_job(job_id, force=True)
        if errors:
            logging.warning("Force delete job {}: {}".format(job_id, errors))
        return

    ret = {}
    dataHandler = DataHandler()

    try:
        # TODO refine later
        # before resubmit the job, reset the endpoints
        # update all endpoint to status 'pending', so it would restart when job is ready
        endpoints = dataHandler.GetJobEndpoints(job_id)
        for endpoint_id, endpoint in endpoints.items():
            endpoint["status"] = "pending"
            logging.info("Reset endpoint status to 'pending': {}".format(endpoint_id))
            dataHandler.UpdateEndpoint(endpoint)

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
            os.makedirs(os.path.dirname(local_jobDescriptionPath))
        with open(local_jobDescriptionPath, 'w') as f:
            f.write(job_description)

        job_deployer = JobDeployer()
        try:
            pods = job_deployer.create_pods(pods)
            ret["output"] = "Created pods: {}".format([pod.metadata.name for pod in pods])
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
        jobMeta["LaunchCMD"] = pods[0].spec.containers[0].command

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


def KillJob(job_id, desiredState="killed"):
    dataHandler = DataHandler()
    result, detail = k8sUtils.GetJobStatus(job_id)
    dataHandler.UpdateJobTextField(job_id, "jobStatusDetail", base64.b64encode(json.dumps(detail)))
    logging.info("Killing job %s, with status %s, %s" % (job_id, result, detail))

    job_deployer = JobDeployer()
    errors = job_deployer.delete_job(job_id, force=True)

    if len(errors) == 0:
        dataHandler.UpdateJobTextField(job_id, "jobStatus", desiredState)
        dataHandler.UpdateJobTextField(job_id, "lastUpdated", datetime.datetime.now().isoformat())
        dataHandler.Close()
        return True
    else:
        dataHandler.UpdateJobTextField(job_id, "jobStatus", "error")
        dataHandler.UpdateJobTextField(job_id, "lastUpdated", datetime.datetime.now().isoformat())
        dataHandler.Close()
        logging.error("Kill job failed with errors: {}".format(errors))
        return False


def ApproveJob(job):
    try:
        job_id = job["jobId"]
        vcName = job["vcName"]
        jobParams = json.loads(base64.b64decode(job["jobParams"]))
        total_gpus = GetJobTotalGpu(jobParams)

        dataHandler = DataHandler()
        vcList = dataHandler.ListVCs()
        vc = None
        for item in vcList:
            if item["vcName"] == vcName:
                vc = item
                break
        if vc is None:
            logging.warning("Vc not exising! job {}, vc {}".format(job_id, vcName))
            return False
        metadata = json.loads(vc["metadata"])

        if "user_quota" in metadata and int(metadata["user_quota"]) < total_gpus:
            logging.info("Job {} excesses the user quota: {} > {}. Will need approve from admin.".format(job_id, total_gpus, metadata["user_quota"]))
            return False
        else:
            dataHandler.UpdateJobTextField(job_id, "jobStatus", "queued")
            return True
    except Exception as e:
        logging.warning(e, exc_info=True)
    finally:
        dataHandler.Close()


UnusualJobs = {}

def UpdateJobStatus(job, notifier=None):
    assert(job["jobStatus"] == "scheduling" or job["jobStatus"] == "running")
    dataHandler = DataHandler()
    jobParams = json.loads(base64.b64decode(job["jobParams"]))

    result = check_job_status(job["jobId"])
    logging.info("++++++++ Job status: {} {}".format(job["jobId"], result))

    jobPath, workPath, dataPath = GetStoragePath(jobParams["jobPath"], jobParams["workPath"], jobParams["dataPath"])
    localJobPath = os.path.join(config["storage-mount-path"], jobPath)
    logPath = os.path.join(localJobPath, "logs/joblog.txt")

    jobDescriptionPath = os.path.join(config["storage-mount-path"], job["jobDescriptionPath"]) if "jobDescriptionPath" in job else None
    if "userId" not in jobParams:
        jobParams["userId"] = "0"

    if result == "Succeeded":
        joblog_manager.extract_job_log(job["jobId"], logPath, jobParams["userId"])
        dataHandler.UpdateJobTextField(job["jobId"], "jobStatus", "finished")
        if jobDescriptionPath is not None and os.path.isfile(jobDescriptionPath):
            k8sUtils.kubectl_delete(jobDescriptionPath)


        if notifier is not None:
            notifier.notify(notify.new_job_state_change_message(
                job["userName"], job["jobId"], result.strip()))
    elif result == "Running":
        if job["jobStatus"] != "running":
            started_at = datetime.datetime.now().isoformat()
            detail = [{"startedAt": started_at, "message": "started at: {}".format(started_at)}]
            dataHandler.UpdateJobTextField(job["jobId"], "jobStatusDetail", base64.b64encode(json.dumps(detail)))
            dataHandler.UpdateJobTextField(job["jobId"], "jobStatus", "running")

    elif result == "Failed":
        logging.warning("Job %s fails, cleaning...", job["jobId"])

        if notifier is not None:
            notifier.notify(notify.new_job_state_change_message(
                job["userName"], job["jobId"], result.strip()))

        joblog_manager.extract_job_log(job["jobId"], logPath, jobParams["userId"])
        dataHandler.UpdateJobTextField(job["jobId"], "jobStatus", "failed")
        dataHandler.UpdateJobTextField(job["jobId"], "errorMsg", "pod failed")

        if jobDescriptionPath is not None and os.path.isfile(jobDescriptionPath):
            k8sUtils.kubectl_delete(jobDescriptionPath)

    elif result == "Unknown" or result == "NotFound":
        if job["jobId"] not in UnusualJobs:
            logging.warning("!!! Job status ---{}---, job: {}".format(result, job["jobId"]))
            UnusualJobs[job["jobId"]] = datetime.datetime.now()
        # TODO
        # 1) May need to reduce the timeout.
        #     It takes minutes before pod turns into "Unknown", we may don't need to wait so long.
        # 2) If node resume before we resubmit the job, the job will end in status 'NotFound'.
        elif (datetime.datetime.now() - UnusualJobs[job["jobId"]]).seconds > 30:
            del UnusualJobs[job["jobId"]]

            # TODO refine later
            # before resubmit the job, reset the endpoints
            # update all endpoint to status 'pending', so it would restart when job is ready
            endpoints = dataHandler.GetJobEndpoints(job["jobId"])
            for endpoint_id, endpoint in endpoints.items():
                endpoint["status"] = "pending"
                logging.info("Reset endpoint status to 'pending': {}".format(endpoint_id))
                dataHandler.UpdateEndpoint(endpoint)

            logging.warning("Job {} fails in Kubernetes as {}, delete and re-submit.".format(job["jobId"], result))
            KillJob(job["jobId"], "queued")

    if result != "Unknown" and result != "NotFound" and job["jobId"] in UnusualJobs:
        del UnusualJobs[job["jobId"]]

    dataHandler.Close()


# TODO refine later
def check_job_status(job_id):
    job_deployer = JobDeployer()
    job_roles = JobRole.get_job_roles(job_id)

    if len(job_roles) < 1:
        return "NotFound"

    # role status in ["NotFound", "Pending", "Running", "Succeeded", "Failed", "Unknown"]
    # TODO ??? when ps/master role "Succeeded", return Succeeded
    for job_role in job_roles:
        if job_role.role_name not in ["master", "ps"]:
            continue
        if job_role.status() == "Succeeded":
            logging.info("Job: {}, Succeeded!".format(job_id))
            return "Succeeded"

    statuses = [job_role.status() for job_role in job_roles]
    logging.info("Job: {}, status: {}".format(job_id, statuses))

    if "Failed" in statuses:
        return "Failed"
    if "Unknown" in statuses:
        return "Unknown"
    if "NotFound" in statuses:
        return "NotFound"
    if "Pending" in statuses:
        return "Pending"

    return "Running"

def create_log(logdir = '/var/log/dlworkspace'):
    if not os.path.exists(logdir):
        os.system("mkdir -p " + logdir)
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
    globalReservedRes = ResourceInfo(clusterStatus["gpu_reserved"])

    localResInfo = ResourceInfo()
    globalResInfo = ResourceInfo.Difference(globalTotalRes, globalReservedRes)

    for vc in vcList:
        vcTotalRes = ResourceInfo(json.loads(vc["quota"]), vc["vcName"])
        clusterTotalRes = ResourceInfo(clusterStatus["gpu_capacity"], vc["vcName"])
        clusterReservedRes = ResourceInfo(clusterStatus["gpu_reserved"], vc["vcName"])
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
        try:
            if sji["job"]["jobStatus"] == "queued" and sji["allowed"] == True:
                SubmitJob(sji["job"])
                logging.info("TakeJobActions : submitting job : %s : %s : %s" % (sji["jobParams"]["jobName"], sji["jobParams"]["jobId"], sji["sortKey"]))
            elif sji["jobParams"]["preemptionAllowed"] and (sji["job"]["jobStatus"] == "scheduling" or sji["job"]["jobStatus"] == "running") and sji["allowed"] == False:
                KillJob(sji["job"]["jobId"], "queued")
                logging.info("TakeJobActions : pre-empting job : %s : %s : %s" % (sji["jobParams"]["jobName"], sji["jobParams"]["jobId"], sji["sortKey"]))
        except Exception as e:
            logging.error("Process job failed {}".format(sji["job"]), exc_info=True)

    logging.info("TakeJobActions : job desired actions taken")


def Run():
    notifier = notify.Notifier(config.get("job-manager"))
    notifier.start()
    create_log()

    while True:
        with manager_iteration_histogram.labels("job_manager").time():
            try:
                config["racks"] = k8sUtils.get_node_labels("rack")
                config["skus"] = k8sUtils.get_node_labels("sku")
            except Exception as e:
                logging.exception("get node labels failed")

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
                            KillJob(job["jobId"], "killed")
                        elif job["jobStatus"] == "pausing":
                            KillJob(job["jobId"], "paused")
                        elif job["jobStatus"] == "scheduling" or job["jobStatus"] == "running":
                            UpdateJobStatus(job, notifier)
                        elif job["jobStatus"] == "unapproved":
                            ApproveJob(job)
                    except Exception as e:
                        logging.warning(e, exc_info=True)
            except Exception as e:
                logging.warning("Process job failed!", exc_info=True)
            finally:
                try:
                    dataHandler.Close()
                except:
                    pass

        time.sleep(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", "-p", help="port of exporter", type=int, default=9200)
    args = parser.parse_args()
    setup_exporter_thread(args.port)

    Run()
