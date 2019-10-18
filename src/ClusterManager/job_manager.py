import json
import os
import time
import argparse
import sys
import datetime
import functools
import timeit

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../storage"))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../utils"))

import k8sUtils
import joblog_manager
import notify

import yaml
from config import config, GetStoragePath, GetWorkPath
from DataHandler import DataHandler
from node_manager import get_cluster_status
import base64
from ResourceInfo import ResourceInfo

import re

from prometheus_client import Histogram

import logging
import logging.config
from job import Job, JobSchema
from job_launcher import JobDeployer, JobRole, PythonLauncher

from cluster_manager import setup_exporter_thread, manager_iteration_histogram, register_stack_trace_dump, update_file_modification_time

from job_launcher import get_job_status_detail, job_status_detail_with_finished_time


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
def UpdateJobStatus(launcher, job, notifier=None, dataHandlerOri=None):
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
            launcher.kill_job(job["jobId"], "queued")

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
            return "Succeeded", []

    statuses = [job_role.status() for job_role in job_roles]
    logging.info("Job: {}, status: {}".format(job_id, statuses))

    details = []
    for job_role in job_roles:
        details.append(job_role.pod_details().to_dict())
    logging.info("Job {}, details: {}".format(job_id, details))

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
def TakeJobActions(launcher, jobs):
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
                launcher.submit_job(sji["job"])
                logging.info("TakeJobActions : submitting job : %s : %s" % (sji["jobId"], sji["sortKey"]))
            elif sji["preemptionAllowed"] and (sji["job"]["jobStatus"] == "scheduling" or sji["job"]["jobStatus"] == "running") and (sji["allowed"] is False):
                launcher.kill_job(sji["job"]["jobId"], "queued")
                logging.info("TakeJobActions : pre-empting job : %s : %s" % (sji["jobId"], sji["sortKey"]))
        except Exception as e:
            logging.error("Process job failed {}".format(sji["job"]), exc_info=True)

    logging.info("TakeJobActions : job desired actions taken")


def Run(updateblock=0):
    register_stack_trace_dump()
    notifier = notify.Notifier(config.get("job-manager"))
    notifier.start()
    create_log()

    launcher = PythonLauncher()
    launcher.start()

    while True:
        if updateblock == 0:
            update_file_modification_time("job_manager")
        else:
            update_file_modification_time("job_manager" + str(updateblock))

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
                    TakeJobActions(launcher, pendingJobs)

                pendingJobs = dataHandler.GetPendingJobs()
                logging.info("Updating status for %d jobs" % len(pendingJobs))
                for job in pendingJobs:
                    try:
                        logging.info("Processing job: %s, status: %s" % (job["jobId"], job["jobStatus"]))
                        if updateblock == 0 or updateblock == 2:
                            if job["jobStatus"] == "killing":
                                launcher.kill_job(job["jobId"], "killed", dataHandlerOri=dataHandler)
                            elif job["jobStatus"] == "pausing":
                                launcher.kill_job(job["jobId"], "paused", dataHandlerOri=dataHandler)
                            elif job["jobStatus"] == "running":
                                UpdateJobStatus(launcher, job, notifier, dataHandlerOri=dataHandler)

                        if updateblock == 0 or updateblock == 1:
                            if job["jobStatus"] == "scheduling":
                                UpdateJobStatus(launcher, job, notifier, dataHandlerOri=dataHandler)
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
