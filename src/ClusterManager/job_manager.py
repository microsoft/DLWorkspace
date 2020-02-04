import json
import os
import time
import argparse
import sys
import datetime
import functools
import timeit
import collections

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
import quota

from prometheus_client import Histogram
import redis

import logging
import logging.config
from job import Job, JobSchema
from job_launcher import JobDeployer, JobRole, PythonLauncher

from cluster_manager import setup_exporter_thread, manager_iteration_histogram, register_stack_trace_dump, update_file_modification_time, record

from job_launcher import get_job_status_detail, job_status_detail_with_finished_time

logger = logging.getLogger(__name__)


job_state_change_histogram = Histogram("job_state_change_latency_seconds",
        """latency for job to change state(seconds).
        Possible value for current_state is approved/scheduling/running.
        It means how much time it takes for a job change state from previous state
        to current state. The order of state:
        created -> approved -> scheduling -> running.
        For example, approved current_state means how much time it takes for a job
        to change state from created to approved, running current_state means how
        long it takes from scheduling to running.""",
        buckets=(1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 256.0, 512.0, 1024.0,
            float("inf")),
        labelnames=("current_state",))

class JobTimeRecord(object):
    def __init__(self, create_time=None, approve_time=None,
            submit_time=None, running_time=None):
        self.create_time = create_time
        self.approve_time = approve_time
        self.submit_time = submit_time
        self.running_time = running_time

    @staticmethod
    def parse_time(t):
        if t is None:
            return None
        return datetime.datetime.fromtimestamp(t)

    @staticmethod
    def to_timestamp(t):
        if t is None:
            return None
        return time.mktime(t.timetuple())

    @staticmethod
    def parse(m):
        c_time = JobTimeRecord.parse_time(m.get("create_time"))
        a_time = JobTimeRecord.parse_time(m.get("approve_time"))
        s_time = JobTimeRecord.parse_time(m.get("submit_time"))
        r_time = JobTimeRecord.parse_time(m.get("running_time"))
        return JobTimeRecord(c_time, a_time, s_time, r_time)

    def to_map(self):
        return {
                "create_time": JobTimeRecord.to_timestamp(self.create_time),
                "approve_time": JobTimeRecord.to_timestamp(self.approve_time),
                "submit_time": JobTimeRecord.to_timestamp(self.submit_time),
                "running_time": JobTimeRecord.to_timestamp(self.running_time),
                }

def to_job_status_key(job_id):
    return "job_status_" + job_id

def load_job_status(redis_conn, job_id):
    try:
        val = redis_conn.get(to_job_status_key(job_id))
        if val is not None:
            return JobTimeRecord.parse(json.loads(val))
    except Exception:
        logger.exception("load job status failed")
    return JobTimeRecord()

def set_job_status(redis_conn, job_id, job_status):
    try:
        val = json.dumps(job_status.to_map())
        redis_conn.set(to_job_status_key(job_id), val)
    except Exception:
        logger.exception("set job status failed")

# If previous state has no record, which means the job_manager get restarted
# or previous entry is expired, we ignore this entry.
def update_job_state_latency(redis_conn, job_id, state, event_time=None):
    if event_time is None:
        event_time = datetime.datetime.utcnow()

    job_status = load_job_status(redis_conn, job_id)
    changed = False

    if state == "created":
        if job_status.create_time is None:
            changed = True
            job_status.create_time = event_time
    elif state == "approved":
        if job_status.approve_time is None:
            changed = True
            job_status.approve_time = event_time
        if changed and job_status.create_time is not None:
            changed = True
            elapsed = (event_time - job_status.create_time).seconds
            job_state_change_histogram.labels(state).observe(elapsed)
    elif state == "scheduling":
        if job_status.submit_time is None:
            changed = True
            job_status.submit_time = event_time
        if changed and job_status.approve_time is not None:
            changed = True
            elapsed = (event_time - job_status.approve_time).seconds
            job_state_change_histogram.labels(state).observe(elapsed)
    elif state == "running":
        if job_status.running_time is None:
            changed = True
            job_status.running_time = event_time
        # because UpdateJobStatus will call update_job_state_latency
        # multiple times, so here need to avoid override metric
        if changed and job_status.submit_time is not None:
            changed = True
            elapsed = (event_time - job_status.submit_time).seconds
            job_state_change_histogram.labels(state).observe(elapsed)

    if changed:
        set_job_status(redis_conn, job_id, job_status)


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
def ApproveJob(redis_conn, job, dataHandlerOri=None):
    try:
        job_id = job["jobId"]
        vcName = job["vcName"]

        update_job_state_latency(redis_conn, job_id, "created", event_time=job["jobTime"])

        jobParams = json.loads(base64.b64decode(job["jobParams"]))
        job_total_gpus = GetJobTotalGpu(jobParams)

        if dataHandlerOri is None:
            dataHandler = DataHandler()
        else:
            dataHandler = dataHandlerOri

        if "preemptionAllowed" in jobParams and jobParams["preemptionAllowed"] is True:
            logger.info("Job {} preemptible, approve!".format(job_id))
            detail = [{"message": "waiting for available preemptible resource."}]

            dataFields = {
                "jobStatusDetail": base64.b64encode(json.dumps(detail)),
                "jobStatus": "queued"
            }
            conditionFields = {"jobId": job_id}
            dataHandler.UpdateJobTextFields(conditionFields, dataFields)
            update_job_state_latency(redis_conn, job_id, "approved")
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
            logger.warning("Vc not exising! job {}, vc {}".format(job_id, vcName))
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

            logger.info("Job {} require {}, used quota (exclude preemptible GPUs) {}, with user quota of {}.".format(job_id, job_total_gpus, running_gpus, metadata["user_quota"]))
            if job_total_gpus > 0 and int(metadata["user_quota"]) < (running_gpus + job_total_gpus):
                logger.info("Job {} excesses the user quota: {} + {} > {}. Will need approve from admin.".format(job_id, running_gpus, job_total_gpus, metadata["user_quota"]))
                detail = [{"message": "exceeds the user quota in VC: {} (used) + {} (requested) > {} (user quota). Will need admin approval.".format(running_gpus, job_total_gpus, metadata["user_quota"])}]
                dataHandler.UpdateJobTextField(job["jobId"], "jobStatusDetail", base64.b64encode(json.dumps(detail)))
                if dataHandlerOri is None:
                    dataHandler.Close()
                return False

        detail = [{"message": "waiting for available resource."}]

        dataFields = {
            "jobStatusDetail": base64.b64encode(json.dumps(detail)),
            "jobStatus": "queued"
        }
        conditionFields = {"jobId": job_id}
        dataHandler.UpdateJobTextFields(conditionFields, dataFields)
        update_job_state_latency(redis_conn, job_id, "approved")
        if dataHandlerOri is None:
            dataHandler.Close()
        return True
    except Exception as e:
        logger.warning(e, exc_info=True)
    finally:
        if dataHandlerOri is None:
            dataHandler.Close()


UnusualJobs = {}

@record
def UpdateJobStatus(redis_conn, launcher, job, notifier=None, dataHandlerOri=None):
    assert(job["jobStatus"] == "scheduling" or job["jobStatus"] == "running")
    if dataHandlerOri is None:
        dataHandler = DataHandler()
    else:
        dataHandler = dataHandlerOri
    jobParams = json.loads(base64.b64decode(job["jobParams"]))

    result, details = check_job_status(job["jobId"])
    logger.info("++++++++ Job status: {} {}".format(job["jobId"], result))

    jobPath, workPath, dataPath = GetStoragePath(jobParams["jobPath"], jobParams["workPath"], jobParams["dataPath"])
    localJobPath = os.path.join(config["storage-mount-path"], jobPath)
    logPath = os.path.join(localJobPath, "logs/joblog.txt")

    jobDescriptionPath = None
    if "jobDescriptionPath" in job and job["jobDescriptionPath"] is not None:
        jobDescriptionPath = os.path.join(config["storage-mount-path"], job["jobDescriptionPath"])
    if "userId" not in jobParams:
        jobParams["userId"] = "0"

    if result == "Succeeded":
        joblog_manager.extract_job_log(job["jobId"], logPath, jobParams["userId"])

        # TODO: Refactor
        detail = get_job_status_detail(job)
        detail = job_status_detail_with_finished_time(detail, "finished")

        dataFields = {
            "jobStatusDetail": base64.b64encode(json.dumps(detail)),
            "jobStatus": "finished"
        }
        conditionFields = {"jobId": job["jobId"]}
        dataHandler.UpdateJobTextFields(conditionFields, dataFields)

        # Retain the old code for reference
        # if jobDescriptionPath is not None and os.path.isfile(jobDescriptionPath):
        #     k8sUtils.kubectl_delete(jobDescriptionPath)

        job_deployer = JobDeployer()
        job_deployer.delete_job(job["jobId"], force=True)

        if notifier is not None:
            notifier.notify(notify.new_job_state_change_message(
                job["userName"], job["jobId"], result.strip()))
    elif result == "Running":
        update_job_state_latency(redis_conn, job["jobId"], "running")
        if job["jobStatus"] != "running":
            started_at = k8sUtils.localize_time(datetime.datetime.now())
            detail = [{"startedAt": started_at, "message": "started at: {}".format(started_at)}]

            dataFields = {
                "jobStatusDetail": base64.b64encode(json.dumps(detail)),
                "jobStatus":"running"
            }
            conditionFields = {"jobId": job["jobId"]}
            dataHandler.UpdateJobTextFields(conditionFields, dataFields)
            if notifier is not None:
                notifier.notify(notify.new_job_state_change_message(
                    job["userName"], job["jobId"], result.strip()))

    elif result == "Failed":
        logger.warning("Job %s fails, cleaning...", job["jobId"])

        if notifier is not None:
            notifier.notify(notify.new_job_state_change_message(
                job["userName"], job["jobId"], result.strip()))

        joblog_manager.extract_job_log(job["jobId"], logPath, jobParams["userId"])

        # TODO: Refactor
        detail = get_job_status_detail(job)
        detail = job_status_detail_with_finished_time(detail, "failed")

        dataFields = {
            "jobStatusDetail": base64.b64encode(json.dumps(detail)),
            "jobStatus": "failed",
            "errorMsg": "pod failed"
        }
        conditionFields = {"jobId": job["jobId"]}
        dataHandler.UpdateJobTextFields(conditionFields, dataFields)

        # Retain the old code for reference
        # if jobDescriptionPath is not None and os.path.isfile(jobDescriptionPath):
        #     k8sUtils.kubectl_delete(jobDescriptionPath)

        job_deployer = JobDeployer()
        job_deployer.delete_job(job["jobId"], force=True)

    elif result == "Unknown" or result == "NotFound":
        if job["jobId"] not in UnusualJobs:
            logger.warning("!!! Job status ---{}---, job: {}".format(result, job["jobId"]))
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
                logger.info("Reset endpoint status to 'pending': {}".format(endpoint_id))
                dataHandler.UpdateEndpoint(endpoint)

            logger.warning("Job {} fails in Kubernetes as {}, delete and re-submit.".format(job["jobId"], result))
            launcher.kill_job(job["jobId"], "queued")
            if notifier is not None:
                notifier.notify(notify.new_job_state_change_message(
                    job["userName"], job["jobId"], result.strip()))

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
        return "NotFound", []

    # role status in ["NotFound", "Pending", "Running", "Succeeded", "Failed", "Unknown"]
    # TODO ??? when ps/master role "Succeeded", return Succeeded
    for job_role in job_roles:
        if job_role.role_name not in ["master", "ps"]:
            continue
        if job_role.status() == "Succeeded":
            logger.info("Job: {}, Succeeded!".format(job_id))
            return "Succeeded", []

    statuses = [job_role.status() for job_role in job_roles]
    logger.info("Job: {}, status: {}".format(job_id, statuses))

    details = []
    for job_role in job_roles:
        details.append(job_role.pod_details().to_dict())
    logger.debug("Job {}, details: {}".format(job_id, details))

    restricted_details = [
        job_role.pod_restricted_details() for job_role in job_roles
    ]
    logger.info("Job: {}, restricted details: {}".format(job_id, restricted_details))

    job_status = "Running"

    if "Failed" in statuses:
        job_status = "Failed"
    elif "Unknown" in statuses:
        job_status = "Unknown"
    elif "NotFound" in statuses:
        job_status = "NotFound"
    elif "Pending" in statuses:
        job_status = "Pending"

    return job_status, details


def create_log(logdir="/var/log/dlworkspace", process_name="jobmanager"):
    if not os.path.exists(logdir):
        os.system("mkdir -p " + logdir)
    with open('logging.yaml') as f:
        logging_config = yaml.full_load(f)
        f.close()
        logging_config["handlers"]["file"]["filename"] = "%s/%s.log" % (logdir, process_name)
        logging.config.dictConfig(logging_config)


def get_priority_dict():
    try:
        dataHandler = DataHandler()
        priority_dict = dataHandler.get_job_priority()
        return priority_dict
    except Exception as e:
        logger.warning("Fetch job priority dict failed!", exc_info=True)
        return {}
    finally:
        dataHandler.Close()


def get_job_priority(priority_dict, job_id):
    if job_id in priority_dict.keys():
        return priority_dict[job_id]
    return 100


@record
def TakeJobActions(data_handler, redis_conn, launcher, jobs):
    vc_list = data_handler.ListVCs()
    cluster_status, _ = data_handler.GetClusterStatus()
    cluster_total = cluster_status["gpu_capacity"]
    cluster_available = cluster_status["gpu_avaliable"]
    cluster_reserved = cluster_status["gpu_reserved"]

    vc_info = {}
    vc_usage = collections.defaultdict(lambda :
            collections.defaultdict(lambda : 0))

    for vc in vc_list:
        vc_info[vc["vcName"]] = json.loads(vc["quota"])

    active_job_list = data_handler.GetActiveJobList()
    for job in active_job_list:
        jobParam = json.loads(base64.b64decode(job["jobParams"]))
        if "gpuType" in jobParam:
            vc_usage[job["vcName"]][jobParam["gpuType"]] += GetJobTotalGpu(jobParam)

    result = quota.calculate_vc_gpu_counts(cluster_total, cluster_available,
            cluster_reserved, vc_info, vc_usage)
    vc_total, vc_used, vc_available, vc_unschedulable = result

    cluster_gpu_capacity = cluster_status["gpu_capacity"]
    cluster_gpu_unschedulable = cluster_status["gpu_unschedulable"]
    global_total = ResourceInfo(cluster_gpu_capacity)
    global_unschedulable = ResourceInfo(cluster_gpu_unschedulable)

    vc_resources = {}
    globalResInfo = ResourceInfo.Difference(global_total, global_unschedulable)

    priority_dict = get_priority_dict()
    logger.info("Job priority dict: {}".format(priority_dict))

    for vc in vc_list:
        vc_name = vc["vcName"]
        vc_schedulable = {}
        for gpu_type, total in vc_total[vc_name].items():
            vc_schedulable[gpu_type] = total - vc_unschedulable[vc_name][gpu_type]
        vc_resources[vc_name] = ResourceInfo(vc_schedulable)

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

    logger.info("TakeJobActions : local resources : %s" % (vc_resources))
    logger.info("TakeJobActions : global resources : %s" % (globalResInfo.CategoryToCountMap))

    for sji in jobsInfo:
        logger.info("TakeJobActions : job : %s : %s : %s" % (sji["jobId"], sji["globalResInfo"].CategoryToCountMap, sji["sortKey"]))
        vc_name = sji["job"]["vcName"]
        vc_resource = vc_resources[vc_name]

        if (not sji["preemptionAllowed"]) and (vc_resource.CanSatisfy(sji["globalResInfo"])):
            vc_resource.Subtract(sji["globalResInfo"])
            globalResInfo.Subtract(sji["globalResInfo"])
            sji["allowed"] = True
            logger.info("TakeJobActions : local assignment : %s : %s" % (sji["jobId"], sji["globalResInfo"].CategoryToCountMap))

    for sji in jobsInfo:
        if sji["preemptionAllowed"] and (sji["allowed"] is False):
            if globalResInfo.CanSatisfy(sji["globalResInfo"]):
                logger.info("TakeJobActions : job : %s : %s" % (sji["jobId"], sji["globalResInfo"].CategoryToCountMap))
                # Strict FIFO policy not required for global (bonus) tokens since these jobs are anyway pre-emptible.
                globalResInfo.Subtract(sji["globalResInfo"])
                sji["allowed"] = True
                logger.info("TakeJobActions : global assignment : %s : %s" % (sji["jobId"], sji["globalResInfo"].CategoryToCountMap))

    logger.info("TakeJobActions : global resources : %s" % (globalResInfo.CategoryToCountMap))

    for sji in jobsInfo:
        try:
            if sji["job"]["jobStatus"] == "queued" and (sji["allowed"] is True):
                launcher.submit_job(sji["job"])
                update_job_state_latency(redis_conn, sji["jobId"], "scheduling")
                logger.info("TakeJobActions : submitting job : %s : %s" % (sji["jobId"], sji["sortKey"]))
            elif sji["preemptionAllowed"] and (sji["job"]["jobStatus"] == "scheduling" or sji["job"]["jobStatus"] == "running") and (sji["allowed"] is False):
                launcher.kill_job(sji["job"]["jobId"], "queued")
                logger.info("TakeJobActions : pre-empting job : %s : %s" % (sji["jobId"], sji["sortKey"]))
            elif sji["job"]["jobStatus"] == "queued" and sji["allowed"] is False:
                vc_name = sji["job"]["vcName"]
                available_resource = vc_resources[vc_name]
                requested_resource = sji["globalResInfo"]
                detail = [{"message": "waiting for available resource. requested: %s. available: %s" % (requested_resource, available_resource)}]
                data_handler.UpdateJobTextField(sji["jobId"], "jobStatusDetail", base64.b64encode(json.dumps(detail)))
        except Exception as e:
            logger.error("Process job failed {}".format(sji["job"]), exc_info=True)

    logger.info("TakeJobActions : job desired actions taken")

def Run(redis_port, target_status):
    register_stack_trace_dump()
    process_name = "job_manager_" + target_status

    create_log(process_name=process_name)

    notifier = notify.Notifier(config.get("job-manager"))
    notifier.start()

    launcher = PythonLauncher()
    launcher.start()

    redis_conn = redis.StrictRedis(host="localhost",
            port=redis_port, db=0)

    while True:
        update_file_modification_time(process_name)

        with manager_iteration_histogram.labels(process_name).time():
            try:
                config["racks"] = k8sUtils.get_node_labels("rack")
                config["skus"] = k8sUtils.get_node_labels("sku")
            except Exception as e:
                logger.exception("get node labels failed")

            try:
                launcher.wait_tasks_done() # wait for tasks from previous batch done

                dataHandler = DataHandler()

                if target_status == "queued":
                    jobs = dataHandler.GetJobList("all", "all", num=None,
                            status="queued,scheduling,running")
                    TakeJobActions(dataHandler, redis_conn, launcher, jobs)
                else:
                    jobs = dataHandler.GetJobList("all", "all", num=None,
                            status=target_status)
                    logger.info("Updating status for %d %s jobs",
                            len(jobs), target_status)

                    for job in jobs:
                        logger.info("Processing job: %s, status: %s" % (job["jobId"], job["jobStatus"]))
                        if job["jobStatus"] == "killing":
                            launcher.kill_job(job["jobId"], "killed")
                        elif job["jobStatus"] == "pausing":
                            launcher.kill_job(job["jobId"], "paused")
                        elif job["jobStatus"] == "running":
                            UpdateJobStatus(redis_conn, launcher, job, notifier, dataHandlerOri=dataHandler)
                        elif job["jobStatus"] == "scheduling":
                            UpdateJobStatus(redis_conn, launcher, job, notifier, dataHandlerOri=dataHandler)
                        elif job["jobStatus"] == "unapproved":
                            ApproveJob(redis_conn, job, dataHandlerOri=dataHandler)
                        else:
                            logger.error("unknown job status %s for job %s",
                                    job["jobStatus"], job["jobId"])
            except Exception as e:
                logger.warning("Process job failed!", exc_info=True)
            finally:
                try:
                    dataHandler.Close()
                except:
                    pass

        time.sleep(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--redis_port", "-r", help="port of redis", type=int, default=9300)
    parser.add_argument("--port", "-p", help="port of exporter", type=int, default=9200)
    parser.add_argument("--status", "-s", help="target status to update, queued is a special status", type=str, default="queued")

    args = parser.parse_args()
    setup_exporter_thread(args.port)

    Run(args.redis_port, args.status)
