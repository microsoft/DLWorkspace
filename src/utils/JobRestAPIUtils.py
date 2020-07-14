#!/usr/bin/env python3

import datetime
import json
import os
import time
import argparse
import uuid
import sys
import collections
import copy
import requests
import itertools
import pytz

import base64
import re
import logging
from cachetools import cached, TTLCache
from threading import Lock

import requests

from config import config
from DataHandler import DataHandler, DataManager, GlobalDBHandler
from authorization import ResourceType, Permission, AuthorizationManager, IdentityManager, ACLManager
import authorization
from job_op import KillOp, PauseOp, ResumeOp, ApproveOp

sys.path.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "../ClusterManager"))

from common import walk_json
from job_params_util import make_job_params
import JobLogUtils
from resource_stat import Gpu, to_byte

DEFAULT_JOB_PRIORITY = 100
USER_JOB_PRIORITY_RANGE = (100, 200)
ADMIN_JOB_PRIORITY_RANGE = (1, 1000)

logger = logging.getLogger(__name__)

ACTIVE_STATUS = {
    "unapproved",
    "queued",
    "scheduling",
    "running",
    "pausing",
    "paused",
}
has_access = AuthorizationManager.HasAccess
VC = ResourceType.VC
ADMIN = Permission.Admin
COLLABORATOR = Permission.Collaborator
USER = Permission.User
DEFAULT_EXPIRATION = 24 * 30 * 60
vc_cache = TTLCache(maxsize=10240, ttl=DEFAULT_EXPIRATION)
vc_cache_lock = Lock()


def is_cluster_admin(username):
    return AuthorizationManager.HasAccess(
        username, ResourceType.Cluster, "", Permission.Admin)


def is_vc_admin(username, vc_name):
    return AuthorizationManager.HasAccess(
        username, ResourceType.VC, vc_name, Permission.Admin)


def is_vc_collaborator(username, vc_name):
    return AuthorizationManager.HasAccess(
        username, ResourceType.VC, vc_name, Permission.Collaborator)


def is_vc_user(username, vc_name):
    return AuthorizationManager.HasAccess(
        username, ResourceType.VC, vc_name, Permission.User)


def get_job_total_gpu(job_params):
    num_workers = 1
    if "numpsworker" in job_params:
        num_workers = int(job_params["numpsworker"])
    return int(job_params["resourcegpu"]) * num_workers


def base64encode(str_val):
    return base64.b64encode(str_val.encode("utf-8")).decode("utf-8")


def base64decode(str_val):
    return base64.b64decode(str_val.encode("utf-8")).decode("utf-8")


def adjust_job_priority(priority, permission):
    priority_range = (DEFAULT_JOB_PRIORITY, DEFAULT_JOB_PRIORITY)
    if permission == Permission.User:
        priority_range = USER_JOB_PRIORITY_RANGE
    elif permission == Permission.Admin:
        priority_range = ADMIN_JOB_PRIORITY_RANGE

    if priority > priority_range[1]:
        priority = priority_range[1]
    elif priority < priority_range[0]:
        priority = priority_range[0]

    return priority


def LoadJobParams(jobParamsJsonStr):
    return json.loads(jobParamsJsonStr)


def ToBool(value):
    if isinstance(value, str):
        value = str(value)
        if str.isdigit(value):
            ret = int(value)
            if ret == 0:
                return False
            else:
                return True
        else:
            if value.upper() == 'TRUE':
                return True
            elif value.upper() == 'FALSE':
                return False
            else:
                raise ValueError
    elif isinstance(value, int):
        if value == 0:
            return False
        else:
            return True
    else:
        return value


def populate_job_resource(params):
    try:
        # Populate sku with one from vc info in DB
        vc_name = params["vcName"]
        vc_list = get_vc_list()
        vc_info = None
        for vc in vc_list:
            if vc["vcName"] == vc_name:
                vc_info = vc
                break

        if vc_info is None:
            logger.warning("vc info for %s is None", vc_name)
            return

        try:
            quota = json.loads(vc_info["resourceQuota"])
            metadata = json.loads(vc_info["resourceMetadata"])
        except:
            logger.exception("Failed to parse resource quota and metadata")
            return

        is_admin = has_access(params["userName"], VC, vc_name, ADMIN)
        job_params = make_job_params(params, quota, metadata, config, is_admin)
        if job_params.is_valid():
            logger.info("job_params %s is valid. Populating.", job_params)
            params["sku"] = job_params.sku
            if job_params.gpu_type:
                params["gpuType"] = job_params.gpu_type
            params["resourcegpu"] = job_params.gpu_limit
            if params.get("jobtrainingtype") == "InferenceJob":
                params["mingpu"] = job_params.min_gpu
                params["maxgpu"] = job_params.max_gpu
            params["cpurequest"] = job_params.cpu_request
            params["cpulimit"] = job_params.cpu_limit
            params["memoryrequest"] = job_params.memory_request
            params["memorylimit"] = job_params.memory_limit

        else:
            logger.warning("job_params %s is invalid. Not populating.",
                           job_params)
    except:
        logger.exception("Failed to populate job resource", exc_info=True)


def SubmitJob(jobParamsJsonStr):
    ret = {}

    jobParams = LoadJobParams(jobParamsJsonStr)

    if "jobName" not in jobParams or len(jobParams["jobName"].strip()) == 0:
        ret["error"] = "ERROR: Job name cannot be empty"
        return ret
    if "vcName" not in jobParams or len(jobParams["vcName"].strip()) == 0:
        ret["error"] = "ERROR: VC name cannot be empty"
        return ret
    vc_name = jobParams["vcName"].strip()
    if jobParams.get("jobtrainingtype") == "PSDistJob":
        num_workers = None
        try:
            num_workers = int(jobParams.get("numpsworker"))
        except:
            logger.exception("Parsing numpsworker in %s failed", jobParams)

        if num_workers is None or num_workers == 0:
            ret["error"] = "ERROR: Invalid numpsworker value"
            return ret

    if "userId" not in jobParams or len(jobParams["userId"].strip()) == 0:
        jobParams["userId"] = GetUser(jobParams["userName"])["uid"]

    if "preemptionAllowed" not in jobParams:
        jobParams["preemptionAllowed"] = False
    else:
        jobParams["preemptionAllowed"] = ToBool(jobParams["preemptionAllowed"])

    if jobParams.get("jobtrainingtype") == "InferenceJob":
        jobParams["preemptionAllowed"] = True

    uniqId = str(uuid.uuid4())
    if "jobId" not in jobParams or jobParams["jobId"] == "":
        #jobParams["jobId"] = jobParams["jobName"] + "-" + str(uuid.uuid4())
        #jobParams["jobId"] = jobParams["jobName"] + "-" + str(time.time())
        jobParams["jobId"] = uniqId
    #jobParams["jobId"] = jobParams["jobId"].replace("_","-").replace(".","-")

    if "resourcegpu" not in jobParams:
        jobParams["resourcegpu"] = 0

    if isinstance(jobParams["resourcegpu"], str):
        if len(jobParams["resourcegpu"].strip()) == 0:
            jobParams["resourcegpu"] = 0
        else:
            jobParams["resourcegpu"] = int(jobParams["resourcegpu"])

    populate_job_resource(jobParams)

    if "familyToken" not in jobParams or jobParams["familyToken"].isspace():
        jobParams["familyToken"] = uniqId
    if "isParent" not in jobParams:
        jobParams["isParent"] = 1

    userName = getAlias(jobParams["userName"])

    if not AuthorizationManager.HasAccess(
            jobParams["userName"], ResourceType.VC, vc_name, Permission.User):
        ret["error"] = "Access Denied!"
        return ret

    if "cmd" not in jobParams:
        jobParams["cmd"] = ""

    if "jobPath" in jobParams and len(jobParams["jobPath"].strip()) > 0:
        jobPath = jobParams["jobPath"]
        if ".." in jobParams["jobPath"]:
            ret["error"] = "ERROR: '..' cannot be used in job directory"
            return ret

        if "\\." in jobParams["jobPath"]:
            ret["error"] = "ERROR: invalided job directory"
            return ret

        if jobParams["jobPath"].startswith(
                "/") or jobParams["jobPath"].startswith("\\"):
            ret["error"] = "ERROR: job directory should not start with '/' or '\\' "
            return ret

        if not jobParams["jobPath"].startswith(userName):
            jobParams["jobPath"] = os.path.join(userName, jobParams["jobPath"])

    else:
        jobPath = userName+"/" + "jobs/" + \
            time.strftime("%y%m%d")+"/"+jobParams["jobId"]
        jobParams["jobPath"] = jobPath

    if "workPath" not in jobParams or len(jobParams["workPath"].strip()) == 0:
        jobParams["workPath"] = "."

    if ".." in jobParams["workPath"]:
        ret["error"] = "ERROR: '..' cannot be used in work directory"
        return ret

    if "\\." in jobParams["workPath"]:
        ret["error"] = "ERROR: invalided work directory"
        return ret

    if jobParams["workPath"].startswith(
            "/") or jobParams["workPath"].startswith("\\"):
        ret["error"] = "ERROR: work directory should not start with '/' or '\\' "
        return ret

    if not jobParams["workPath"].startswith(userName):
        jobParams["workPath"] = os.path.join(userName, jobParams["workPath"])

    if "dataPath" not in jobParams or len(jobParams["dataPath"].strip()) == 0:
        jobParams["dataPath"] = "."

    if ".." in jobParams["dataPath"]:
        ret["error"] = "ERROR: '..' cannot be used in data directory"
        return ret

    if "\\." in jobParams["dataPath"]:
        ret["error"] = "ERROR: invalided data directory"
        return ret

    if jobParams["dataPath"][0] == "/" or jobParams["dataPath"][0] == "\\":
        ret["error"] = "ERROR: data directory should not start with '/' or '\\' "
        return ret

    jobParams["dataPath"] = jobParams["dataPath"].replace("\\", "/")
    jobParams["workPath"] = jobParams["workPath"].replace("\\", "/")
    jobParams["jobPath"] = jobParams["jobPath"].replace("\\", "/")
    jobParams["dataPath"] = os.path.realpath(
        os.path.join("/", jobParams["dataPath"]))[1:]
    jobParams["workPath"] = os.path.realpath(
        os.path.join("/", jobParams["workPath"]))[1:]
    jobParams["jobPath"] = os.path.realpath(
        os.path.join("/", jobParams["jobPath"]))[1:]

    dataHandler = DataHandler()

    vc_meta = walk_json(dataHandler.GetVC(vc_name), "metadata")
    vc_meta = {} if vc_meta is None else json.loads(vc_meta)
    max_time = walk_json(vc_meta, "admin", "job_max_time_second")
    if max_time is not None:
        jobParams["maxTimeSec"] = max_time

    if "logDir" in jobParams and len(jobParams["logDir"].strip()) > 0:
        tensorboardParams = jobParams.copy()

        # overwrite for distributed job
        if tensorboardParams["jobtrainingtype"] == "PSDistJob":
            tensorboardParams["jobtrainingtype"] = "RegularJob"
            match = re.match('(.*)(/.*)', tensorboardParams["logDir"])
            if not match is None:
                newDir = match.group(1) + "/worker0" + match.group(2)
                prefix = match.group(1)
                match2 = re.match('.*/worker0', prefix)
                if match2 is None:
                    tensorboardParams["logDir"] = newDir
            #match = re.match('(.*--logdir\s+.*)(/.*--.*)', tensorboardParams["cmd"])
            # if not match is None:
            #    tensorboardParams["cmd"] = match.group(1) + "/worker0" + match.group(2)

        tensorboardParams["jobId"] = uniqId
        tensorboardParams["jobName"] = "tensorboard-" + jobParams["jobName"]
        tensorboardParams["jobPath"] = jobPath
        tensorboardParams["jobType"] = "visualization"
        tensorboardParams["cmd"] = "tensorboard --logdir " + \
            tensorboardParams["logDir"] + " --host 0.0.0.0"
        tensorboardParams["image"] = jobParams["image"]
        tensorboardParams["resourcegpu"] = 0

        tensorboardParams["interactivePort"] = "6006"

        if "error" not in ret:
            if not dataHandler.AddJob(tensorboardParams):
                ret["error"] = "Cannot schedule tensorboard job."

    with GlobalDBHandler(config["global-mysql"]["hostname"],
                         config["global-mysql"]["username"],
                         config["global-mysql"]["password"]) as global_handler:
        public_keys = global_handler.list_public_keys(jobParams["userName"])
        if len(public_keys) > 0:
            user_submitted = jobParams.get("ssh_public_keys", [])
            user_submitted.extend([obj["public_key"] for obj in public_keys])
            jobParams["ssh_public_keys"] = user_submitted

    if "error" not in ret:
        if dataHandler.AddJob(jobParams):
            ret["jobId"] = jobParams["jobId"]
            if "jobPriority" in jobParams:
                priority = DEFAULT_JOB_PRIORITY
                try:
                    priority = int(jobParams["jobPriority"])
                except Exception as e:
                    pass

                permission = Permission.User
                if AuthorizationManager.HasAccess(jobParams["userName"],
                                                  ResourceType.VC, vc_name,
                                                  Permission.Admin):
                    permission = Permission.Admin

                priority = adjust_job_priority(priority, permission)

                job_priorities = {jobParams["jobId"]: priority}
                dataHandler.update_job_priority(job_priorities)
        else:
            ret["error"] = "Cannot schedule job. Cannot add job into database."

    dataHandler.Close()
    return ret


def get_job_list(username, vc_name, job_owner, num=20):
    try:
        with DataHandler() as data_handler:
            if job_owner == "all" and \
                    has_access(username, VC, vc_name, COLLABORATOR):
                jobs = data_handler.get_union_job_list("all", vc_name, num,
                                                       ACTIVE_STATUS)
            else:
                jobs = data_handler.get_union_job_list(username, vc_name, num,
                                                       ACTIVE_STATUS)
            for job in jobs:
                job.pop('jobMeta', None)
    except:
        logger.exception("Exception in getting job list for username %s",
                         username)
        jobs = []

    return jobs


def get_job_list_v2(username, vc_name, job_owner, num=None):
    try:
        with DataHandler() as data_handler:
            if job_owner == "all" and \
                    has_access(username, VC, vc_name, COLLABORATOR):
                jobs = data_handler.get_union_job_list_v2(
                    "all", vc_name, num, ACTIVE_STATUS)
            else:
                jobs = data_handler.get_union_job_list_v2(
                    username, vc_name, num, ACTIVE_STATUS)
    except:
        logger.exception("Exception in getting job list v2 for username %s",
                         username)
        jobs = {}

    return jobs


def get_active_job_list():
    try:
        with DataHandler() as data_handler:
            fields = ["jobId", "jobStatus", "userName", "vcName"]
            status = ["scheduling", "running"]
            jobs = data_handler.get_fields_for_jobs_in_status(fields, status)
            return jobs, 200
    except:
        logger.exception("Failed to get active job list")
        return "Internal error", 500


def GetUserPendingJobs(userName, vcName):
    jobs = []
    allJobs = DataManager.GetAllPendingJobs(vcName)
    for job in allJobs:
        if userName == "all" or userName == job["userName"]:
            jobs.append(job)
    return jobs


def GetCommands(userName, jobId):
    commands = []
    dataHandler = DataHandler()
    job = dataHandler.GetJobTextFields(jobId, ["userName", "vcName"])
    if job is not None:
        if job["userName"] == userName or AuthorizationManager.HasAccess(
                userName, ResourceType.VC, job["vcName"],
                Permission.Collaborator):
            commands = dataHandler.GetCommands(jobId=jobId)
    dataHandler.Close()
    return commands


def get_access_to_job(username, job):
    is_owner = job["userName"].lower() == username.lower()
    is_admin = has_access(username, VC, job["vcName"], ADMIN)
    allowed = is_owner or is_admin

    role = "unauthorized"
    if is_owner:
        role = "owner"
    elif is_admin:
        role = "admin"
    return allowed, role


def op_job(username, job_id, op):
    op_name = op.name
    op_past_tense = op.past_tense
    from_states = op.from_states
    to_state = op.to_state

    ret = False
    with DataHandler() as data_handler:
        job = data_handler.GetJobTextFields(job_id,
                                            ["userName", "vcName", "jobStatus"])

        if job is None:
            return ret

        allowed, role = get_access_to_job(username, job)

        if not allowed:
            logger.info("%s (%s) attempted to %s job %s", username, role,
                        op_name, job_id)
            return ret

        job_status = job["jobStatus"]
        if job_status not in from_states:
            logger.info("%s (%s) attempted to %s a(n) \"%s\" job %s", username,
                        role, op_name, job_status, job_id)
            return ret

        data_fields = {"jobStatus": to_state}
        cond_fields = {"jobId": job_id}
        if isinstance(op, KillOp) and op.desc is not None:
            data_fields["errorMsg"] = op.desc
        ret = data_handler.UpdateJobTextFields(cond_fields, data_fields)
        if ret is True:
            logger.info("%s (%s) successfully %s job %s", username, role,
                        op_past_tense, job_id)
        else:
            logger.info("%s (%s) failed to %s job %s", username, role, op_name,
                        job_id)
    return ret


def kill_job(username, job_id, desc):
    return op_job(username, job_id, KillOp(desc))


def pause_job(username, job_id):
    return op_job(username, job_id, PauseOp())


def resume_job(username, job_id):
    return op_job(username, job_id, ResumeOp())


def approve_job(username, job_id):
    return op_job(username, job_id, ApproveOp())


def scale_inference_job(username, job_id, mingpu, maxgpu):
    dataHandler = DataHandler()
    try:
        job = dataHandler.GetJobTextFields(job_id,
                                           ["userName", "vcName", "jobStatus", "jobParams"])

        if job is None:
            msg = "Job %s cannot be found in database" % job_id
            logger.error(msg)
            return msg, 404

        allowed, role = get_access_to_job(username, job)

        if not allowed:
            msg = "You are not authorized to scale inference job %s" % job_id
            logger.error(msg)
            return msg, 403

        job_params = json.loads(base64decode(job["jobParams"]))
        job_type = job_params["jobtrainingtype"]
        if job_type != "InferenceJob":
            msg = "Only inference job could be scaled, current job %s is %s" % (
                job_id, job_type)
            logger.error(msg)
            return msg, 403

        if (job["jobStatus"] != 'queued' and job_params["mingpu"] != mingpu):
            msg = "Inference job %s has been scheduled, only maxgpu can be changed. \
                Please pause the job first, change mingpu, then resume the job" % (job_id)
            logger.error(msg)
            return msg, 403

        job_params["mingpu"] = mingpu
        job_params["maxgpu"] = maxgpu
        dataHandler.UpdateJobTextFields(
            {"jobId": job_id},
            {"jobParams": base64encode(json.dumps(job_params))})
        return "Success", 200
    except Exception as e:
        logger.exception("Scale inference job exception")
    finally:
        dataHandler.Close()
    return "Server error", 500


def _op_jobs_in_one_batch(username, job_ids, op, data_handler):
    op_name = op.name
    op_past_tense = op.past_tense
    from_states = op.from_states
    to_state = op.to_state

    # Get all jobs to op
    fields = [
        "jobId",
        "userName",
        "vcName",
        "jobStatus",
    ]
    jobs = data_handler.get_fields_for_jobs(job_ids, fields)

    result = {}

    if jobs is None:
        return result

    job_ids_to_op = []
    roles_for_jobs = []
    for job in jobs:
        job_id = job["jobId"]
        job_status = job["jobStatus"]

        allowed, role = get_access_to_job(username, job)

        if not allowed:
            result[job_id] = "unauthorized to %s" % op_name
            logger.info("%s (%s) attempted to %s job %s", username, role,
                        op_name, job_id)
            continue

        if job_status not in from_states:
            result[job_id] = "cannot %s a(n) \"%s\" job" % (op_name, job_status)
            logger.info("%s (%s) attempted to %s a(n) \"%s\" job %s", username,
                        role, op_name, job_status, job_id)
            continue

        job_ids_to_op.append(job_id)
        roles_for_jobs.append(role)

    data_fields = {"jobStatus": to_state}
    success = data_handler.update_text_fields_for_jobs(job_ids_to_op,
                                                       data_fields)

    msg = "successfully %s" % op_past_tense \
        if success else "failed to %s" % op_name
    result.update({job_id: msg for job_id in job_ids_to_op})

    for i, job_id in enumerate(job_ids_to_op):
        role = roles_for_jobs[i]
        logger.info("%s (%s) %s job %s", username, role, msg, job_id)

    return result


def op_jobs(username, job_ids, op, batch_size=20):
    if isinstance(job_ids, str):
        job_ids = job_ids.split(",")
    elif not isinstance(job_ids, list):
        t = type(job_ids)
        err_msg = "Unsupported type %s of job_ids %s" % (t, job_ids)
        return err_msg

    # Partition jobs into processing batches
    batch_starts = range(0, len(job_ids), batch_size)
    job_id_batches = [job_ids[x:x + batch_size] for x in batch_starts]

    result = {}
    with DataHandler() as data_handler:
        for job_id_batch in job_id_batches:
            batch_result = _op_jobs_in_one_batch(username, job_id_batch, op,
                                                 data_handler)
            result.update(batch_result)
    return result


def kill_jobs(username, job_ids):
    return op_jobs(username, job_ids, KillOp(None))


def pause_jobs(username, job_ids):
    return op_jobs(username, job_ids, PauseOp())


def resume_jobs(username, job_ids):
    return op_jobs(username, job_ids, ResumeOp())


def approve_jobs(username, job_ids):
    return op_jobs(username, job_ids, ApproveOp())


def AddCommand(userName, jobId, command):
    dataHandler = DataHandler()
    ret = False
    job = dataHandler.GetJobTextFields(jobId, ["userName", "vcName"])
    if job is not None:
        if job["userName"] == userName or AuthorizationManager.HasAccess(
                userName, ResourceType.VC, job["vcName"],
                Permission.Collaborator):
            ret = dataHandler.AddCommand(jobId, command)
    dataHandler.Close()
    return ret


def isBase64(s):
    try:
        if base64encode(base64decode(s)) == s:
            return True
    except Exception as e:
        pass
    return False


_get_job_log_enabled = config.get('logging') in ['azure_blob', 'elasticsearch']
_extract_job_log_legacy = config.get('__extract_job_log_legacy',
                                     not _get_job_log_enabled)
_get_job_log_legacy = config.get('__get_job_log_legacy',
                                 _extract_job_log_legacy)
_get_job_log_fallback = config.get('__get_job_log_fallback', False)


def GetJobDetail(userName, jobId):
    job = None
    dataHandler = DataHandler()
    jobs = dataHandler.GetJob(jobId=jobId)
    if len(jobs) == 1:
        if jobs[0]["userName"] == userName or AuthorizationManager.HasAccess(
                userName, ResourceType.VC, jobs[0]["vcName"],
                Permission.Collaborator):
            job = jobs[0]
            job["log"] = ""
            if "jobDescription" in job:
                job.pop("jobDescription", None)
            if _extract_job_log_legacy:
                try:
                    log = dataHandler.GetJobTextField(jobId, "jobLog")
                    try:
                        if isBase64(log):
                            log = base64decode(log)
                    except Exception:
                        pass
                    if log is not None:
                        job["log"] = log
                except Exception:
                    job["log"] = "fail-to-get-logs"
    dataHandler.Close()
    return job


def GetJobDetailV2(userName, jobId):
    job = {}
    dataHandler = None
    try:
        dataHandler = DataHandler()
        jobs = dataHandler.GetJobV2(jobId)
        if len(jobs) == 1:
            if jobs[0]["userName"] == userName or AuthorizationManager.HasAccess(
                    userName, ResourceType.VC, jobs[0]["vcName"],
                    Permission.Collaborator):
                job = jobs[0]
    except Exception as e:
        logger.error(
            "get job detail v2 exception for user: %s, jobId: %s, exception: %s",
            userName, jobId, str(e))
    finally:
        if dataHandler is not None:
            dataHandler.Close()
    return job


def GetJobStatus(jobId):
    result = None
    dataHandler = DataHandler()
    result = dataHandler.GetJobTextFields(jobId,
                                          ["jobStatus", "jobTime", "errorMsg"])
    dataHandler.Close()
    return result


def GetJobLog(userName, jobId, cursor=None, size=100):
    dataHandler = DataHandler()
    jobs = dataHandler.GetJob(jobId=jobId)
    if len(jobs) == 1:
        if jobs[0]["userName"] == userName or AuthorizationManager.HasAccess(
                userName, ResourceType.VC, jobs[0]["vcName"],
                Permission.Collaborator):
            if _get_job_log_legacy:
                try:
                    log = dataHandler.GetJobTextField(jobId, "jobLog")
                    try:
                        if isBase64(log):
                            log = base64decode(log)
                    except Exception:
                        pass
                    if log is not None:
                        return {
                            "log": log,
                            "cursor": None,
                        }
                except:
                    pass
            elif _get_job_log_enabled:
                (pod_logs, cursor) = JobLogUtils.GetJobLog(jobId, cursor, size)

                if _get_job_log_fallback:
                    if pod_logs is None or len(pod_logs.keys()) == 0:
                        try:
                            log = dataHandler.GetJobTextField(jobId, "jobLog")
                            try:
                                if isBase64(log):
                                    log = base64decode(log)
                            except Exception:
                                pass
                            if log is not None:
                                return {
                                    "log": log,
                                    "cursor": None,
                                }
                        except:
                            pass

                return {
                    "log": pod_logs,
                    "cursor": cursor,
                }
            else:
                return {
                    "log": "See your job folder on NFS / Samba",
                    "cursor": None,
                }

    return {
        "log": {},
        "cursor": None,
    }


def GetJobRawLog(userName, jobId):
    dataHandler = DataHandler()
    jobs = dataHandler.GetJob(jobId=jobId)
    if len(jobs) == 1:
        if jobs[0]["userName"] == userName or AuthorizationManager.HasAccess(
                userName, ResourceType.VC, jobs[0]["vcName"],
                Permission.Collaborator):
            return JobLogUtils.GetJobRawLog(jobId)
        else:
            return 403
    else:
        return 404


def GetClusterStatus():
    cluster_status, last_update_time = DataManager.GetClusterStatus()
    return cluster_status, last_update_time


def AddUser(username, uid, gid, groups, public_key, private_key):
    ret = IdentityManager.UpdateIdentityInfo(username, uid, gid, groups,
                                             public_key, private_key)
    ret = ret & ACLManager.UpdateAclIdentityId(username, uid)
    return ret


def GetUser(username):
    return IdentityManager.GetIdentityInfoFromDB(username)


def UpdateAce(userName, identityName, resourceType, resourceName, permissions):
    ret = None
    resourceAclPath = AuthorizationManager.GetResourceAclPath(
        resourceName, resourceType)
    if AuthorizationManager.HasAccess(userName, resourceType, resourceName,
                                      Permission.Admin):
        ret = ACLManager.UpdateAce(identityName, resourceAclPath, permissions,
                                   0)
    else:
        ret = "Access Denied!"
    return ret


def DeleteAce(userName, identityName, resourceType, resourceName):
    ret = None
    resourceAclPath = AuthorizationManager.GetResourceAclPath(
        resourceName, resourceType)
    if AuthorizationManager.HasAccess(userName, resourceType, resourceName,
                                      Permission.Admin):
        ret = ACLManager.DeleteAce(identityName, resourceAclPath)
    else:
        ret = "Access Denied!"
    return ret


def AddStorage(userName, vcName, url, storageType, metadata, defaultMountPath):
    ret = None
    dataHandler = DataHandler()
    if AuthorizationManager.IsClusterAdmin(userName):
        ret = dataHandler.AddStorage(vcName, url, storageType, metadata,
                                     defaultMountPath)
    else:
        ret = "Access Denied!"
    dataHandler.Close()
    return ret


def ListStorages(userName, vcName):
    ret = []
    dataHandler = DataHandler()
    if AuthorizationManager.HasAccess(userName, ResourceType.VC, vcName,
                                      Permission.User):
        ret = dataHandler.ListStorages(vcName)
    dataHandler.Close()
    return ret


def DeleteStorage(userName, vcName, url):
    ret = None
    dataHandler = DataHandler()
    if AuthorizationManager.HasAccess(userName, ResourceType.VC, vcName,
                                      Permission.Admin):
        ret = dataHandler.DeleteStorage(vcName, url)
    else:
        ret = "Access Denied!"
    dataHandler.Close()
    return ret


def UpdateStorage(userName, vcName, url, storageType, metadata,
                  defaultMountPath):
    ret = None
    dataHandler = DataHandler()
    if AuthorizationManager.HasAccess(userName, ResourceType.VC, vcName,
                                      Permission.Admin):
        ret = dataHandler.UpdateStorage(vcName, url, storageType, metadata,
                                        defaultMountPath)
    else:
        ret = "Access Denied!"
    dataHandler.Close()
    return ret


def AddVC(userName, vcName, quota, metadata):
    ret = None
    dataHandler = DataHandler()
    if AuthorizationManager.IsClusterAdmin(userName):
        ret = dataHandler.AddVC(vcName, quota, metadata)
        if ret:
            cacheItem = {"vcName": vcName, "quota": quota, "metadata": metadata}
            with vc_cache_lock:
                vc_cache[vcName] = cacheItem
    else:
        ret = "Access Denied!"
    dataHandler.Close()
    return ret


def get_vc_list():
    vc_list = None
    try:
        with vc_cache_lock:
            vc_list = copy.deepcopy(list(vc_cache.values()))
    except Exception:
        pass

    if not vc_list:
        vc_list = DataManager.ListVCs()
        with vc_cache_lock:
            for vc in vc_list:
                vc_cache[vc["vcName"]] = vc

    return vc_list


def ListVCs(userName):
    ret = []
    vc_list = get_vc_list()

    for vc in vc_list:
        if AuthorizationManager.HasAccess(userName, ResourceType.VC,
                                          vc["vcName"], Permission.User):
            vc['admin'] = AuthorizationManager.HasAccess(
                userName, ResourceType.VC, vc["vcName"], Permission.Admin)
            ret.append(vc)
    # web portal (client) can filter out Default VC
    return ret


def get_vc(username, vc_name):
    ret = None
    try:
        with DataHandler() as data_handler:
            cluster_status, _ = data_handler.GetClusterStatus()

        vc_statuses = cluster_status.get("vc_statuses", {})
        vc_list = get_vc_list()

        for vc in vc_list:
            if vc["vcName"] == vc_name and \
                    has_access(username, VC, vc_name, USER):
                ret = copy.deepcopy(vc)
                ret.update(vc_statuses.get(vc_name, {}))
                ret["node_status"] = cluster_status.get("node_status")

                # TODO: deprecate typo "gpu_avaliable" in legacy code
                ret["gpu_avaliable"] = ret["gpu_available"]

                # TODO: deprecate typo "AvaliableJobNum" in legacy code
                ret["AvaliableJobNum"] = ret["available_job_num"]

                break
    except:
        logger.exception("Exception in getting VC %s for user %s", vc_name,
                         username)

    return ret


def get_vc_meta(username, vc_name):
    try:
        if has_access(username, VC, vc_name, ADMIN):
            result = {}
            with DataHandler() as data_handler:
                meta = json.loads(data_handler.GetVC(vc_name)["metadata"])
                result["scheduling_policy"] = walk_json(meta,
                                                        "admin",
                                                        "scheduling_policy",
                                                        default="RF")
                result["job_max_time_second"] = walk_json(
                    meta, "admin", "job_max_time_second")
                result["interactive_limit"] = walk_json(meta, "admin",
                                                        "interactive_limit")
                return result, 200
        else:
            return {
                "error":
                    "%s do not have permission to query meta from vc %s" %
                    (username, vc_name)
            }, 403
    except Exception as e:
        logger.exception("Exception in get_vc_meta VC %s for user %s", vc_name,
                         username)

        return {
            "error":
                "failed to get meta from vc %s, exception %s" %
                (vc_name, str(e))
        }, 500


def patch_vc_meta(username, vc_name, vc_meta):
    try:
        if has_access(username, VC, vc_name, ADMIN):
            if vc_meta is None or len(vc_meta) == 0:
                return {"error": "empty vc_meta"}, 400
            with DataHandler() as data_handler:
                meta = json.loads(data_handler.GetVC(vc_name)["metadata"])
                origin = copy.deepcopy(meta)
                if meta.get("admin") is None:
                    meta["admin"] = {}

                if "scheduling_policy" in vc_meta:
                    scheduling_policy = vc_meta.pop("scheduling_policy")
                    if scheduling_policy is not None and scheduling_policy not in {
                            "RF", "FIFO"
                    }:
                        return {
                            "error":
                                "unknown scheduling_policy %s" %
                                (scheduling_policy)
                        }, 400
                    else:
                        meta["admin"]["scheduling_policy"] = scheduling_policy

                if "job_max_time_second" in vc_meta:
                    job_max_time_second = vc_meta.pop("job_max_time_second")
                    if job_max_time_second is not None and type(
                            job_max_time_second) != int:
                        return {
                            "error":
                                "job_max_time_second should be int, got %s with type %s"
                                %
                                (job_max_time_second, type(job_max_time_second))
                        }, 400
                    else:
                        meta["admin"][
                            "job_max_time_second"] = job_max_time_second

                if "interactive_limit" in vc_meta:
                    interactive_limit = vc_meta.pop("interactive_limit")
                    if interactive_limit is not None and type(
                            interactive_limit) != int:
                        return {
                            "error":
                                "interactive_limit should be int, got %s with type %s"
                                % (interactive_limit, type(interactive_limit))
                        }, 400
                    else:
                        meta["admin"]["interactive_limit"] = interactive_limit

                if len(vc_meta) > 0:
                    return {
                        "error": "unknown key(s) %s" % (str(vc_meta.keys()))
                    }, 400
                else:
                    logger.info("%s update vc meta for %s from %s to %s",
                                username, vc_name, json.dumps(origin),
                                json.dumps(meta))
                    data_handler.UpdateVCMeta(vc_name, json.dumps(meta))
                    return {"error": None}, 200
        else:
            return {
                "error":
                    "%s do not have permission to update meta for vc %s" %
                    (username, vc_name)
            }, 403
    except Exception as e:
        logger.exception("Exception in patch_vc_meta VC %s for user %s",
                         vc_name, username)

        return {
            "error":
                "failed to update meta from vc %s, exception %s" %
                (vc_name, str(e))
        }, 500


def get_resource_quota(username):
    """Get resource quota for all VCs.

    Args:
        username: Name of the user querying VC resource quota.

    Returns:
        Resource quota and metadata for all VCs if user is cluster admin,
        error otherwise.
    """
    try:
        if is_cluster_admin(username):
            vc_list = get_vc_list()
            result = {}
            for vc in vc_list:
                r_quota = {
                    "gpu": {},
                    "gpu_memory": {},
                    "cpu": {},
                    "memory": {},
                }

                vc_r_quota = json.loads(vc["resourceQuota"])

                gpu_quota = walk_json(vc_r_quota, "gpu", default={})
                for sku, count in gpu_quota.items():
                    r_quota["gpu"][sku] = int(count)

                gpu_memory_quota = \
                    walk_json(vc_r_quota, "gpu_memory", default={})
                for sku, count in gpu_memory_quota.items():
                    r_quota["gpu_memory"][sku] = to_byte(count)

                cpu_quota = walk_json(vc_r_quota, "cpu", default={})
                for sku, count in cpu_quota.items():
                    r_quota["cpu"][sku] = int(count)

                memory_quota = walk_json(vc_r_quota, "memory", default={})
                for sku, count in memory_quota.items():
                    r_quota["memory"][sku] = to_byte(count)

                result[vc["vcName"]] = {
                    "resourceQuota": r_quota,
                    "resourceMetadata": json.loads(vc["resourceMetadata"]),
                }
            return result, 200
        else:
            return {
                "error":
                    "%s does not have permission to query resource quota for VCs" %
                    username
            }, 403
    except Exception as e:
        logger.exception("Exception in get_vc_resource_quota for user %s",
                         username)
        return {
            "error":
                "failed to get vc resource quota, exception %s" % str(e)
        }, 500


def patch_resource_quota(username, payload):
    """Update VC resource quota with payload.

    Args:
        username: Name of the user updating VC resource quota.
        payload: Resource quota payload to update.

    Returns:
        200 if successful, error otherwise.
    """
    try:
        if is_cluster_admin(username):
            if payload is None or len(payload) == 0:
                return {"error": "empty payload"}, 400

            vc_list = get_vc_list()
            with DataHandler() as data_handler:
                for vc in vc_list:
                    vc_name = vc["vcName"]
                    if vc_name not in payload:
                        continue

                    vc_payload = payload[vc_name]
                    r_meta = json.loads(vc["resourceMetadata"])
                    req_quota = walk_json(vc_payload, "resourceQuota")
                    if req_quota is None or len(req_quota) == 0:
                        logger.error("empty resourceQuota for vc %s by user %s",
                                     vc_name, username)
                        return {
                            "error": "empty resourceQuota for vc %s" % vc_name
                        }, 400

                    r_quota = {
                        "gpu": {},
                        "gpu_memory": {},
                        "cpu": {},
                        "memory": {},
                    }
                    quota = {}

                    req_gpu_quota = walk_json(req_quota, "gpu", default={})
                    for sku, count in req_gpu_quota.items():
                        gpu_meta = walk_json(r_meta, "gpu", default={})
                        logger.info("gpu_meta: %s", gpu_meta)
                        if sku not in gpu_meta:
                            logger.error(
                                "unrecognized sku %s for vc %s by user %s",
                                sku, vc_name, username)
                            return {
                                "error":
                                    "unrecognized sku %s for vc %s" %
                                    (sku, vc_name)
                            }, 400

                        gpu_type = walk_json(
                            r_meta, "gpu", sku, "gpu_type")
                        gpu_per_node = int(walk_json(
                            r_meta, "gpu", sku, "per_node") or 0)
                        gpu_memory_per_node = to_byte(walk_json(
                            r_meta, "gpu_memory", sku, "per_node") or 0)
                        cpu_per_node = int(walk_json(
                            r_meta, "cpu", sku, "per_node") or 0)
                        memory_per_node = to_byte(walk_json(
                            r_meta, "memory", sku, "per_node") or 0)

                        # Resource quota proportional to GPU
                        count = int(count)
                        nodes = count / gpu_per_node
                        r_quota["gpu"][sku] = int(nodes * gpu_per_node)
                        r_quota["gpu_memory"][sku] = int(nodes * gpu_memory_per_node)
                        r_quota["cpu"][sku] = int(nodes * cpu_per_node)
                        r_quota["memory"][sku] = int(nodes * memory_per_node)

                        # Keep consistent for legacy quota
                        # TODO: This is unambiguous in GPU homogeneous cluster
                        quota[gpu_type] = count

                    req_cpu_quota = walk_json(req_quota, "cpu", default={})
                    for sku, count in req_cpu_quota.items():
                        # Already populated GPU sku
                        if sku in r_quota["cpu"]:
                            continue

                        cpu_meta = walk_json(r_meta, "cpu", default={})
                        if sku not in cpu_meta:
                            logger.error(
                                "unrecognized sku %s for vc %s by user %s",
                                sku, vc_name, username)
                            return {
                                "error":
                                    "unrecognized sku %s for vc %s" %
                                    (sku, vc_name)
                            }, 400

                        count = int(count)
                        cpu_per_node = int(walk_json(
                            r_meta, "cpu", sku, "per_node") or 0)
                        memory_per_node = to_byte(walk_json(
                            r_meta, "memory", sku, "per_node") or 0)

                        # Resource quota proportional to CPU
                        nodes = count / cpu_per_node
                        r_quota["cpu"][sku] = int(nodes * cpu_per_node)
                        r_quota["memory"][sku] = int(nodes * memory_per_node)

                        # Keep consistent for legacy quota
                        # TODO: This is unambiguous in CPU homogeneous cluster
                        quota["None"] = 0

                    success = data_handler.update_vc_resource_quota(
                        vc_name, json.dumps(r_quota), json.dumps(quota))
                    if success:
                        logger.info("updated payload %s for vc %s",
                                    json.dumps(vc_payload), vc_name)
                    else:
                        logger.error("DB error processing payload %s for vc %s",
                                     json.dumps(vc_payload), vc_name)
                        return {
                            "error":
                                "DB error processing payload %s for vc %s" %
                                (json.dumps(vc_payload), vc_name)
                        }, 500

            # Invalidate local vc_cache
            with vc_cache_lock:
                [vc_cache.pop(vc["vcName"], None) for vc in vc_list]

            return {"error": None}, 200
        else:
            return {
                "error":
                    "%s does not have permission to update vc with payload %s" %
                    (username, json.dumps(payload))
            }, 403
    except Exception as e:
        logger.exception("Exception in patch_resource_quota %s for user %s",
                         json.dumps(payload), username)
        return {
            "error":
                "failed to patch resource quota (may succeeded partially), "
                "exception %s" % str(e)
        }, 500


def get_node_status_simplified(node_status):
    if node_status is None:
        return None

    simplified_node_status = []
    for node in node_status:
        # Skip non-workers
        labels = node.get("labels", {})
        not_worker = "worker" not in labels
        if not_worker:
            continue

        # Only keep worker, sku, and vc node labels
        worker_labels = {
            k: v for k, v in labels.items() if k in ["worker", "sku", "vc"]
        }

        simplified_node = {
            "name": node.get("name"),
            "gpu_capacity": node.get("gpu_capacity"),
            "gpu_allocatable": node.get("gpu_capacity"),
            "gpu_used": node.get("gpu_used"),
            "gpu_preemptable_used": node.get("gpu_preemptable_used"),
            "cpu_capacity": node.get("cpu_capacity"),
            "cpu_allocatable": node.get("cpu_allocatable"),
            "cpu_used": node.get("cpu_used"),
            "cpu_preemptable_used": node.get("cpu_preemptable_used"),
            "memory_capacity": node.get("memory_capacity"),
            "memory_allocatable": node.get("memory_allocatable"),
            "memory_used": node.get("memory_used"),
            "memory_preemptable_used": node.get("memory_preemptable_used"),
            "labels": worker_labels,
            "InternalIP": node.get("InternalIP"),
            "unschedulable": node.get("unschedulable"),
            "pods": node.get("pods")
        }
        simplified_node_status.append(simplified_node)

    return simplified_node_status


def get_pod_status_simplified(pod_status):
    if pod_status is None:
        return None

    simplified_pod_status = []
    for pod in pod_status:
        simplified_pod = {
            "name": pod.get("name"),
            "job_id": pod.get("job_id"),
            "username": pod.get("username"),
            "preemption_allowed": pod.get("preemption_allowed"),
            "node_name": pod.get("node_name"),
            "gpu": pod.get("gpu"),
            "cpu": pod.get("cpu"),
            "memory": pod.get("memory"),
            "preemptable_gpu": pod.get("preemptable_gpu"),
            "preemptable_cpu": pod.get("preemptable_cpu"),
            "preemptable_memory": pod.get("preemptable_memory"),
            "gpu_usage": pod.get("gpu_usage"),
        }
        simplified_pod_status.append(simplified_pod)

    return simplified_pod_status


def get_vc_simplified(vc_status):
    if vc_status is None:
        return None

    simplified_vc_status = {
        # VC name
        "vc_name": vc_status.get("vc_name"),

        # Active job count
        "available_job_num": vc_status.get("available_job_num"),

        # GPU overview
        "gpu_capacity": vc_status.get("gpu_capacity"),
        "gpu_used": vc_status.get("gpu_used"),
        "gpu_preemptable_used": vc_status.get("gpu_preemptable_used"),
        "gpu_available": vc_status.get("gpu_available"),
        "gpu_unschedulable": vc_status.get("gpu_unschedulable"),

        # CPU overview
        "cpu_capacity": vc_status.get("cpu_capacity"),
        "cpu_used": vc_status.get("cpu_used"),
        "cpu_preemptable_used": vc_status.get("cpu_preemptable_used"),
        "cpu_available": vc_status.get("cpu_available"),
        "cpu_unschedulable": vc_status.get("cpu_unschedulable"),

        # Memory overview
        "memory_capacity": vc_status.get("memory_capacity"),
        "memory_used": vc_status.get("memory_used"),
        "memory_preemptable_used": vc_status.get("memory_preemptable_used"),
        "memory_available": vc_status.get("memory_available"),
        "memory_unschedulable": vc_status.get("memory_unschedulable"),

        # Nodes
        "node_status": get_node_status_simplified(vc_status.get("node_status")),

        # Pods
        "pod_status": get_pod_status_simplified(vc_status.get("pod_status")),

        # Users
        "user_status": vc_status.get("user_status"),
        "user_status_preemptable": vc_status.get("user_status"),

        # GPU idleness
        "gpu_idle": vc_status.get("gpu_idle"),
    }

    return simplified_vc_status


def get_vc_v2(username, vc_name):
    vc_status = None
    try:
        with DataHandler() as data_handler:
            cluster_status, _ = data_handler.GetClusterStatus()

        vc_statuses = cluster_status.get("vc_statuses", {})
        vc_list = get_vc_list()

        for vc in vc_list:
            if vc["vcName"] == vc_name and \
                    has_access(username, VC, vc_name, USER):
                vc_status = vc_statuses.get(vc_name, {})
                vc_status["vc_name"] = vc_name
                vc_status["node_status"] = cluster_status.get("node_status")
                break

        vc_status = get_vc_simplified(vc_status)

    except:
        logger.exception("Exception in getting VC %s for user %s", vc_name,
                         username)

    return vc_status


def convert_date(obj, field):
    if obj.get(field) is not None:
        obj[field] = obj[field].replace(tzinfo=pytz.UTC).isoformat()
    return obj


def list_public_keys(username):
    with GlobalDBHandler(config["global-mysql"]["hostname"],
                         config["global-mysql"]["username"],
                         config["global-mysql"]["password"]) as handler:
        result = handler.list_public_keys(username)
        return [convert_date(obj, "add_time") for obj in result], 200


def add_public_key(username, key_title, public_key):
    with GlobalDBHandler(config["global-mysql"]["hostname"],
                         config["global-mysql"]["username"],
                         config["global-mysql"]["password"]) as handler:
        try:
            key_id = handler.add_public_key(username, key_title, public_key)
            return {"id": key_id}, 200
        except Exception as e:
            logger.exception("failed to add_public_key %s %s", username,
                             key_title)
            return {"error": "failed to add public key %s" % (str(e))}, 500


def delete_public_key(username, key_id):
    with GlobalDBHandler(config["global-mysql"]["hostname"],
                         config["global-mysql"]["username"],
                         config["global-mysql"]["password"]) as handler:
        try:
            existing_key = handler.get_public_key(key_id)
            if len(existing_key) == 0:
                return {"error": "key not exist"}, 404
            elif len(existing_key) > 1:
                return {"error": "impossible, multiple keys with same id"}, 500

            if existing_key[0]["username"] != username:
                return {"error": "you are not the owner of this key"}, 403

            handler.delete_public_key(key_id)

            return {"error": None}, 200
        except Exception as e:
            logger.exception("failed to delete_public_key %s %s", username,
                             key_id)
            return {"error": "failed to delete public key %s" % (str(e))}, 500


def DeleteVC(userName, vcName):
    ret = None
    dataHandler = DataHandler()
    if AuthorizationManager.IsClusterAdmin(userName):
        ret = dataHandler.DeleteVC(vcName)
        if ret:
            with vc_cache_lock:
                vc_cache.pop(vcName, None)
    else:
        ret = "Access Denied!"
    dataHandler.Close()
    return ret


def UpdateVC(userName, vcName, quota, metadata):
    ret = None
    dataHandler = DataHandler()
    if AuthorizationManager.IsClusterAdmin(userName):
        ret = dataHandler.UpdateVC(vcName, quota, metadata)
        if ret:
            cacheItem = {"vcName": vcName, "quota": quota, "metadata": metadata}
            with vc_cache_lock:
                vc_cache[vcName] = cacheItem
    else:
        ret = "Access Denied!"
    dataHandler.Close()
    return ret


# TODO legacy code, please remove this after all clusters have been running this version(1.7) for
# 1 month. Will have impact on old running job when querying endpoints.
def infer_role_from_pod_name(pod_name):
    """ refer doc string of endpoint_manager.py generate_service_selector """
    parts = pod_name.split("-")
    if len(parts) == 3:
        # job created by framework controller
        uuid, role, idx = parts
        return role, idx
    else:
        if len(parts) == 5:
            return "master", "0"
        else:
            p = re.compile("([a-z]+)([0-9])+")
            match = p.search(parts[-1])
            if match:
                g = match.groups()
                return g[0], g[1]
            else:
                # inference job, do not need this
                return parts[-1], ""


def GetEndpoints(userName, jobId):
    dataHandler = DataHandler()
    ret = []
    try:
        job = dataHandler.GetJobTextFields(jobId,
                                           ["userName", "vcName", "endpoints"])
        if job is not None:
            if job["userName"] == userName or AuthorizationManager.HasAccess(
                    userName, ResourceType.VC, job["vcName"], Permission.Admin):
                endpoints = {}
                if job["endpoints"] is not None:
                    endpoints = json.loads(job["endpoints"])
                for [_, endpoint] in list(endpoints.items()):
                    role_name, role_idx = infer_role_from_pod_name(
                        endpoint["podName"])
                    epItem = {
                        "id": endpoint["id"],
                        "name": endpoint["name"],
                        "username": endpoint["username"],
                        "status": endpoint["status"],
                        "hostNetwork": endpoint["hostNetwork"],
                        "podName": endpoint["podName"],
                        "domain": config["domain"],
                        "role-name": endpoint.get("role-name", role_name),
                        "role-idx": endpoint.get("role-idx", role_idx),
                    }
                    if "podPort" in endpoint:
                        epItem["podPort"] = endpoint["podPort"]
                    if endpoint["status"] == "running":
                        if endpoint["hostNetwork"]:
                            port = int(endpoint["endpointDescription"]["spec"]
                                       ["ports"][0]["port"])
                        else:
                            port = int(
                                walk_json(endpoint,
                                    "endpointDescription", "spec", "ports", 0, "nodePort") or \
                                walk_json(endpoint,
                                    "endpointDescription", "spec", "ports", 0, "node_port")
                                            )
                        epItem["port"] = port
                        if "nodeName" in endpoint:
                            epItem["nodeName"] = endpoint["nodeName"]
                    ret.append(epItem)
    except Exception as e:
        logger.error("Get endpoint exception, ex: %s", str(e))
    finally:
        dataHandler.Close()
    return ret


def is_interactive(endpoints):
    for end in endpoints.keys():
        # if the job opened any endpoint except tensorboard, the job will
        # be deemed as interactive
        if not end.endswith("-tensorboard"):
            return True
    return False


def UpdateEndpoints(userName, jobId, requested_endpoints, interactive_ports):
    dataHandler = DataHandler()
    try:
        job = dataHandler.GetJobTextFields(
            jobId, ["userName", "vcName", "jobParams", "endpoints"])
        if job is None:
            msg = "Job %s cannot be found in database" % jobId
            logger.error(msg)
            return msg, 404

        is_vc_admin = AuthorizationManager.HasAccess(userName, ResourceType.VC,
                                                     job["vcName"],
                                                     Permission.Admin)

        if job["userName"] != userName and (not is_vc_admin):
            msg = "You are not authorized to enable endpoint for job %s" % jobId
            logger.error(msg)
            return msg, 403

        job_params = json.loads(base64decode(job["jobParams"]))
        job_type = job_params["jobtrainingtype"]
        endpoints = {}
        if job["endpoints"] is not None:
            endpoints = json.loads(job["endpoints"])

        is_interactive_before = is_interactive(endpoints)

        # get pods
        pod_names = []
        if job_type == "RegularJob":
            pod_names.append(jobId)
        else:
            nums = {
                "ps": int(job_params["numps"]),
                "worker": int(job_params["numpsworker"])
            }
            for role in ["ps", "worker"]:
                for i in range(nums[role]):
                    pod_names.append(jobId + "-" + role + str(i))

        # HostNetwork
        if "hostNetwork" in job_params and job_params["hostNetwork"] == True:
            host_network = True
        else:
            host_network = False

        # username
        username = getAlias(job["userName"])

        if "ssh" in requested_endpoints:
            # setup ssh for each pod
            for pod_name in pod_names:
                endpoint_id = "e-" + pod_name + "-ssh"

                if endpoint_id in endpoints:
                    logger.debug("Endpoint %s exists. Skip.", endpoint_id)
                    continue
                logger.debug("Endpoint %s does not exist. Add.", endpoint_id)

                endpoint = {
                    "id": endpoint_id,
                    "jobId": jobId,
                    "podName": pod_name,
                    "username": username,
                    "name": "ssh",
                    "status": "pending",
                    "hostNetwork": host_network
                }
                endpoints[endpoint_id] = endpoint

        # Only open Jupyter on the master
        if 'ipython' in requested_endpoints:
            if job_type == "RegularJob":
                pod_name = pod_names[0]
            else:
                # For a distributed job, we set up jupyter on first worker node.
                # PS node does not have GPU access.
                # TODO: Simplify code logic after removing PS
                pod_name = pod_names[1]

            endpoint_id = "e-" + jobId + "-ipython"

            if endpoint_id not in endpoints:
                logger.debug("Endpoint %s does not exist. Add.", endpoint_id)
                endpoint = {
                    "id": endpoint_id,
                    "jobId": jobId,
                    "podName": pod_name,
                    "username": username,
                    "name": "ipython",
                    "status": "pending",
                    "hostNetwork": host_network
                }
                endpoints[endpoint_id] = endpoint
            else:
                logger.debug("Endpoint %s exists. Skip.", endpoint_id)

        # Only open tensorboard on the master
        if 'tensorboard' in requested_endpoints:
            if job_type == "RegularJob":
                pod_name = pod_names[0]
            else:
                # For a distributed job, we set up jupyter on first worker node.
                # PS node does not have GPU access.
                # TODO: Simplify code logic after removing PS
                pod_name = pod_names[1]

            endpoint_id = "e-" + jobId + "-tensorboard"

            if endpoint_id not in endpoints:
                logger.debug("Endpoint %s does not exist. Add.", endpoint_id)
                endpoint = {
                    "id": endpoint_id,
                    "jobId": jobId,
                    "podName": pod_name,
                    "username": username,
                    "name": "tensorboard",
                    "status": "pending",
                    "hostNetwork": host_network
                }
                endpoints[endpoint_id] = endpoint
            else:
                logger.debug("Endpoint %s exists. Skip.", endpoint_id)

        # Only open theia on the master
        if 'theia' in requested_endpoints:
            if job_type == "RegularJob":
                pod_name = pod_names[0]
            else:
                # For a distributed job, we set up jupyter on first worker node.
                # PS node does not have GPU access.
                # TODO: Simplify code logic after removing PS
                pod_name = pod_names[1]

            endpoint_id = "e-" + jobId + "-theia"

            if endpoint_id not in endpoints:
                logger.debug("Endpoint %s does not exist. Add.", endpoint_id)
                endpoint = {
                    "id": endpoint_id,
                    "jobId": jobId,
                    "podName": pod_name,
                    "username": username,
                    "name": "theia",
                    "status": "pending",
                    "hostNetwork": host_network
                }
                endpoints[endpoint_id] = endpoint
            else:
                logger.debug("Endpoint %s exists. Skip.", endpoint_id)

        # interactive port
        for interactive_port in interactive_ports:
            if job_type == "RegularJob":
                pod_name = pod_names[0]
            else:
                # For a distributed job, we set up jupyter on first worker node.
                # PS node does not have GPU access.
                # TODO: Simplify code logic after removing PS
                pod_name = pod_names[1]

            endpoint_id = "e-" + jobId + "-port-" + \
                str(interactive_port["podPort"])
            if endpoint_id not in endpoints:
                logger.debug("Endpoint %s does not exist. Add.", endpoint_id)
                endpoint = {
                    "id": endpoint_id,
                    "jobId": jobId,
                    "podName": pod_name,
                    "username": username,
                    "name": interactive_port["name"],
                    "podPort": interactive_port["podPort"],
                    "status": "pending",
                    "hostNetwork": host_network
                }
                endpoints[endpoint_id] = endpoint
            else:
                logger.debug("Endpoint %s exists. Skip.", endpoint_id)

        is_interactive_after = is_interactive(endpoints)
        allowed = False
        reason = None

        # is_interactive_before | is_interactive_after |  allowed
        #         F             |        F             |     T
        #         F             |        T             |   check
        #         T             |        F             | impossible
        #         T             |        T             |     T

        gpu_request = get_job_total_gpu(job_params)

        if is_vc_admin or \
                gpu_request == 0 or \
                (not (is_interactive_before is False and is_interactive_after is True)):
            allowed = True
        else:
            vc_meta = json.loads(
                walk_json(dataHandler.GetVC(job["vcName"]),
                          "metadata",
                          default="{}"))
            interactive_limit = walk_json(vc_meta, "admin", "interactive_limit")

            if interactive_limit is None:
                allowed = True
            else:
                interactive_limit = int(interactive_limit)
                sku = job_params["sku"]

                status, _ = dataHandler.GetClusterStatus()
                vc_status = walk_json(status, "vc_statuses", job["vcName"])
                required = Gpu({sku: gpu_request})
                interactive_used = Gpu(
                    walk_json(vc_status, "gpu_interactive_used", default={}))
                if required + interactive_used <= interactive_limit:
                    allowed = True
                else:
                    allowed = False
                    reason = "Cannot open interactive endpoint. There are already %s interactive GPUs in the VC, request another %s exceeds the limit of %s. You can ask admin to enable the interactive endpoint." % (
                        interactive_used, gpu_request, interactive_limit)
        if allowed:
            dataHandler.UpdateJobTextFields(
                {"jobId": jobId}, {"endpoints": json.dumps(endpoints)})
            return endpoints, 200
        else:
            logger.error(reason)
            return reason, 403
    except Exception as e:
        logger.error("Get endpoint exception, ex: %s", str(e))
    finally:
        dataHandler.Close()
    return "server error", 500


def get_job(job_id):
    data_handler = None
    try:
        data_handler = DataHandler()
        jobs = data_handler.GetJob(jobId=job_id)
        if len(jobs) == 1:
            return jobs[0]
    except Exception as e:
        logger.error("Exception in get_job: %s" % str(e))
    finally:
        if data_handler is not None:
            data_handler.Close()
    return None


def get_job_priorities():
    dataHandler = DataHandler()
    job_priorites = dataHandler.get_job_priority()
    dataHandler.Close()
    return job_priorites


def update_job_priorites(username, job_priorities):
    if job_priorities is None:
        return "Invalid payload", 400

    data_handler = None
    try:
        data_handler = DataHandler()

        # Only job owner and VC admin can update job priority.
        # Fail job priority update if there is one unauthorized items.
        pending_jobs = {}
        for job_id in job_priorities:
            priority = job_priorities[job_id]
            job = data_handler.GetJobTextFields(
                job_id, ["userName", "vcName", "jobStatus"])
            if job is None:
                continue

            vc_admin = AuthorizationManager.HasAccess(username, ResourceType.VC,
                                                      job["vcName"],
                                                      Permission.Admin)
            if job["userName"] != username and (not vc_admin):
                msg = "Operation aborted. User %s is unauthorized to " \
                      "update priority for job %s" % (job["userName"], job_id)
                return msg, 403

            # Adjust priority based on permission
            permission = Permission.Admin if vc_admin else Permission.User
            job_priorities[job_id] = adjust_job_priority(priority, permission)

            if job["jobStatus"] in ACTIVE_STATUS:
                pending_jobs[job_id] = job_priorities[job_id]

        success = data_handler.update_job_priority(job_priorities)
        if not success:
            return "Internal DB error", 400
        return pending_jobs, 200

    except Exception:
        logger.exception("Failed to update job priorities %s.", job_priorities)

    finally:
        if data_handler is not None:
            data_handler.Close()

    return "Internal server error", 400


def get_job_insight(job_id, username):
    """Get job insight for the specified job.

    Args:
        job_id: Job id for which to get job insight.
        username: Requester username.

    Returns:
        (response message, status code)
    """
    try:
        with DataHandler() as data_handler:
            fields = ["userName", "vcName", "insight"]
            job = data_handler.GetJobTextFields(job_id, fields)

            # Job not found
            if job is None:
                msg = "Job %s requested by user %s cannot be found" % \
                      (job_id, username)
                logger.error(msg)
                return msg, 404

            # Only job owner and VC users/admins can see job insight
            if job["userName"] != username and \
                    not has_access(username, VC, job["vcName"], COLLABORATOR):
                msg = "Unauthorized access to insight for job %s by user %s" % \
                      (job_id, username)
                logger.error(msg)
                return msg, 403

            if job["insight"] is not None:
                insight = json.loads(base64decode(job["insight"]))
            else:
                insight = {}
            logger.info("Insight for job %s is successfully get by user %s",
                        job_id, username)
            return insight, 200
    except Exception:
        msg = "Exception when getting insight for job %s by user %s" % \
              (job_id, username)
        logger.exception(msg)
        return msg, 500


def set_job_insight(job_id, username, insight):
    """Set job insight for the specified job (only by job owner or VC admin).

    Args:
        job_id: Job id for which to set insight.
        username: Requester username.
        insight: Insight content for the job.

    Returns:
        (response message, status code)
    """
    try:
        with DataHandler() as data_handler:
            fields = ["userName", "vcName"]
            job = data_handler.GetJobTextFields(job_id, fields)

            # Job not found
            if job is None:
                msg = "Job %s requested by user %s cannot be found" % \
                      (job_id, username)
                logger.error(msg)
                return msg, 404

            # Only VC admins can set job insight
            if not has_access(username, VC, job["vcName"], ADMIN):
                msg = "Unauthorized to set insight for job %s by user %s" % \
                      (job_id, username)
                logger.error(msg)
                return msg, 403

            if insight is None:
                msg = "Bad insight cannot be set for job %s by user %s" % \
                      (job_id, username)
                logger.error(msg)
                return msg, 400

            cond_fields = {"jobId": job_id}
            data_fields = {"insight": base64encode(json.dumps(insight))}
            ret = data_handler.UpdateJobTextFields(cond_fields, data_fields)
            if ret is True:
                msg = "Insight for job %s is successfully set by user %s" % \
                      (job_id, username)
                logger.info(msg)
                return msg, 200
            else:
                msg = "Internal error on setting insight for job %s by user %s" % \
                      (job_id, username)
                return msg, 500
    except Exception:
        msg = "Exception when setting insight for job %s by user %s" % \
              (job_id, username)
        logger.exception(msg)
        return msg, 500


def set_job_max_time(username, job_id, second):
    dataHandler = DataHandler()
    try:
        job = dataHandler.GetJobTextFields(job_id,
                                           ["userName", "vcName", "jobParams"])

        if job is None:
            msg = "Job %s cannot be found in database" % job_id
            logger.info(msg)
            return msg, 404

        is_admin = has_access(username, VC, job["vcName"], ADMIN)

        if not is_admin:
            msg = "%s is not admin so can not set max running time for job" % username
            logger.info(msg)
            return msg, 403

        job_params = json.loads(base64decode(job["jobParams"]))

        job_params["maxTimeSec"] = second
        dataHandler.UpdateJobTextFields(
            {"jobId": job_id},
            {"jobParams": base64encode(json.dumps(job_params))})
        return "Success", 200
    except Exception as e:
        logger.exception("set job %s/%s max time %s failed", username, job_id,
                         second)
    finally:
        dataHandler.Close()
    return "Server error", 500


def set_repair_message(username, job_id, repair_message):
    """Set repair message for the specified job.

        Args:
            job_id: Job id for which to set repair message.
            username: Requester username.
            repair_message: Repair message content for the job.

        Returns:
            (response message, status code)
        """
    try:
        with DataHandler() as data_handler:
            fields = ["userName", "vcName"]
            job = data_handler.GetJobTextFields(job_id, fields)

            # Job not found
            if job is None:
                msg = "Job %s requested by user %s cannot be found" % \
                      (job_id, username)
                logger.error(msg)
                return msg, 404

            # Only admins can set job repair message
            if not has_access(username, VC, job["vcName"], ADMIN):
                msg = "Unauthorized to set repair message for job %s by user " \
                      "%s" % (job_id, username)
                logger.error(msg)
                return msg, 403

            if repair_message is None:
                msg = "Bad repair message cannot be set for job %s by user " \
                      "%s" % (job_id, username)
                logger.error(msg)
                return msg, 400

            cond_fields = {"jobId": job_id}
            data_fields = {
                "repairMessage": base64encode(json.dumps(repair_message))
            }
            ret = data_handler.UpdateJobTextFields(cond_fields, data_fields)
            if ret is True:
                msg = "Repair message for job %s is successfully set by " \
                      "user %s" % (job_id, username)
                logger.info(msg)
                return msg, 200
            else:
                msg = "Internal error on setting repair message for job %s " \
                      "by user %s" % (job_id, username)
                return msg, 500
    except Exception:
        msg = "Exception when setting repair message for job %s by user %s" % \
              (job_id, username)
        logger.exception(msg)
        return msg, 500


def get_allow_record(username, user):
    try:
        if not is_cluster_admin(username) and username != user:
            msg = "%s is unauthorized to get allow record for %s" % (
                username, user)
            logger.error(msg)
            return msg, 503

        with DataHandler() as data_handler:
            if user == "all":
                ret = data_handler.get_all_allow_records()
            else:
                ret = data_handler.get_allow_record(user)
        for obj in ret:
            convert_date(obj, "valid_until")
            convert_date(obj, "time")
        return ret, 200
    except:
        logger.exception("failed to get allow record for %s by %s",
                         user, username)
    return "Server error", 500


def add_allow_record(username, user, ip):
    try:
        if not is_cluster_admin(username) and username != user:
            msg = "%s is unauthorized to add allow record ip %s for %s" % (
                username, ip, user)
            logger.error(msg)
            return msg, 503

        allow_days = config.get("allow_record_days", 30)
        now = datetime.datetime.utcnow()
        valid_until = (now + datetime.timedelta(days=allow_days)).isoformat()

        with DataHandler() as data_handler:
            success = data_handler.add_allow_record(user, ip, valid_until)

        if not success:
            return "Internal DB error", 500
        else:
            return "Success", 200
    except:
        logger.exception("failed to add allow record ip %s for %s by %s",
                         ip, user, username)
    return "Server error", 500


def delete_allow_record(username, user):
    try:
        if not is_cluster_admin(username) and username != user:
            msg = "%s is unauthorized to delete allow record for %s" % (
                username, user)
            logger.error(msg)
            return msg, 503

        with DataHandler() as data_handler:
            success = data_handler.delete_allow_record(user)

        if not success:
            return "Internal DB error", 500
        else:
            return "Success", 200
    except:
        logger.exception("failed to delete allow record for %s by %s",
                         user, username)
    return "Server error", 500


def getAlias(username):
    if "@" in username:
        username = username.split("@")[0].strip()
    if "/" in username:
        username = username.split("/")[1].strip()
    return username


if __name__ == '__main__':
    TEST_SUB_REG_JOB = False
    TEST_JOB_STATUS = True
    TEST_DEL_JOB = False
    TEST_GET_TB = False
    TEST_GET_SVC = False
    TEST_GET_LOG = False

    if TEST_SUB_REG_JOB:
        parser = argparse.ArgumentParser(description='Launch a kubernetes job')
        parser.add_argument('-f',
                            '--param-file',
                            required=True,
                            type=str,
                            help='Path of the Parameter File')
        parser.add_argument('-t',
                            '--template-file',
                            required=True,
                            type=str,
                            help='Path of the Job Template File')
        args, unknown = parser.parse_known_args()
        with open(args.param_file, "r") as f:
            jobParamsJsonStr = f.read()
        f.close()

        SubmitRegularJob(jobParamsJsonStr, args.template_file)

    if TEST_JOB_STATUS:
        print(GetJobStatus(sys.argv[1]))

    if TEST_DEL_JOB:
        print(DeleteJob("tf-dist-1483504085-13"))

    if TEST_GET_TB:
        print(GetTensorboard("tf-resnet18-1483509537-31"))

    if TEST_GET_SVC:
        print(GetServiceAddress("tf-i-1483566214-12"))

    if TEST_GET_LOG:
        print(GetLog("tf-i-1483566214-12"))
