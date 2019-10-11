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
import functools
import timeit

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../storage"))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../utils"))

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

from prometheus_client import Histogram

import logging
import logging.config
from job import Job, JobSchema
from pod_template import PodTemplate
from dist_pod_template import DistPodTemplate
from job_deployer import JobDeployer
from job_role import JobRole

from cluster_manager import setup_exporter_thread, manager_iteration_histogram, register_stack_trace_dump, update_file_modification_time

jobmanager_fn_histogram = Histogram("jobmanager_fn_latency_seconds",
        "latency for executing jobmanager function (seconds)",
        buckets=(.1, 2.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 50.0,
            float("inf")),
        labelnames=("fn_name",))

def record(fn):
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        start = timeit.default_timer()
        try:
            return fn(*args, **kwargs)
        finally:
            elapsed = timeit.default_timer() - start
            jobmanager_fn_histogram.labels(fn.__name__).observe(elapsed)
    return wrapped

def all_pods_not_existing(job_id):
    job_deployer = JobDeployer()
    job_roles = JobRole.get_job_roles(job_id)
    statuses = [job_role.status() for job_role in job_roles]
    logging.info("Job: {}, status: {}".format(job_id, statuses))
    return all([status == "NotFound" for status in statuses])


def get_job_status_detail(job):
    if "jobStatusDetail" not in job:
        return None

    job_status_detail = job["jobStatusDetail"]
    if job_status_detail is None:
        return job_status_detail

    if not isinstance(job_status_detail, list):
        job_status_detail = base64.b64decode(job_status_detail)
        job_status_detail = json.loads(job_status_detail)
    return job_status_detail


def job_status_detail_with_finished_time(job_status_detail, status, msg=""):
    # This method is called when a job succeeds/fails/is killed/has an error

    # job_status_detail must be None or a list
    if (job_status_detail is not None) and (not isinstance(job_status_detail, list)):
        return job_status_detail

    # Force adding an item for empty detail
    if (job_status_detail is None) or (len(job_status_detail) == 0):
        job_status_detail = [{}]

    finished_at = k8sUtils.localize_time(datetime.datetime.now())
    new_job_status_detail = []
    # Override finishedAt for all pods if absent
    for pod_status_detail in job_status_detail:
        # Mark started time the same as finished time for a fast finishing job
        if "startedAt" not in pod_status_detail:
            pod_status_detail["startedAt"] = finished_at

        if "finishedAt" not in pod_status_detail:
            pod_status_detail["finishedAt"] = finished_at

        pod_status_detail["message"] = "{} at {}. {}".format(status, finished_at, msg)
        new_job_status_detail.append(pod_status_detail)

    return new_job_status_detail


def get_scheduling_job_details(details):
    pod_details = []
    for detail in details:
        # Users are mostly interested in
        # 1. Pod name
        # 2. Pod phase
        # 3. Message indicating why it's pending
        pod_detail = {}
        if "metadata" in detail and "labels" in detail["metadata"] and \
                "podName" in detail["metadata"]["labels"]:
            pod_detail["podName"] = detail["metadata"]["labels"]["podName"]

        if "status" in detail:
            status = detail["status"]
            if "phase" in status:
                pod_phase = status["phase"]
                pod_detail["podPhase"] = pod_phase
                if pod_phase == "Pending":
                    message = {}
                    if "conditions" in status:
                        conditions = status["conditions"]
                        for condition in conditions:
                            condition["last_transition_time"] = str(condition["last_transition_time"])
                        message["conditions"] = conditions
                    if "container_statuses" in status:
                        message["containerStatuses"] = status["container_statuses"]
                    pod_detail["message"] = message

        pod_details.append(pod_detail)

    return pod_details


@record
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
            pod_template = PodTemplate(job_object.get_template(), enable_custom_scheduler=enable_custom_scheduler)
        elif job_object.params["jobtrainingtype"] == "PSDistJob":
            pod_template = DistPodTemplate(job_object.get_template())
        elif job_object.params["jobtrainingtype"] == "InferenceJob":
            pod_template = PodTemplate(job_object.get_template(),deployment_template=job_object.get_deployment_template(), enable_custom_scheduler=False)
        else:
            dataHandler.SetJobError(job_object.job_id, "ERROR: invalid jobtrainingtype: %s" % job_object.params["jobtrainingtype"])
            dataHandler.Close()
            return False

        pods, error = pod_template.generate_pods(job_object)
        if error:
            dataHandler.SetJobError(job_object.job_id, "ERROR: %s" % error)
            dataHandler.Close()
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

            detail = get_job_status_detail(job)
            detail = job_status_detail_with_finished_time(detail, "error", "Server error in job submission")
            dataHandler.UpdateJobTextField(job["jobId"], "jobStatusDetail", base64.b64encode(json.dumps(detail)))

    dataHandler.Close()
    return ret


def KillJob(job_id, desiredState="killed", dataHandlerOri=None):
    if dataHandlerOri is None:
        dataHandler = DataHandler()
    else:
        dataHandler = dataHandlerOri

    # TODO: Use JobDeployer?
    result, detail = k8sUtils.GetJobStatus(job_id)
    detail = job_status_detail_with_finished_time(detail, desiredState)
    dataHandler.UpdateJobTextField(job_id, "jobStatusDetail", base64.b64encode(json.dumps(detail)))
    logging.info("Killing job %s, with status %s, %s" % (job_id, result, detail))

    job_deployer = JobDeployer()
    errors = job_deployer.delete_job(job_id, force=True)

    if len(errors) == 0:
        dataHandler.UpdateJobTextField(job_id, "jobStatus", desiredState)
        dataHandler.UpdateJobTextField(job_id, "lastUpdated", datetime.datetime.now().isoformat())
        if dataHandlerOri is None:
            dataHandler.Close()
        return True
    else:
        dataHandler.UpdateJobTextField(job_id, "jobStatus", "error", "{}".format(errors))
        dataHandler.UpdateJobTextField(job_id, "lastUpdated", datetime.datetime.now().isoformat())
        if dataHandlerOri is None:
            dataHandler.Close()
        logging.error("Kill job failed with errors: {}".format(errors))
        return False


def GetJobTotalGpu(jobParams):
    numWorkers = 1
    if "numpsworker" in jobParams:
        numWorkers = int(jobParams["numpsworker"])
    return int(jobParams["resourcegpu"]) * numWorkers


@record
def ApproveJob(job, dataHandlerOri=None):
    try:
        job_id = job["jobId"]
        vcName = job["vcName"]
        jobParams = json.loads(base64.b64decode(job["jobParams"]))
        job_total_gpus = GetJobTotalGpu(jobParams)

        if dataHandlerOri is None:
            dataHandler = DataHandler()
        else:
            dataHandler = dataHandlerOri

        if "preemptionAllowed" in jobParams and jobParams["preemptionAllowed"] is True:
            logging.info("Job {} preemptible, approve!".format(job_id))
            detail = [{"message": "waiting for available preemptible resource."}]
            dataHandler.UpdateJobTextField(job["jobId"], "jobStatusDetail", base64.b64encode(json.dumps(detail)))
            dataHandler.UpdateJobTextField(job_id, "jobStatus", "queued")
            if dataHandlerOri is None:
                dataHandler.Close()            
            return True

        vcList = dataHandler.ListVCs()
        vc = None
        for item in vcList:
            if item["vcName"] == vcName:
                vc = item
                break
        if vc is None:
            logging.warning("Vc not exising! job {}, vc {}".format(job_id, vcName))
            if dataHandlerOri is None:
                dataHandler.Close()            
            return False
        metadata = json.loads(vc["metadata"])

        if "user_quota" in metadata:
            user_running_jobs = dataHandler.GetJobList(job["userName"], vcName, status="running,queued,scheduling", op=("=", "or"))
            running_gpus = 0
            for running_job in user_running_jobs:
                running_jobParams = json.loads(base64.b64decode(running_job["jobParams"]))
                # ignore preemptible GPUs
                if "preemptionAllowed" in running_jobParams and running_jobParams["preemptionAllowed"] is True:
                    continue
                running_job_total_gpus = GetJobTotalGpu(running_jobParams)
                running_gpus += running_job_total_gpus

            logging.info("Job {} require {}, used quota (exclude preemptible GPUs) {}, with user quota of {}.".format(job_id, job_total_gpus, running_gpus, metadata["user_quota"]))
            if job_total_gpus > 0 and int(metadata["user_quota"]) < (running_gpus + job_total_gpus):
                logging.info("Job {} excesses the user quota: {} + {} > {}. Will need approve from admin.".format(job_id, running_gpus, job_total_gpus, metadata["user_quota"]))
                detail = [{"message": "exceeds the user quota in VC: {} (used) + {} (requested) > {} (user quota). Will need admin approval.".format(running_gpus, job_total_gpus, metadata["user_quota"])}]
                dataHandler.UpdateJobTextField(job["jobId"], "jobStatusDetail", base64.b64encode(json.dumps(detail)))
                if dataHandlerOri is None:
                    dataHandler.Close()                
                return False

        detail = [{"message": "waiting for available resource."}]
        dataHandler.UpdateJobTextField(job["jobId"], "jobStatusDetail", base64.b64encode(json.dumps(detail)))
        dataHandler.UpdateJobTextField(job_id, "jobStatus", "queued")
        if dataHandlerOri is None:
            dataHandler.Close()        
        return True
    except Exception as e:
        logging.warning(e, exc_info=True)
    finally:
        if dataHandlerOri is None:
            dataHandler.Close()


UnusualJobs = {}

@record
def UpdateJobStatus(job, notifier=None, dataHandlerOri=None):
    assert(job["jobStatus"] == "scheduling" or job["jobStatus"] == "running")
    if dataHandlerOri is None:
        dataHandler = DataHandler()
    else:
        dataHandler = dataHandlerOri
    jobParams = json.loads(base64.b64decode(job["jobParams"]))

    result, details = check_job_status(job["jobId"])
    logging.info("++++++++ Job status: {} {}".format(job["jobId"], result))

    jobPath, workPath, dataPath = GetStoragePath(jobParams["jobPath"], jobParams["workPath"], jobParams["dataPath"])
    localJobPath = os.path.join(config["storage-mount-path"], jobPath)
    logPath = os.path.join(localJobPath, "logs/joblog.txt")

    jobDescriptionPath = os.path.join(config["storage-mount-path"], job["jobDescriptionPath"]) if "jobDescriptionPath" in job else None
    if "userId" not in jobParams:
        jobParams["userId"] = "0"

    if result == "Succeeded":
        joblog_manager.extract_job_log(job["jobId"], logPath, jobParams["userId"])

        # TODO: Refactor
        detail = get_job_status_detail(job)
        detail = job_status_detail_with_finished_time(detail, "finished")
        dataHandler.UpdateJobTextField(job["jobId"], "jobStatusDetail", base64.b64encode(json.dumps(detail)))
        dataHandler.UpdateJobTextField(job["jobId"], "jobStatus", "finished")

        if jobDescriptionPath is not None and os.path.isfile(jobDescriptionPath):
            k8sUtils.kubectl_delete(jobDescriptionPath)

        if notifier is not None:
            notifier.notify(notify.new_job_state_change_message(
                job["userName"], job["jobId"], result.strip()))
    elif result == "Running":
        if job["jobStatus"] != "running":
            started_at = k8sUtils.localize_time(datetime.datetime.now())
            detail = [{"startedAt": started_at, "message": "started at: {}".format(started_at)}]
            dataHandler.UpdateJobTextField(job["jobId"], "jobStatusDetail", base64.b64encode(json.dumps(detail)))
            dataHandler.UpdateJobTextField(job["jobId"], "jobStatus", "running")

    elif result == "Failed":
        logging.warning("Job %s fails, cleaning...", job["jobId"])

        if notifier is not None:
            notifier.notify(notify.new_job_state_change_message(
                job["userName"], job["jobId"], result.strip()))

        joblog_manager.extract_job_log(job["jobId"], logPath, jobParams["userId"])

        # TODO: Refactor
        detail = get_job_status_detail(job)
        detail = job_status_detail_with_finished_time(detail, "failed")
        dataHandler.UpdateJobTextField(job["jobId"], "jobStatusDetail", base64.b64encode(json.dumps(detail)))
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

    elif result == "Pending":
        detail = get_scheduling_job_details(details)
        dataHandler.UpdateJobTextField(job["jobId"], "jobStatusDetail", base64.b64encode(json.dumps(detail)))

    if result != "Unknown" and result != "NotFound" and job["jobId"] in UnusualJobs:
        del UnusualJobs[job["jobId"]]
    if dataHandlerOri is None:
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

    details = []
    for job_role in job_roles:
        details.append(job_role.pod_details().to_dict())

    job_status = "Running"

    if "Failed" in statuses:
        job_status = "Failed"
    if "Unknown" in statuses:
        job_status = "Unknown"
    if "NotFound" in statuses:
        job_status = "NotFound"
    if "Pending" in statuses:
        job_status = "Pending"

    return job_status, details


def create_log(logdir = '/var/log/dlworkspace'):
    if not os.path.exists(logdir):
        os.system("mkdir -p " + logdir)
    with open('logging.yaml') as f:
        logging_config = yaml.full_load(f)
        f.close()
        logging_config["handlers"]["file"]["filename"] = logdir+"/jobmanager.log"
        logging.config.dictConfig(logging_config)


def get_priority_dict():
    try:
        dataHandler = DataHandler()
        priority_dict = dataHandler.get_job_priority()
        return priority_dict
    except Exception as e:
        logging.warning("Fetch job priority dict failed!", exc_info=True)
        return {}
    finally:
        dataHandler.Close()


def get_job_priority(priority_dict, job_id):
    if job_id in priority_dict.keys():
        return priority_dict[job_id]
    return 100


@record
def TakeJobActions(jobs):
    dataHandler = DataHandler()
    vcList = dataHandler.ListVCs()
    clusterStatus, _ = dataHandler.GetClusterStatus()
    dataHandler.Close()

    cluster_gpu_capacity = clusterStatus["gpu_capacity"]
    cluster_gpu_reserved = clusterStatus["gpu_reserved"]
    globalTotalRes = ResourceInfo(cluster_gpu_capacity)
    globalReservedRes = ResourceInfo(cluster_gpu_reserved)

    vc_resources = {}
    localResInfo = ResourceInfo()
    globalResInfo = ResourceInfo.Difference(globalTotalRes, globalReservedRes)

    priority_dict = get_priority_dict()
    logging.info("Job priority dict: {}".format(priority_dict))

    for vc in vcList:
        vcTotalRes = ResourceInfo(json.loads(vc["quota"]))
        clusterTotalRes = ResourceInfo(clusterStatus["gpu_capacity"])
        clusterReservedRes = ResourceInfo(clusterStatus["gpu_reserved"])
        vcReservedRes = clusterReservedRes.GetFraction(vcTotalRes, clusterTotalRes)
        vc_resources[vc["vcName"]] = ResourceInfo.Difference(vcTotalRes, vcReservedRes)

    jobsInfo = []
    for job in jobs:
        if job["jobStatus"] in ["queued", "scheduling", "running"]:
            singleJobInfo = {}
            singleJobInfo["job"] = job
            job_params = json.loads(base64.b64decode(job["jobParams"]))
            singleJobInfo["preemptionAllowed"] = job_params["preemptionAllowed"]
            singleJobInfo["jobId"] = job_params["jobId"]
            jobGpuType = "any"
            if "gpuType" in job_params:
                jobGpuType = job_params["gpuType"]
            singleJobInfo["globalResInfo"] = ResourceInfo({jobGpuType : GetJobTotalGpu(job_params)})

            # Job lists will be sorted based on and in the order of below
            # 1. non-preemptible precedes preemptible
            # 2. running precedes scheduling, precedes queued
            # 3. larger priority value precedes lower priority value
            # 4. early job time precedes later job time

            # Non-Preemptible jobs first
            preemptible = 1 if singleJobInfo["preemptionAllowed"] else 0

            # Job status
            job_status = 0
            if job["jobStatus"] == "scheduling":
                job_status = 1
            elif job["jobStatus"] == "queued":
                job_status = 2

            # Priority value
            reverse_priority = get_job_priority(priority_dict, singleJobInfo["jobId"])
            priority = 999999 - reverse_priority

            # Job time
            job_time = str(job["jobTime"])

            singleJobInfo["sortKey"] = "{}_{}_{:06d}_{}".format(preemptible, job_status, priority, job_time)

            singleJobInfo["allowed"] = False
            jobsInfo.append(singleJobInfo)

    jobsInfo.sort(key=lambda x: x["sortKey"])

    logging.info("TakeJobActions : local resources : %s" % (vc_resources))
    logging.info("TakeJobActions : global resources : %s" % (globalResInfo.CategoryToCountMap))

    for sji in jobsInfo:
        logging.info("TakeJobActions : job : %s : %s : %s" % (sji["jobId"], sji["globalResInfo"].CategoryToCountMap, sji["sortKey"]))
        vc_name = sji["job"]["vcName"]
        vc_resource = vc_resources[vc_name]

        if (vc_resource.CanSatisfy(sji["globalResInfo"])):
            vc_resource.Subtract(sji["globalResInfo"])
            globalResInfo.Subtract(sji["globalResInfo"])
            sji["allowed"] = True
            logging.info("TakeJobActions : local assignment : %s : %s" % (sji["jobId"], sji["globalResInfo"].CategoryToCountMap))

    for sji in jobsInfo:
        if sji["preemptionAllowed"] and (sji["allowed"] is False):
            if globalResInfo.CanSatisfy(sji["globalResInfo"]):
                logging.info("TakeJobActions : job : %s : %s" % (sji["jobId"], sji["globalResInfo"].CategoryToCountMap))
                # Strict FIFO policy not required for global (bonus) tokens since these jobs are anyway pre-emptible.
                globalResInfo.Subtract(sji["globalResInfo"])
                sji["allowed"] = True
                logging.info("TakeJobActions : global assignment : %s : %s" % (sji["jobId"], sji["globalResInfo"].CategoryToCountMap))

    logging.info("TakeJobActions : global resources : %s" % (globalResInfo.CategoryToCountMap))

    for sji in jobsInfo:
        try:
            if sji["job"]["jobStatus"] == "queued" and (sji["allowed"] is True):
                SubmitJob(sji["job"])
                logging.info("TakeJobActions : submitting job : %s : %s" % (sji["jobId"], sji["sortKey"]))
            elif sji["preemptionAllowed"] and (sji["job"]["jobStatus"] == "scheduling" or sji["job"]["jobStatus"] == "running") and (sji["allowed"] is False):
                KillJob(sji["job"]["jobId"], "queued")
                logging.info("TakeJobActions : pre-empting job : %s : %s" % (sji["jobId"], sji["sortKey"]))
        except Exception as e:
            logging.error("Process job failed {}".format(sji["job"]), exc_info=True)

    logging.info("TakeJobActions : job desired actions taken")


@record
def kill_killing_job(job_id, dataHandlerOri=None):
    KillJob(job_id, "killed", dataHandlerOri)

@record
def kill_pausing_job(job_id, dataHandlerOri=None):
    KillJob(job_id, "paused", dataHandlerOri)

def Run(updateblock=0):
    register_stack_trace_dump()
    notifier = notify.Notifier(config.get("job-manager"))
    notifier.start()
    create_log()

    while True:
        update_file_modification_time("job_manager")

        with manager_iteration_histogram.labels("job_manager").time():
            try:
                config["racks"] = k8sUtils.get_node_labels("rack")
                config["skus"] = k8sUtils.get_node_labels("sku")
            except Exception as e:
                logging.exception("get node labels failed")

            try:
                dataHandler = DataHandler()

                if updateblock == 0 or updateblock == 1:
                    pendingJobs = dataHandler.GetPendingJobs()
                    TakeJobActions(pendingJobs)

                pendingJobs = dataHandler.GetPendingJobs()
                logging.info("Updating status for %d jobs" % len(pendingJobs))
                for job in pendingJobs:
                    try:
                        logging.info("Processing job: %s, status: %s" % (job["jobId"], job["jobStatus"]))
                        if updateblock == 0 or updateblock == 2:
                            if job["jobStatus"] == "killing":
                                kill_killing_job(job["jobId"], dataHandlerOri=dataHandler)
                            elif job["jobStatus"] == "pausing":
                                kill_pausing_job(job["jobId"], dataHandlerOri=dataHandler)
                            elif job["jobStatus"] == "running":
                                UpdateJobStatus(job, notifier,dataHandlerOri = dataHandler)

                        if updateblock == 0 or updateblock == 1:
                            if job["jobStatus"] == "scheduling":
                                UpdateJobStatus(job, notifier,dataHandlerOri = dataHandler)
                            elif job["jobStatus"] == "unapproved":
                                ApproveJob(job,dataHandlerOri = dataHandler)
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
    parser.add_argument("--updateblock", "-u", help="updateblock", type=int, default=0)

    args = parser.parse_args()
    setup_exporter_thread(args.port)

    Run(args.updateblock)
