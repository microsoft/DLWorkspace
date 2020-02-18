#!/usr/bin/env python3

import json
import os
import time
import argparse
import uuid
import sys
import collections
import copy
import requests

import base64
import re
import logging
from cachetools import cached, TTLCache
from threading import Lock

import requests

from config import config
from DataHandler import DataHandler, DataManager
from authorization import ResourceType, Permission, AuthorizationManager, IdentityManager, ACLManager
import authorization
import quota
from job_op import KillOp, PauseOp, ResumeOp, ApproveOp

sys.path.append(os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "../ClusterManager"))

from ResourceInfo import ResourceInfo
from cluster_resource import ClusterResource
from job_params_util import get_resource_params_from_job_params
from JobLogUtils import GetJobLog as UtilsGetJobLog

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
DEFAULT_EXPIRATION = 24 * 30 * 60
vc_cache = TTLCache(maxsize=10240, ttl=DEFAULT_EXPIRATION)
vc_cache_lock = Lock()


def walk_json_field_safe(obj, *fields):
    """ for example a=[{"a": {"b": 2}}]
    walk_json_field_safe(a, 0, "a", "b") will get 2
    walk_json_field_safe(a, 0, "not_exist") will get None
    """
    try:
        for f in fields:
            obj = obj[f]
        return obj
    except:
        return None

def base64encode(str_val):
    return base64.b64encode(str_val.encode("utf-8")).decode("utf-8")


def base64decode(str_val):
    return base64.b64decode(str_val.encode("utf-8")).decode("utf-8")

elasticsearch_deployed = isinstance(config.get('elasticsearch'), list) and len(config['elasticsearch']) > 0

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


def cpu_format(cpu, ratio=1.0):
    """Convert number of cpu to cpu cycle.

    Args:
        cpu: Number of cpu.
        ratio: The percent that can be used.

    Returns:
        Formatted string of cpu cycle if cpu is valid, None otherwise.
    """
    try:
        cpu = float(cpu)
    except:
        return None
    else:
        return "%dm" % int(ratio * cpu * 1000)


def mem_format(memory, ratio=1.0):
    """Convert memory in G to memory requirement.

    Args:
        memory: Memory size in G.
        ratio: The percent that can be used.

    Returns:
        Formatted string of memory size if memory is valid, None otherwise.
    """
    try:
        memory = float(memory)
    except:
        return None
    else:
        return "%dMi" % int(ratio * memory * 1024)


def get_sku_info(sku, config):
    """Returns a sku info dictionary for sku.

    Args:
        sku: String specifying machine's SKU.
        config: Configuration containing sku_meta.

    Returns:
        A dictionary containing sku info for the given machine sku, including
        - cpu
        - cpu usable ratio
        - memory
        - memory usable ratio
        if sku and sku_info in config["sku_meta"] are valid, None otherwise.
    """
    # Ignore invalid sku and sku_info.
    if sku is None:
        return None

    sku_meta = config.get("sku_meta", {})
    sku_info = sku_meta.get(sku, None)
    if sku_info is None:
        return None

    for key in ["cpu", "memory"]:
        if key not in sku_info:
            return None

    # Default sku_info must contain ratio info.
    # Assign 0.8 as default if default values are not defined.
    default_sku_info = sku_meta.get("default", {})

    for key in ["cpu_ratio", "memory_ratio"]:
        if key not in default_sku_info:
            default_sku_info[key] = 0.8

    # Override ratios in sku_info with default values if absent.
    for key in ["cpu_ratio", "memory_ratio"]:
        if key not in sku_info:
            sku_info[key] = default_sku_info[key]

    return sku_info


def populate_cpu_resource(job_params):
    # Ignore if cpuworker is not enabled
    enable_cpuworker = config.get("enable_cpuworker", False)
    if enable_cpuworker is False:
        return

    # Only works for 0-GPU job
    if "resourcegpu" not in job_params or int(job_params["resourcegpu"]) != 0:
        return

    job_training_type = job_params.get("jobtrainingtype", None)
    default_cpu_sku = config.get("default_cpu_sku", "")
    if "sku" not in job_params:
        job_params["sku"] = default_cpu_sku

    default_cpu_request = None
    default_cpu_limit = None
    default_mem_request = None
    default_mem_limit = None

    if job_training_type == "PSDistJob":
        full_node = True
    else:
        full_node = False

    if full_node is True:
        sku = job_params["sku"]
        sku_info = get_sku_info(sku=sku, config=config)
        if sku_info is not None:
            # Do not restrict the limit for full node worker
            default_cpu_request = cpu_format(sku_info["cpu"],
                                             sku_info["cpu_ratio"])
            default_mem_request = mem_format(sku_info["memory"],
                                             sku_info["memory_ratio"])
    else:
        default_cpu_request = cpu_format(config.get("default_cpurequest"))
        default_cpu_limit = cpu_format(config.get("default_cpulimit"))
        default_mem_request = mem_format(config.get("default_memoryrequest"))
        default_mem_limit = mem_format(config.get("default_memorylimit"))

    if "cpurequest" not in job_params and default_cpu_request is not None:
        job_params["cpurequest"] = default_cpu_request
    if "cpulimit" not in job_params and default_cpu_limit is not None:
        job_params["cpulimit"] = default_cpu_limit
    if "memoryrequest" not in job_params and default_mem_request is not None:
        job_params["memoryrequest"] = default_mem_request
    if "memorylimit" not in job_params and default_mem_limit is not None:
        job_params["memorylimit"] = default_mem_limit


def SubmitJob(jobParamsJsonStr):
    ret = {}

    jobParams = LoadJobParams(jobParamsJsonStr)

    if "jobName" not in jobParams or len(jobParams["jobName"].strip()) == 0:
        ret["error"] = "ERROR: Job name cannot be empty"
        return ret
    if "vcName" not in jobParams or len(jobParams["vcName"].strip()) == 0:
        ret["error"] = "ERROR: VC name cannot be empty"
        return ret
    if "userId" not in jobParams or len(jobParams["userId"].strip()) == 0:
        jobParams["userId"] = GetUser(jobParams["userName"])["uid"]

    if "preemptionAllowed" not in jobParams:
        jobParams["preemptionAllowed"] = False
    else:
        jobParams["preemptionAllowed"] = ToBool(jobParams["preemptionAllowed"])

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

    # Populate CPU resource requirement
    populate_cpu_resource(jobParams)

    if "familyToken" not in jobParams or jobParams["familyToken"].isspace():
        jobParams["familyToken"] = uniqId
    if "isParent" not in jobParams:
        jobParams["isParent"] = 1

    userName = getAlias(jobParams["userName"])

    if not AuthorizationManager.HasAccess(jobParams["userName"], ResourceType.VC, jobParams["vcName"].strip(), Permission.User):
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

        if jobParams["jobPath"].startswith("/") or jobParams["jobPath"].startswith("\\"):
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

    if jobParams["workPath"].startswith("/") or jobParams["workPath"].startswith("\\"):
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
        tensorboardParams["jobName"] = "tensorboard-"+jobParams["jobName"]
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
                if AuthorizationManager.HasAccess(jobParams["userName"], ResourceType.VC, jobParams["vcName"].strip(), Permission.Admin):
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
                jobs = data_handler.get_union_job_list(
                    "all",
                    vc_name,
                    num,
                    ACTIVE_STATUS
                )
            else:
                jobs = data_handler.get_union_job_list(
                    username,
                    vc_name,
                    num,
                    ACTIVE_STATUS
                )
            for job in jobs:
                job.pop('jobMeta', None)
    except:
        logger.exception("Exception in getting job list for username %s",
                         username, exc_info=True)
        jobs = []

    return jobs


def get_job_list_v2(username, vc_name, job_owner, num=None):
    try:
        with DataHandler() as data_handler:
            if job_owner == "all" and \
                    has_access(username, VC, vc_name, COLLABORATOR):
                jobs = data_handler.get_union_job_list_v2(
                    "all",
                    vc_name,
                    num,
                    ACTIVE_STATUS
                )
            else:
                jobs = data_handler.get_union_job_list_v2(
                    username,
                    vc_name,
                    num,
                    ACTIVE_STATUS
                )
    except:
        logger.exception("Exception in getting job list v2 for username %s",
                         username, exc_info=True)
        jobs = {}

    return jobs


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
        if job["userName"] == userName or AuthorizationManager.HasAccess(userName, ResourceType.VC, job["vcName"], Permission.Collaborator):
            commands = dataHandler.GetCommands(jobId=jobId)
    dataHandler.Close()
    return commands


def get_access_to_job(username, job):
    is_owner = job["userName"] == username
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
        job = data_handler.GetJobTextFields(
            job_id, ["userName", "vcName", "jobStatus"])

        if job is None:
            return ret

        allowed, role = get_access_to_job(username, job)

        if not allowed:
            logger.info("%s (%s) attempted to %s job %s",
                        username, role, op_name, job_id)
            return ret

        job_status = job["jobStatus"]
        if job_status not in from_states:
            logger.info("%s (%s) attempted to %s a(n) \"%s\" job %s",
                        username, role, op_name, job_status, job_id)
            return ret

        data_fields = {"jobStatus": to_state}
        cond_fields = {"jobId": job_id}
        ret = data_handler.UpdateJobTextFields(cond_fields, data_fields)
        if ret is True:
            logger.info("%s (%s) successfully %s job %s",
                        username, role, op_past_tense, job_id)
        else:
            logger.info("%s (%s) failed to %s job %s",
                        username, role, op_name, job_id)
    return ret


def kill_job(username, job_id):
    return op_job(username, job_id, KillOp())


def pause_job(username, job_id):
    return op_job(username, job_id, PauseOp())


def resume_job(username, job_id):
    return op_job(username, job_id, ResumeOp())


def approve_job(username, job_id):
    return op_job(username, job_id, ApproveOp())


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
            logger.info("%s (%s) attempted to %s job %s",
                        username, role, op_name, job_id)
            continue

        if job_status not in from_states:
            result[job_id] = "cannot %s a(n) \"%s\" job" % (op_name, job_status)
            logger.info("%s (%s) attempted to %s a(n) \"%s\" job %s",
                        username, role, op_name, job_status, job_id)
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
    job_id_batches = [job_ids[x:x+batch_size] for x in batch_starts]

    result = {}
    with DataHandler() as data_handler:
        for job_id_batch in job_id_batches:
            batch_result = _op_jobs_in_one_batch(
                username, job_id_batch, op, data_handler)
            result.update(batch_result)
    return result


def kill_jobs(username, job_ids):
    return op_jobs(username, job_ids, KillOp())


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
        if job["userName"] == userName or AuthorizationManager.HasAccess(userName, ResourceType.VC, job["vcName"], Permission.Collaborator):
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


def GetJobDetail(userName, jobId):
    job = None
    dataHandler = DataHandler()
    jobs = dataHandler.GetJob(jobId=jobId)
    if len(jobs) == 1:
        if jobs[0]["userName"] == userName or AuthorizationManager.HasAccess(userName, ResourceType.VC, jobs[0]["vcName"], Permission.Collaborator):
            job = jobs[0]
            if "jobDescription" in job:
                job.pop("jobDescription", None)
    dataHandler.Close()
    return job


def GetJobDetailV2(userName, jobId):
    job = {}
    dataHandler = None
    try:
        dataHandler = DataHandler()
        jobs = dataHandler.GetJobV2(jobId)
        if len(jobs) == 1:
            if jobs[0]["userName"] == userName or AuthorizationManager.HasAccess(userName, ResourceType.VC, jobs[0]["vcName"], Permission.Collaborator):
                job = jobs[0]
    except Exception as e:
        logger.error(
            "get job detail v2 exception for user: %s, jobId: %s, exception: %s", userName, jobId, str(e))
    finally:
        if dataHandler is not None:
            dataHandler.Close()
    return job


def GetJobStatus(jobId):
    result = None
    dataHandler = DataHandler()
    result = dataHandler.GetJobTextFields(
        jobId, ["jobStatus", "jobTime", "errorMsg"])
    dataHandler.Close()
    return result


def GetJobLog(userName, jobId, cursor=None, size=100):
    dataHandler = DataHandler()
    jobs = dataHandler.GetJob(jobId=jobId)
    if len(jobs) == 1:
        if jobs[0]["userName"] == userName or AuthorizationManager.HasAccess(userName, ResourceType.VC, jobs[0]["vcName"], Permission.Collaborator):
            if elasticsearch_deployed:
                (logs, cursor) = UtilsGetJobLog(jobId, cursor, size)

                pod_logs = {}
                for log in logs:
                    try:
                        pod_name = log["_source"]["kubernetes"]["pod_name"]
                        log = log["_source"]["log"]
                        if pod_name in pod_logs:
                            pod_logs[pod_name] += log
                        else:
                            pod_logs[pod_name] = log
                    except Exception:
                        logging.exception("Failed to parse elasticsearch log: {}".format(log))

                return {
                    "log": pod_logs,
                    "cursor": cursor,
                }
            else:
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
        "log": {},
        "cursor": None,
    }


def GetClusterStatus():
    cluster_status, last_update_time = DataManager.GetClusterStatus()
    return cluster_status, last_update_time


def AddUser(username, uid, gid, groups):
    ret = None
    needToUpdateDB = False

    if uid == authorization.INVALID_ID:
        info = IdentityManager.GetIdentityInfoFromDB(username)
        if info["uid"] == authorization.INVALID_ID:
            needToUpdateDB = True
            info = IdentityManager.GetIdentityInfoFromAD(username)
        uid = info["uid"]
        gid = info["gid"]
        groups = info["groups"]
    else:
        needToUpdateDB = True

    if needToUpdateDB:
        ret = IdentityManager.UpdateIdentityInfo(username, uid, gid, groups)
        ret = ret & ACLManager.UpdateAclIdentityId(username, uid)
    return ret


def GetUser(username):
    return IdentityManager.GetIdentityInfoFromDB(username)


def UpdateAce(userName, identityName, resourceType, resourceName, permissions):
    ret = None
    resourceAclPath = AuthorizationManager.GetResourceAclPath(
        resourceName, resourceType)
    if AuthorizationManager.HasAccess(userName, resourceType, resourceName, Permission.Admin):
        ret =  ACLManager.UpdateAce(identityName, resourceAclPath, permissions, 0)
    else:
        ret = "Access Denied!"
    return ret


def DeleteAce(userName, identityName, resourceType, resourceName):
    ret = None
    resourceAclPath = AuthorizationManager.GetResourceAclPath(
        resourceName, resourceType)
    if AuthorizationManager.HasAccess(userName, resourceType, resourceName, Permission.Admin):
        ret = ACLManager.DeleteAce(identityName, resourceAclPath)
    else:
        ret = "Access Denied!"
    return ret


def AddStorage(userName, vcName, url, storageType, metadata, defaultMountPath):
    ret = None
    dataHandler = DataHandler()
    if AuthorizationManager.IsClusterAdmin(userName):
        ret = dataHandler.AddStorage(
            vcName, url, storageType, metadata, defaultMountPath)
    else:
        ret = "Access Denied!"
    dataHandler.Close()
    return ret


def ListStorages(userName, vcName):
    ret = []
    dataHandler = DataHandler()
    if AuthorizationManager.HasAccess(userName, ResourceType.VC, vcName, Permission.User):
        ret = dataHandler.ListStorages(vcName)
    dataHandler.Close()
    return ret


def DeleteStorage(userName, vcName, url):
    ret = None
    dataHandler = DataHandler()
    if AuthorizationManager.HasAccess(userName, ResourceType.VC, vcName, Permission.Admin):
        ret = dataHandler.DeleteStorage(vcName, url)
    else:
        ret = "Access Denied!"
    dataHandler.Close()
    return ret


def UpdateStorage(userName, vcName, url, storageType, metadata, defaultMountPath):
    ret = None
    dataHandler = DataHandler()
    if AuthorizationManager.HasAccess(userName, ResourceType.VC, vcName, Permission.Admin):
        ret = dataHandler.UpdateStorage(
            vcName, url, storageType, metadata, defaultMountPath)
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
            cacheItem = {
                "vcName": vcName,
                "quota": quota,
                "metadata": metadata
            }
            with vc_cache_lock:
                vc_cache[vcName] = cacheItem
    else:
        ret = "Access Denied!"
    dataHandler.Close()
    return ret


def getClusterVCs():
    vcList = None
    try:
        with vc_cache_lock:
            vcList = copy.deepcopy(list(vc_cache.values()))
    except Exception:
        pass

    if not vcList:
        vcList = DataManager.ListVCs()
        with vc_cache_lock:
            for vc in vcList:
                vc_cache[vc["vcName"]] = vc

    return vcList


def ListVCs(userName):
    ret = []
    vcList = getClusterVCs()

    for vc in vcList:
        if AuthorizationManager.HasAccess(userName, ResourceType.VC, vc["vcName"], Permission.User):
            vc['admin'] = AuthorizationManager.HasAccess(
                userName, ResourceType.VC, vc["vcName"], Permission.Admin)
            ret.append(vc)
    # web portal (client) can filter out Default VC
    return ret


def GetVC(user_name, vc_name):
    # TODO: Expose CPU/memory usage for users
    ret = None
    try:
        with DataHandler() as data_handler:
            cluster_status, _ = data_handler.GetClusterStatus()
            cluster_total = cluster_status["gpu_capacity"]
            cluster_available = cluster_status["gpu_available"]
            cluster_reserved = cluster_status["gpu_reserved"]

            vc_list = getClusterVCs()
            vc_info = {}
            vc_usage = collections.defaultdict(
                lambda:collections.defaultdict(lambda: 0))
            vc_preemptable_usage = collections.defaultdict(
                lambda: collections.defaultdict(lambda: 0))

            for vc in vc_list:
                vc_info[vc["vcName"]] = json.loads(vc["quota"])

            active_job_list = data_handler.GetActiveJobList()
            for job in active_job_list:
                job_vc = job["vcName"]
                job_param = json.loads(base64decode(job["jobParams"]))
                if "gpuType" in job_param:
                    gpu_type = job_param["gpuType"]
                    if not job_param["preemptionAllowed"]:
                        vc_usage[job_vc][gpu_type] += GetJobTotalGpu(job_param)
                    else:
                        vc_preemptable_usage[job_vc][gpu_type] += \
                            GetJobTotalGpu(job_param)

            result = quota.calculate_vc_gpu_counts(cluster_total,
                                                   cluster_available,
                                                   cluster_reserved,
                                                   vc_info,
                                                   vc_usage)

            vc_total, vc_used, vc_available, vc_unschedulable = result

            # Cluster resource calculation
            # Currently including CPU and memory
            cluster_resource_capacity = ClusterResource(
                params={
                    "cpu": cluster_status["cpu_capacity"],
                    "memory": cluster_status["memory_capacity"],
                    "gpu": cluster_status["gpu_capacity"],
                }
            )
            cluster_resource_available = ClusterResource(
                params={
                    "cpu": cluster_status["cpu_available"],
                    "memory": cluster_status["memory_available"],
                    "gpu": cluster_status["gpu_available"],
                }
            )
            cluster_resource_reserved = ClusterResource(
                params={
                    "cpu": cluster_status["cpu_reserved"],
                    "memory": cluster_status["memory_reserved"],
                    "gpu": cluster_status["gpu_reserved"],
                }
            )

            vc_resource_info = {}
            vc_resource_usage = collections.defaultdict(
                lambda: ClusterResource())

            for vc in vc_list:
                res_quota = {}
                try:
                    res_quota = json.loads(vc["resourceQuota"])
                except:
                    logger.exception("Parsing resourceQuota failed for %s", vc)
                vc_resource_info[vc["vcName"]] = ClusterResource(
                    params=res_quota)

            for job in active_job_list:
                job_params = json.loads(base64.b64decode(
                    job["jobParams"].encode("utf-8")).decode("utf-8"))
                job_res = get_resource_params_from_job_params(job_params)
                vc_resource_usage[job["vcName"]] += ClusterResource(
                    params=job_res)

            result = quota.calculate_vc_resources(cluster_resource_capacity,
                                                  cluster_resource_available,
                                                  cluster_resource_reserved,
                                                  vc_resource_info,
                                                  vc_resource_usage)
            (
                vc_resource_total,
                vc_resource_used,
                vc_resource_available,
                vc_resource_unschedulable
            ) = result

            for vc in vc_list:
                if vc["vcName"] == vc_name and AuthorizationManager.HasAccess(
                        user_name, ResourceType.VC, vc_name, Permission.User):

                    user_status = collections.defaultdict(
                        lambda: ResourceInfo())
                    user_status_preemptable = collections.defaultdict(
                        lambda: ResourceInfo())

                    num_active_jobs = 0
                    for job in active_job_list:
                        if job["vcName"] == vc_name and job["jobStatus"] == "running":
                            num_active_jobs += 1
                            username = job["userName"]
                            job_param = json.loads(base64decode(job["jobParams"]))
                            if "gpuType" in job_param:
                                if not job_param["preemptionAllowed"]:
                                    if username not in user_status:
                                        user_status[username] = ResourceInfo()
                                    user_status[username].Add(ResourceInfo({job_param["gpuType"]: GetJobTotalGpu(job_param)}))
                                else:
                                    if username not in user_status_preemptable:
                                        user_status_preemptable[username] = ResourceInfo()
                                    user_status_preemptable[username].Add(ResourceInfo({job_param["gpuType"]: GetJobTotalGpu(job_param)}))

                    vc["gpu_capacity"] = vc_total[vc_name]
                    vc["gpu_used"] = vc_used[vc_name]
                    vc["gpu_preemptable_used"] = vc_preemptable_usage[vc_name]
                    vc["gpu_unschedulable"] = vc_unschedulable[vc_name]
                    # TODO: deprecate typo "gpu_avaliable" in legacy code
                    vc["gpu_avaliable"] = vc_available[vc_name]
                    vc["gpu_available"] = vc_available[vc_name]

                    vc["cpu_capacity"] = vc_resource_total[vc_name].cpu.floor
                    vc["cpu_used"] = vc_resource_used[vc_name].cpu.floor
                    vc["cpu_unschedulable"] = vc_resource_unschedulable[vc_name].cpu.floor
                    vc["cpu_available"] = vc_resource_available[vc_name].cpu.floor

                    vc["memory_capacity"] = vc_resource_total[vc_name].memory.floor
                    vc["memory_used"] = vc_resource_used[vc_name].memory.floor
                    vc["memory_unschedulable"] = vc_resource_unschedulable[vc_name].memory.floor
                    vc["memory_available"] = vc_resource_available[vc_name].memory.floor

                    # TODO: deprecate typo "AvaliableJobNum" in legacy code
                    vc["AvaliableJobNum"] = num_active_jobs
                    vc["available_job_num"] = num_active_jobs

                    vc["node_status"] = cluster_status["node_status"]

                    vc["user_status"] = []
                    for user_name, user_gpu in user_status.items():
                        # TODO: job_manager.getAlias should be put in a util file
                        user_name = user_name.split("@")[0].strip()
                        vc["user_status"].append({"userName": user_name, "userGPU": user_gpu.ToSerializable()})

                    vc["user_status_preemptable"] = []
                    for user_name, user_gpu in user_status_preemptable.items():
                        user_name = user_name.split("@")[0].strip()
                        vc["user_status_preemptable"].append({"userName": user_name, "userGPU": user_gpu.ToSerializable()})

                    try:
                        gpu_idle_url = config["gpu_reporter"] + '/gpu_idle'
                        gpu_idle_params = {"vc": vc_name}
                        gpu_idle_response = requests.get(
                            gpu_idle_url, params=gpu_idle_params)
                        gpu_idle_json = gpu_idle_response.json()
                        vc["gpu_idle"] = gpu_idle_json
                    except Exception:
                        logger.exception("Failed to fetch gpu_idle from "
                                         "gpu-exporter")
                    ret = vc
                    break

    except Exception:
        logger.exception("Exception in GetVC", exc_info=True)

    return ret


def GetJobTotalGpu(jobParams):
    numWorkers = 1
    if "numpsworker" in jobParams:
        numWorkers = int(jobParams["numpsworker"])
    return int(jobParams["resourcegpu"]) * numWorkers


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
            cacheItem = {
                "vcName": vcName,
                "quota": quota,
                "metadata": metadata
            }
            with vc_cache_lock:
                vc_cache[vcName] = cacheItem
    else:
        ret = "Access Denied!"
    dataHandler.Close()
    return ret


def GetEndpoints(userName, jobId):
    dataHandler = DataHandler()
    ret = []
    try:
        job = dataHandler.GetJobTextFields(
            jobId, ["userName", "vcName", "endpoints"])
        if job is not None:
            if job["userName"] == userName or AuthorizationManager.HasAccess(userName, ResourceType.VC, job["vcName"], Permission.Admin):
                endpoints = {}
                if job["endpoints"] is not None:
                    endpoints = json.loads(job["endpoints"])
                for [_, endpoint] in list(endpoints.items()):
                    epItem = {
                        "id": endpoint["id"],
                        "name": endpoint["name"],
                        "username": endpoint["username"],
                        "status": endpoint["status"],
                        "hostNetwork": endpoint["hostNetwork"],
                        "podName": endpoint["podName"],
                        "domain": config["domain"],
                    }
                    if "podPort" in endpoint:
                        epItem["podPort"] = endpoint["podPort"]
                    if endpoint["status"] == "running":
                        if endpoint["hostNetwork"]:
                            port = int(
                                endpoint["endpointDescription"]["spec"]["ports"][0]["port"])
                        else:
                            port = int(
                                walk_json_field_safe(endpoint,
                                    "endpointDescription", "spec", "ports", 0, "nodePort") or \
                                walk_json_field_safe(endpoint,
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


def UpdateEndpoints(userName, jobId, requested_endpoints, interactive_ports):
    dataHandler = DataHandler()
    try:
        job = dataHandler.GetJobTextFields(
            jobId, ["userName", "vcName", "jobParams", "endpoints"])
        if job is None:
            msg = "Job %s cannot be found in database" % jobId
            logger.error(msg)
            return msg, 404
        if job["userName"] != userName and (not AuthorizationManager.HasAccess(userName, ResourceType.VC, job["vcName"], Permission.Admin)):
            msg = "You are not authorized to enable endpoint for job %s" % jobId
            logger.error(msg)
            return msg, 403

        job_params = json.loads(base64decode(job["jobParams"]))
        job_type = job_params["jobtrainingtype"]
        job_endpoints = {}
        if job["endpoints"] is not None:
            job_endpoints = json.loads(job["endpoints"])

        # get pods
        pod_names = []
        if job_type == "RegularJob":
            pod_names.append(jobId)
        else:
            nums = {"ps": int(job_params["numps"]), "worker": int(
                job_params["numpsworker"])}
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

        endpoints = job_endpoints

        if "ssh" in requested_endpoints:
            # setup ssh for each pod
            for pod_name in pod_names:
                endpoint_id = "e-" + pod_name + "-ssh"

                if endpoint_id in job_endpoints:
                    logger.info("Endpoint %s exists. Skip.", endpoint_id)
                    continue
                logger.info("Endpoint %s does not exist. Add.", endpoint_id)

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

            if endpoint_id not in job_endpoints:
                logger.info("Endpoint %s does not exist. Add.", endpoint_id)
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
                logger.info("Endpoint %s exists. Skip.", endpoint_id)

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

            if endpoint_id not in job_endpoints:
                logger.info("Endpoint %s does not exist. Add.", endpoint_id)
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
                logger.info("Endpoint %s exists. Skip.", endpoint_id)

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
            if endpoint_id not in job_endpoints:
                logger.info("Endpoint %s does not exist. Add.", endpoint_id)
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
                logger.info("Endpoint %s exists. Skip.", endpoint_id)

        dataHandler.UpdateJobTextField(
            jobId, "endpoints", json.dumps(endpoints))
        return endpoints, 200
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


def update_job(job_id, field, value):
    dataHandler = DataHandler()
    dataHandler.UpdateJobTextField(job_id, field, value)
    dataHandler.Close()


def get_job_priorities():
    dataHandler = DataHandler()
    job_priorites = dataHandler.get_job_priority()
    dataHandler.Close()
    return job_priorites


def update_job_priorites(username, job_priorities):
    data_handler = None
    try:
        data_handler = DataHandler()

        # Only job owner and VC admin can update job priority.
        # Fail job priority update if there is one unauthorized items.
        pendingJobs = {}
        for job_id in job_priorities:
            priority = job_priorities[job_id]
            job = data_handler.GetJobTextFields(
                job_id, ["userName", "vcName", "jobStatus"])
            if job is None:
                continue

            vc_admin = AuthorizationManager.HasAccess(
                username, ResourceType.VC, job["vcName"], Permission.Admin)
            if job["userName"] != username and (not vc_admin):
                return False

            # Adjust priority based on permission
            permission = Permission.Admin if vc_admin else Permission.User
            job_priorities[job_id] = adjust_job_priority(priority, permission)

            if job["jobStatus"] in ACTIVE_STATUS:
                pendingJobs[job_id] = job_priorities[job_id]

        ret_code = data_handler.update_job_priority(job_priorities)
        return ret_code, pendingJobs

    except Exception as e:
        logger.error("Exception when updating job priorities: %s" % e)

    finally:
        if data_handler is not None:
            data_handler.Close()


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
        parser.add_argument('-f', '--param-file', required=True, type=str,
                            help='Path of the Parameter File')
        parser.add_argument('-t', '--template-file', required=True, type=str,
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
