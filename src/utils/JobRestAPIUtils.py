import json
import os
import time
import argparse
import uuid
import subprocess
import sys
import collections
import copy

from jobs_tensorboard import GenTensorboardMeta

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../storage"))

import yaml
from jinja2 import Environment, FileSystemLoader, Template
from config import config
from DataHandler import DataHandler,DataManager
import base64
import re
import requests

from config import global_vars
from authorization import ResourceType, Permission, AuthorizationManager, IdentityManager, ACLManager
import authorization
from cache import CacheManager
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../ClusterManager"))
from ResourceInfo import ResourceInfo
import quota

import copy
import logging
from cachetools import cached, TTLCache
from threading import Lock


DEFAULT_JOB_PRIORITY = 100
USER_JOB_PRIORITY_RANGE = (100, 200)
ADMIN_JOB_PRIORITY_RANGE = (1, 1000)


logger = logging.getLogger(__name__)

pendingStatus = "running,queued,scheduling,unapproved,pausing,paused"
DEFAULT_EXPIRATION = 24 * 30 * 60
vc_cache = TTLCache(maxsize=10240, ttl=DEFAULT_EXPIRATION)
vc_cache_lock = Lock()

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
    if isinstance(value, basestring):
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

    if isinstance(jobParams["resourcegpu"], basestring):
        if len(jobParams["resourcegpu"].strip()) == 0:
            jobParams["resourcegpu"] = 0
        else:
            jobParams["resourcegpu"] = int(jobParams["resourcegpu"])

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
            jobParams["jobPath"] = os.path.join(userName,jobParams["jobPath"])

    else:
        jobPath = userName+"/"+ "jobs/"+time.strftime("%y%m%d")+"/"+jobParams["jobId"]
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
        jobParams["workPath"] = os.path.join(userName,jobParams["workPath"])

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

    jobParams["dataPath"] = jobParams["dataPath"].replace("\\","/")
    jobParams["workPath"] = jobParams["workPath"].replace("\\","/")
    jobParams["jobPath"] = jobParams["jobPath"].replace("\\","/")
    jobParams["dataPath"] = os.path.realpath(os.path.join("/",jobParams["dataPath"]))[1:]
    jobParams["workPath"] = os.path.realpath(os.path.join("/",jobParams["workPath"]))[1:]
    jobParams["jobPath"] = os.path.realpath(os.path.join("/",jobParams["jobPath"]))[1:]

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
            #if not match is None:
            #    tensorboardParams["cmd"] = match.group(1) + "/worker0" + match.group(2)

        tensorboardParams["jobId"] = uniqId
        tensorboardParams["jobName"] = "tensorboard-"+jobParams["jobName"]
        tensorboardParams["jobPath"] = jobPath
        tensorboardParams["jobType"] = "visualization"
        tensorboardParams["cmd"] = "tensorboard --logdir " + tensorboardParams["logDir"] + " --host 0.0.0.0"
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


def GetJobList(userName, vcName, jobOwner, num=None):
    try:
        dataHandler = DataHandler()
        jobs = []
        hasAccessOnAllJobs = False

        if AuthorizationManager.HasAccess(userName, ResourceType.VC, vcName, Permission.Collaborator):
            hasAccessOnAllJobs = True

        if jobOwner != "all" or not hasAccessOnAllJobs:
            jobs = jobs + GetUserPendingJobs(userName, vcName)
            jobs = jobs + dataHandler.GetJobList(userName,vcName,num, "running,queued,scheduling,unapproved,pausing,paused", ("<>","and"))
        else:
            jobs = GetUserPendingJobs(jobOwner, vcName)

        for job in jobs:
            job.pop('jobMeta', None)
        dataHandler.Close()
        return jobs
    except Exception as e:
        logger.error('Exception: %s', str(e))
        logger.warn("Fail to get job list for user %s, return empty list", userName)
        return []

def GetJobListV2(userName, vcName, jobOwner, num=None):
    jobs = {}
    dataHandler = None
    try:
        dataHandler = DataHandler()

        hasAccessOnAllJobs = False
        if jobOwner == "all":
            hasAccessOnAllJobs = AuthorizationManager.HasAccess(userName, ResourceType.VC, vcName, Permission.Collaborator)

        # if user needs to access all jobs, and has been authorized, he could get all pending jobs; otherwise, he could get his own jobs with all status
        if hasAccessOnAllJobs:
            jobs = dataHandler.GetJobListV2("all", vcName, num, pendingStatus, ("=","or"))
        else:
            jobs = dataHandler.GetJobListV2(userName, vcName, num)
    except Exception as e:
        logger.error('get job list V2 Exception: user: %s, ex: %s', userName, str(e))
    finally:
        if dataHandler is not None:
            dataHandler.Close()
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


def KillJob(userName, jobId):
    ret = False
    dataHandler = DataHandler()
    job = dataHandler.GetJobTextFields(jobId, ["userName", "vcName", "jobStatus", "isParent", "familyToken"])
    if job is not None and job["jobStatus"] in pendingStatus.split(","):
        if job["userName"] == userName or AuthorizationManager.HasAccess(userName, ResourceType.VC, job["vcName"], Permission.Admin):
            dataFields = {"jobStatus": "killing"}
            conditionFields = {"jobId": jobId}
            if job["isParent"] == 1:
                conditionFields = {"familyToken": job["familyToken"]}
            ret = dataHandler.UpdateJobTextFields(conditionFields, dataFields)
    dataHandler.Close()
    return ret


def AddCommand(userName, jobId,command):
    dataHandler = DataHandler()
    ret = False
    job = dataHandler.GetJobTextFields(jobId, ["userName", "vcName"])
    if job is not None:
        if job["userName"] == userName or AuthorizationManager.HasAccess(userName, ResourceType.VC, job["vcName"], Permission.Collaborator):
            ret = dataHandler.AddCommand(jobId,command)
    dataHandler.Close()
    return ret


def ApproveJob(userName, jobId):
    dataHandler = DataHandler()
    ret = False
    job = dataHandler.GetJobTextFields(jobId, ["vcName", "jobStatus"])
    if job is not None and job["jobStatus"] == "unapproved":
        if AuthorizationManager.HasAccess(userName, ResourceType.VC, job["vcName"], Permission.Admin):
            ret = dataHandler.UpdateJobTextField(jobId,"jobStatus","queued")
    dataHandler.Close()
    return ret


def ResumeJob(userName, jobId):
    dataHandler = DataHandler()
    ret = False
    job = dataHandler.GetJobTextFields(jobId, ["userName", "vcName", "jobStatus"])
    if job is not None and job["jobStatus"] == "paused":
        if job["userName"] == userName or AuthorizationManager.HasAccess(userName, ResourceType.VC, job["vcName"], Permission.Collaborator):
            ret = dataHandler.UpdateJobTextField(jobId, "jobStatus", "unapproved")
    dataHandler.Close()
    return ret


def PauseJob(userName, jobId):
    dataHandler = DataHandler()
    ret = False
    job = dataHandler.GetJobTextFields(jobId, ["userName", "vcName", "jobStatus"])
    if job is not None and job["jobStatus"] in ["unapproved", "queued", "scheduling", "running"]:
        if job["userName"] == userName or AuthorizationManager.HasAccess(userName, ResourceType.VC, job["vcName"], Permission.Admin):
            ret = dataHandler.UpdateJobTextField(jobId,"jobStatus","pausing")
    dataHandler.Close()
    return ret


def isBase64(s):
    try:
        if base64.b64encode(base64.b64decode(s)) == s:
            return True
    except Exception as e:
        pass
    return False


def GetJobDetail(userName, jobId):
    job = None
    dataHandler = DataHandler()
    jobs =  dataHandler.GetJob(jobId=jobId)
    if len(jobs) == 1:
        if jobs[0]["userName"] == userName or AuthorizationManager.HasAccess(userName, ResourceType.VC, jobs[0]["vcName"], Permission.Collaborator):
            job = jobs[0]
            job["log"] = ""
            #jobParams = json.loads(base64.b64decode(job["jobMeta"]))
            #jobPath,workPath,dataPath = GetStoragePath(jobParams["jobPath"],jobParams["workPath"],jobParams["dataPath"])
            #localJobPath = os.path.join(config["storage-mount-path"],jobPath)
            #logPath = os.path.join(localJobPath,"joblog.txt")
            #print logPath
            #if os.path.isfile(logPath):
            #    with open(logPath, 'r') as f:
            #        log = f.read()
            #        job["log"] = log
            #    f.close()
            if "jobDescription" in job:
                job.pop("jobDescription",None)
            try:
                log = dataHandler.GetJobTextField(jobId,"jobLog")
                try:
                    if isBase64(log):
                        log = base64.b64decode(log)
                except Exception:
                    pass
                if log is not None:
                    job["log"] = log
            except:
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
            if jobs[0]["userName"] == userName or AuthorizationManager.HasAccess(userName, ResourceType.VC, jobs[0]["vcName"], Permission.Collaborator):
                job = jobs[0]
    except Exception as e:
        logger.error("get job detail v2 exception for user: %s, jobId: %s, exception: %s", userName, jobId, str(e))
    finally:
        if dataHandler is not None:
            dataHandler.Close()
    return job

def GetJobStatus(jobId):
    result = None
    dataHandler = DataHandler()
    result = dataHandler.GetJobTextFields(jobId, ["jobStatus", "jobTime", "errorMsg"])
    dataHandler.Close()
    return result

def GetJobLog(userName, jobId):
    dataHandler = DataHandler()
    jobs =  dataHandler.GetJob(jobId=jobId)
    if len(jobs) == 1:
        if jobs[0]["userName"] == userName or AuthorizationManager.HasAccess(userName, ResourceType.VC, jobs[0]["vcName"], Permission.Collaborator):
            try:
                log = dataHandler.GetJobTextField(jobId,"jobLog")
                try:
                    if isBase64(log):
                        log = base64.b64decode(log)
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
    cluster_status,last_update_time =  DataManager.GetClusterStatus()
    return cluster_status,last_update_time


def AddUser(username,uid,gid,groups):
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
        ret = ret & ACLManager.UpdateAclIdentityId(username,uid)
    return ret


def GetUser(username):
    return IdentityManager.GetIdentityInfoFromDB(username)


def UpdateAce(userName, identityName, resourceType, resourceName, permissions):
    ret = None
    resourceAclPath = AuthorizationManager.GetResourceAclPath(resourceName, resourceType)
    if AuthorizationManager.HasAccess(userName, resourceType, resourceName, Permission.Admin):
        ret =  ACLManager.UpdateAce(identityName, resourceAclPath, permissions, 0)
    else:
        ret = "Access Denied!"
    return ret


def DeleteAce(userName, identityName, resourceType, resourceName):
    ret = None
    resourceAclPath = AuthorizationManager.GetResourceAclPath(resourceName, resourceType)
    if AuthorizationManager.HasAccess(userName, resourceType, resourceName, Permission.Admin):
        ret =  ACLManager.DeleteAce(identityName, resourceAclPath)
    else:
        ret = "Access Denied!"
    return ret


def AddStorage(userName, vcName, url, storageType, metadata, defaultMountPath):
    ret = None
    dataHandler = DataHandler()
    if AuthorizationManager.IsClusterAdmin(userName):
        ret =  dataHandler.AddStorage(vcName, url, storageType, metadata, defaultMountPath)
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
        ret =  dataHandler.DeleteStorage(vcName, url)
    else:
        ret = "Access Denied!"
    dataHandler.Close()
    return ret


def UpdateStorage(userName, vcName, url, storageType, metadata, defaultMountPath):
    ret = None
    dataHandler = DataHandler()
    if AuthorizationManager.HasAccess(userName, ResourceType.VC, vcName, Permission.Admin):
        ret =  dataHandler.UpdateStorage(vcName, url, storageType, metadata, defaultMountPath)
    else:
        ret = "Access Denied!"
    dataHandler.Close()
    return ret


def AddVC(userName, vcName, quota, metadata):
    ret = None
    dataHandler = DataHandler()
    if AuthorizationManager.IsClusterAdmin(userName):
        ret =  dataHandler.AddVC(vcName, quota, metadata)
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
            vcList = copy.deepcopy(vc_cache.values())
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
            vc['admin'] = AuthorizationManager.HasAccess(userName, ResourceType.VC, vc["vcName"], Permission.Admin)
            ret.append(vc)
    # web portal (client) can filter out Default VC
    return ret

def GetVC(userName, vcName):
    ret = None

    data_handler = DataHandler()

    cluster_status, _ = data_handler.GetClusterStatus()
    cluster_total = cluster_status["gpu_capacity"]
    cluster_available = cluster_status["gpu_avaliable"]
    cluster_reserved = cluster_status["gpu_reserved"]

    user_status = collections.defaultdict(lambda : ResourceInfo())
    user_status_preemptable = collections.defaultdict(lambda : ResourceInfo())

    vc_list = getClusterVCs()
    vc_info = {}
    vc_usage = collections.defaultdict(lambda :
            collections.defaultdict(lambda : 0))
    vc_preemptable_usage = collections.defaultdict(lambda :
            collections.defaultdict(lambda : 0))

    for vc in vc_list:
        vc_info[vc["vcName"]] = json.loads(vc["quota"])

    active_job_list = data_handler.GetActiveJobList()
    for job in active_job_list:
        jobParam = json.loads(base64.b64decode(job["jobParams"]))
        if "gpuType" in jobParam:
            if not jobParam["preemptionAllowed"]:
                vc_usage[job["vcName"]][jobParam["gpuType"]] += GetJobTotalGpu(jobParam)
            else:
                vc_preemptable_usage[job["vcName"]][jobParam["gpuType"]] += GetJobTotalGpu(jobParam)

    result = quota.calculate_vc_gpu_counts(cluster_total, cluster_available,
            cluster_reserved, vc_info, vc_usage)

    vc_total, vc_used, vc_available, vc_unschedulable = result

    for vc in vc_list:
        if vc["vcName"] == vcName and AuthorizationManager.HasAccess(userName, ResourceType.VC, vcName, Permission.User):

            num_active_jobs = 0
            for job in active_job_list:
                if job["vcName"] == vcName and job["jobStatus"] == "running":
                    num_active_jobs += 1
                    username = job["userName"]
                    jobParam = json.loads(base64.b64decode(job["jobParams"]))
                    if "gpuType" in jobParam:
                        if not jobParam["preemptionAllowed"]:
                            if username not in user_status:
                                user_status[username] = ResourceInfo()
                            user_status[username].Add(ResourceInfo({jobParam["gpuType"] : GetJobTotalGpu(jobParam)}))
                        else:
                            if username not in user_status_preemptable:
                                user_status_preemptable[username] = ResourceInfo()
                            user_status_preemptable[username].Add(ResourceInfo({jobParam["gpuType"] : GetJobTotalGpu(jobParam)}))

            vc["gpu_capacity"] = vc_total[vcName]
            vc["gpu_used"] = vc_used[vcName]
            vc["gpu_preemptable_used"] = vc_preemptable_usage[vcName]
            vc["gpu_unschedulable"] = vc_unschedulable[vcName]
            vc["gpu_avaliable"] = vc_available[vcName]
            vc["AvaliableJobNum"] = num_active_jobs
            vc["node_status"] = cluster_status["node_status"]
            vc["user_status"] = []
            for user_name, user_gpu in user_status.iteritems():
                # TODO: job_manager.getAlias should be put in a util file
                user_name = user_name.split("@")[0].strip()
                vc["user_status"].append({"userName":user_name, "userGPU":user_gpu.ToSerializable()})

            vc["user_status_preemptable"] = []
            for user_name, user_gpu in user_status_preemptable.iteritems():
                user_name = user_name.split("@")[0].strip()
                vc["user_status_preemptable"].append({"userName": user_name, "userGPU": user_gpu.ToSerializable()})

            try:
                gpu_idle_url = config["gpu_reporter"] + '/gpu_idle'
                gpu_idle_params = {"vc": vcName}
                gpu_idle_response = requests.get(gpu_idle_url, params=gpu_idle_params)
                gpu_idle_json = gpu_idle_response.json()
                vc["gpu_idle"] = gpu_idle_json
            except Exception:
                logger.exception("Failed to fetch gpu_idle from gpu-exporter")

            ret = vc
            break
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
        ret =  dataHandler.DeleteVC(vcName)
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
        ret =  dataHandler.UpdateVC(vcName, quota, metadata)
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
        job = dataHandler.GetJobTextFields(jobId, ["userName", "vcName", "endpoints"])
        if job is not None:
            if job["userName"] == userName or AuthorizationManager.HasAccess(userName, ResourceType.VC, job["vcName"], Permission.Admin):
                endpoints = {}
                if job["endpoints"] is not None:
                    endpoints = json.loads(job["endpoints"])
                for [_, endpoint] in endpoints.items():
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
                            port = int(endpoint["endpointDescription"]["spec"]["ports"][0]["port"])
                        else:
                            port = int(endpoint["endpointDescription"]["spec"]["ports"][0]["nodePort"])
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
        job = dataHandler.GetJobTextFields(jobId, ["userName", "vcName", "jobParams", "endpoints"])
        if job is None:
            msg = "Job %s cannot be found in database" % jobId
            logger.error(msg)
            return msg, 404
        if job["userName"] != userName and (not AuthorizationManager.HasAccess(userName, ResourceType.VC, job["vcName"], Permission.Admin)):
            msg = "You are not authorized to enable endpoint for job %s" % jobId
            logger.error(msg)
            return msg, 403

        job_params = json.loads(base64.b64decode(job["jobParams"]))
        job_type = job_params["jobtrainingtype"]
        job_endpoints = {}
        if job["endpoints"] is not None:
            job_endpoints = json.loads(job["endpoints"])

        # get pods
        pod_names = []
        if job_type == "RegularJob":
            pod_names.append(jobId)
        else:
            nums = {"ps": int(job_params["numps"]), "worker": int(job_params["numpsworker"])}
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

            endpoint_id = "e-" + jobId + "-port-" + str(interactive_port["podPort"])
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

        dataHandler.UpdateJobTextField(jobId, "endpoints", json.dumps(endpoints))
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
            job = data_handler.GetJobTextFields(job_id, ["userName", "vcName", "jobStatus"])
            if job is None:
                continue

            vc_admin = AuthorizationManager.HasAccess(username, ResourceType.VC, job["vcName"], Permission.Admin)
            if job["userName"] != username and (not vc_admin):
                return False

            # Adjust priority based on permission
            permission = Permission.Admin if vc_admin else Permission.User
            job_priorities[job_id] = adjust_job_priority(priority, permission)

            if job["jobStatus"] in pendingStatus.split(","):
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
                            help = 'Path of the Parameter File')
        parser.add_argument('-t', '--template-file', required=True, type=str,
                            help = 'Path of the Job Template File')
        args, unknown = parser.parse_known_args()
        with open(args.param_file,"r") as f:
            jobParamsJsonStr = f.read()
        f.close()

        SubmitRegularJob(jobParamsJsonStr,args.template_file)

    if TEST_JOB_STATUS:
        print GetJobStatus(sys.argv[1])

    if TEST_DEL_JOB:
        print DeleteJob("tf-dist-1483504085-13")

    if TEST_GET_TB:
        print GetTensorboard("tf-resnet18-1483509537-31")

    if TEST_GET_SVC:
        print GetServiceAddress("tf-i-1483566214-12")

    if TEST_GET_LOG:
        print GetLog("tf-i-1483566214-12")
