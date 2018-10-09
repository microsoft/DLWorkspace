import json
import os
import time
import argparse
import uuid
import subprocess
import sys
from jobs_tensorboard import GenTensorboardMeta

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../storage"))

import yaml
from jinja2 import Environment, FileSystemLoader, Template
from config import config
from DataHandler import DataHandler
import base64
import re

from config import global_vars
from MyLogger import MyLogger

import copy

logger = MyLogger()

def LoadJobParams(jobParamsJsonStr):
    return json.loads(jobParamsJsonStr)



def SubmitJob(jobParamsJsonStr):
    ret = {}

    jobParams = LoadJobParams(jobParamsJsonStr)

    if "jobName" not in jobParams or len(jobParams["jobName"].strip()) == 0:
        ret["error"] = "ERROR: Job name cannot be empty"
        return ret
    

    if "jobId" not in jobParams or jobParams["jobId"] == "":
        #jobParams["jobId"] = jobParams["jobName"] + "-" + str(uuid.uuid4()) 
        #jobParams["jobId"] = jobParams["jobName"] + "-" + str(time.time())
        jobParams["jobId"] = str(uuid.uuid4()) 
    #jobParams["jobId"] = jobParams["jobId"].replace("_","-").replace(".","-")

    if "resourcegpu" not in jobParams:
        jobParams["resourcegpu"] = 0

    if isinstance(jobParams["resourcegpu"], basestring):
        if len(jobParams["resourcegpu"].strip()) == 0:
            jobParams["resourcegpu"] = 0
        else:
            jobParams["resourcegpu"] = int(jobParams["resourcegpu"])

    if "familyToken" not in jobParams or jobParams["familyToken"].isspace():
        jobParams["familyToken"] = str(uuid.uuid4())
    if "isParent" not in jobParams:
        jobParams["isParent"] = 1
    
    userName = jobParams["userName"]
    if "@" in userName:
        userName = userName.split("@")[0].strip()

    if "/" in userName:
        userName = userName.split("/")[1].strip()

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

        tensorboardParams["jobId"] = str(uuid.uuid4()) 
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
        else:
            ret["error"] = "Cannot schedule job. Cannot add job into database."



    dataHandler.Close()
    return ret



def GetJobList(userName,num=None):
    try:
        dataHandler = DataHandler()
        jobs = []

        if userName != "all":
            jobs = jobs + dataHandler.GetJobList(userName,None, "running,queued,scheduling,unapproved", ("=","or"))
            jobs = jobs + dataHandler.GetJobList(userName,num, "running,queued,scheduling,unapproved", ("<>","and"))
        else:
            jobs = dataHandler.GetJobList(userName,None, "error,failed,finished,killed", ("<>","and"))

        for job in jobs:
            job.pop('jobMeta', None)
        dataHandler.Close()
        return jobs
    except Exception, e:
        logger.error('Exception: '+ str(e))
        logger.warn("Fail to get job list for user %s, return empty list" % userName)
        return []


def GetCommands(jobId):
    dataHandler = DataHandler()
    commands = dataHandler.GetCommands(jobId=jobId);
    dataHandler.Close()
    return commands


def KillJob(jobId):
    ret = True
    dataHandler = DataHandler()
    jobs = dataHandler.GetJob(jobId=jobId)
    if len(jobs) == 1:
        job = jobs[0]
        if job["isParent"] == 1:
            for currJob in dataHandler.GetJob(familyToken=job["familyToken"]):
                ret = ret and dataHandler.KillJob(currJob["jobId"])
        else:
            ret = dataHandler.KillJob(jobId)
    else:
        ret = False
    dataHandler.Close()
    return ret


def AddCommand(jobId,command):
    dataHandler = DataHandler()
    ret = False
    jobs =  dataHandler.GetJob(jobId=jobId)
    if len(jobs) == 1:
        ret = dataHandler.AddCommand(jobId,command)
    dataHandler.Close()
    return ret


def ApproveJob(jobId):
    dataHandler = DataHandler()
    ret = False
    jobs =  dataHandler.GetJob(jobId=jobId)
    if len(jobs) == 1:
        ret = dataHandler.ApproveJob(jobId)
    dataHandler.Close()
    return ret

def isBase64(s):
    try:
        if base64.b64encode(base64.b64decode(s)) == s:
            return True
    except Exception as e:
        pass
    return False

def GetJobDetail(jobId):
    job = None
    dataHandler = DataHandler()
    jobs =  dataHandler.GetJob(jobId=jobId)
    if len(jobs) == 1:
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


def GetClusterStatus():
    job = None
    dataHandler = DataHandler()
    cluster_status,last_update_time =  dataHandler.GetClusterStatus()
    dataHandler.Close()
    return cluster_status,last_update_time


def AddUser(username,userId):
    ret = None
    dataHandler = DataHandler()
    ret =  dataHandler.AddUser(username,userId)
    dataHandler.Close()
    return ret


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
