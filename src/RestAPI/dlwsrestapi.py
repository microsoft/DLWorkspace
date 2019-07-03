import sys
import json
import os

from flask import Flask
from flask_restful import reqparse, abort, Api, Resource
from flask import request, jsonify
import base64
import yaml
import uuid

import logging
import timeit
from logging.config import dictConfig
import thread

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../utils"))
#from JobRestAPIUtils import SubmitDistJob, GetJobList, GetJobStatus, DeleteJob, GetTensorboard, GetServiceAddress, GetLog, GetJob
import JobRestAPIUtils
from authorization import ResourceType, Permission, AuthorizationManager
from config import config
from config import global_vars
import authorization
from DataHandler import DataHandler

import time
import sys
import traceback
import threading

dir_path = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(dir_path, 'logging.yaml'), 'r') as f:
    logging_config = yaml.load(f)
    dictConfig(logging_config)
logger = logging.getLogger('restfulapi')
global_vars["logger"] = logger

app = Flask(__name__)
api = Api(app)
verbose = True
logger.info( "------------------- Restful API started ------------------------------------- ")
logger.info("%s" % config )

if "initAdminAccess" not in global_vars or not global_vars["initAdminAccess"]:
    logger.info("===========Init Admin Access===============")
    global_vars["initAdminAccess"] = True
    logger.info('setting admin access!')
    AuthorizationManager.UpdateAce("Administrator", AuthorizationManager.GetResourceAclPath("", ResourceType.Cluster), Permission.Admin, False)
    logger.info('admin access given!')


def _stacktraces():
   code = []
   for threadId, stack in sys._current_frames().items():
       code.append("\n# ThreadID: %s" % threadId)
       for filename, lineno, name, line in traceback.extract_stack(stack):
           code.append('File: "%s", line %d, in %s' % (filename, lineno, name))
           if line:
               code.append("  %s" % (line.strip()))

   for line in code:
       print("_stacktrace: " + line)


def _WorkerThreadFunc():
   while True:
       _stacktraces()
       time.sleep(60)

#workerThread = threading.Thread(target=_WorkerThreadFunc, args=())
#workerThread.daemon = True
#workerThread.start()


def istrue(value):
    if isinstance(value, bool):
        return value
    elif isinstance(value, basestring):
        return value.lower()[0]=='y'
    else:
        return bool(value)

def tolist(value):
    if isinstance( value, basestring):
        if len(value)>0:
            return [value]
        else:
            return []
    else:
        return value

def getAlias(username):
    if "@" in username:
        username = username.split("@")[0].strip()
    if "/" in username:
        username = username.split("/")[1].strip()
    return username

class SubmitJob(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('jobName')
        parser.add_argument('resourcegpu')
        parser.add_argument('gpuType')
        parser.add_argument('workPath')
        parser.add_argument('dataPath')
        parser.add_argument('jobPath')
        parser.add_argument('image')
        parser.add_argument('cmd')
        parser.add_argument('logDir')
        parser.add_argument('interactivePort')
        parser.add_argument('userName')
        parser.add_argument('vcName')
        parser.add_argument('preemptionAllowed')
        parser.add_argument('userId')
        parser.add_argument('runningasroot')
        parser.add_argument('containerUserId')

        parser.add_argument('familyToken')
        parser.add_argument('isParent')
        parser.add_argument('jobType')
        parser.add_argument('nodeSelector')


        parser.add_argument('jobtrainingtype')
        parser.add_argument('numpsworker')
        parser.add_argument('nummpiworker')


        args = parser.parse_args()

        params = {}
        ret = {}

        for key, value in args.iteritems():
            if value is not None:
                params[key] = value

        if args["jobName"] is None or len(args["jobName"].strip()) == 0:
            ret["error"] = "job name cannot be empty"
        elif args["vcName"] is None or len(args["vcName"].strip()) == 0:
            ret["error"] = "vc name cannot be empty"
        elif args["resourcegpu"] is None or len(args["resourcegpu"].strip()) == 0:
            ret["error"] = "Number of GPU cannot be empty"
        elif args["gpuType"] is None or len(args["gpuType"].strip()) == 0:
            ret["error"] = "GPU Type cannot be empty"
        elif args["dataPath"] is None or len(args["dataPath"].strip()) == 0:
            ret["error"] = "datapath cannot be empty"
        elif args["image"] is None or len(args["image"].strip()) == 0:
            ret["error"] = "docker image cannot be empty"
        elif args["jobType"] is None or len(args["jobType"].strip()) == 0:
            ret["error"] = "jobType cannot be empty"
        else:
            params["jobName"] = args["jobName"]
            params["vcName"] = args["vcName"]
            params["resourcegpu"] = args["resourcegpu"]
            params["gpuType"] = args["gpuType"]
            params["workPath"] = args["workPath"]
            params["dataPath"] = args["dataPath"]
            params["image"] = args["image"]
            params["cmd"] = args["cmd"]
            params["jobType"] = args["jobType"]
            params["preemptionAllowed"] = args["preemptionAllowed"]

            params["jobtrainingtype"] = args["jobtrainingtype"]

            if args["jobtrainingtype"] == "PSDistJob":
                params["numps"] = 1
                params["numpsworker"] = args["numpsworker"]

            if args["jobtrainingtype"] == "MPIDistJob":
                params["nummpiworker"] = args["nummpiworker"]

            if args["jobPath"] is not None and len(args["jobPath"].strip()) > 0:
                params["jobPath"] = args["jobPath"]

            if args["logDir"] is not None and len(args["logDir"].strip()) > 0:
                params["logDir"] = args["logDir"]

            if args["userId"] is not None and len(args["userId"].strip()) > 0:
                params["userId"] = args["userId"]
            else:
                # !! note: if userId is not provided, the container will be running as root. There shouldn't be any security concern since all the resources in docker container should be user's own property. Also, we plan to allow user to choose "run as root".
                params["userId"] = "0"

            if args["nodeSelector"] is not None and len(args["nodeSelector"].strip()) > 0:
                params["nodeSelector"] = {args["nodeSelector"]:"active"}


            if args["interactivePort"] is not None and len(args["interactivePort"].strip()) > 0:
                params["interactivePort"] = args["interactivePort"]

            if args["containerUserId"] is not None and len(args["containerUserId"].strip()) > 0:
                params["containerUserId"] = args["containerUserId"]
            else:
                params["containerUserId"] = params["userId"]

            if args["userName"] is not None and len(args["userName"].strip()) > 0:
                params["userName"] = args["userName"]
            else:
                params["userName"] = "default"
            if args["familyToken"] is not None and len(args["familyToken"].strip()) > 0:
                params["familyToken"] = args["familyToken"]
            else:
                params["familyToken"] = str(uuid.uuid4())
            if args["isParent"] is not None and len(args["isParent"].strip()) > 0:
                params["isParent"] = args["isParent"]
            else:
                params["isParent"] = "1"
            params["mountpoints"] = []
            addcmd = ""
            if "mounthomefolder" in config and istrue(config["mounthomefolder"]) and "storage-mount-path" in config:
                alias = getAlias(params["userName"])
                params["mountpoints"].append({"name":"homeholder","containerPath":os.path.join("/home", alias),"hostPath":os.path.join(config["storage-mount-path"], "work", alias)})
            if "mountpoints" in config and "storage-mount-path" in config:
                # see link_fileshares in deploy.py
                for k, v in config["mountpoints"].iteritems():
                    if "mountpoints" in v:
                        for basename in tolist(v["mountpoints"]):
                            if basename!="" and basename not in config["default-storage-folders"] and basename in config["deploymounts"]:
                                hostBase = os.path.join(config["storage-mount-path"], basename[1:]) if os.path.isabs(basename) else os.path.join(config["storage-mount-path"], basename)
                                basealias = basename[1:] if os.path.isabs(basename) else basename
                                containerBase = os.path.join("/", basename)
                                alias = getAlias(params["userName"])
                                shares = [alias]
                                if "publicshare" in v:
                                    if "all" in v["publicshare"]:
                                        shares += (tolist(v["publicshare"]["all"]))
                                    if basename in v["publicshare"]:
                                        shares += (tolist(v["publicshare"][basename]))
                                for oneshare in shares:
                                    hostPath = os.path.join(hostBase, oneshare)
                                    containerPath = os.path.join(containerBase, oneshare)
                                    if v["type"]=="emptyDir":
                                        params["mountpoints"].append({"name":basealias+"-"+oneshare,
                                                                        "containerPath": containerPath,
                                                                        "hostPath": "/emptydir",
                                                                        "emptydir": "yes" })
                                    else:
                                        params["mountpoints"].append({"name":basealias+"-"+oneshare,
                                                                        "containerPath": containerPath,
                                                                        "hostPath": hostPath })
                                    if False and "type" in v and v["type"]!="local" and v["type"]!="localHDD":
                                        # This part is disabled, see if False above
                                        # This is a shared drive, we can try to create it, and enable the write permission
                                        if not os.path.exists(hostPath):
                                            cmd = "sudo mkdir -m 0777 -p %s; " % hostPath
                                            os.system( cmd )
                                            logger.info( cmd )
                                            if oneshare==alias:
                                                cmd = "sudo chown %s:%s %s; " % (params["containerUserId"], "500000513", hostPath )
                                                os.system(cmd )
                                                logger.info( cmd )
                                    addcmd += "chmod 0777 %s ; " % containerPath
                                    if oneshare==alias:
                                        addcmd += "chown %s:%s %s ; " % ( params["userId"], "500000513", containerPath )
            if verbose and len(params["mountpoints"]) > 0:
                logger.info("Mount path for job %s" % params )
                for mounts in params["mountpoints"]:
                    logger.info( "Share %s, mount %s at %s" % (mounts["name"], mounts["hostPath"], mounts["containerPath"]) )
            if len(addcmd) > 0:
                params["cmd"] = addcmd + params["cmd"]
            output = JobRestAPIUtils.SubmitJob(json.dumps(params))

            if "jobId" in output:
                ret["jobId"] = output["jobId"]
            else:
                if "error" in output:
                    ret["error"] = "Cannot create job!" + output["error"]
                else:
                    ret["error"] = "Cannot create job!"

        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"
        return resp
##
## Actually setup the Api resource routing here
##
api.add_resource(SubmitJob, '/SubmitJob')



class PostJob(Resource):
    def post(self):
        params = request.get_json(force=True)
        monitor = yaml.safe_dump(params, default_flow_style=False)
        logger.info("Post Job" )
        logger.info(monitor )
        ret = {}
        if True:
            output = JobRestAPIUtils.SubmitJob(json.dumps(params))

            if "jobId" in output:
                ret["jobId"] = output["jobId"]
            else:
                if "error" in output:
                    ret["error"] = "Cannot create job!" + output["error"]
                else:
                    ret["error"] = "Cannot create job!"
            logger.info("Submit job through restapi, output is %s, ret is %s" %(output, ret) )
        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"
        return resp
##
## Actually setup the Api resource routing here
##
api.add_resource(PostJob, '/PostJob')



# shows a list of all todos, and lets you POST to add new tasks
class ListJobs(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('userName')
        parser.add_argument('num')
        parser.add_argument('vcName')
        parser.add_argument('jobOwner')
        args = parser.parse_args()
        num = None
        if args["num"] is not None:
            try:
                num = int(args["num"])
            except:
                pass
        jobs = JobRestAPIUtils.GetJobList(args["userName"], args["vcName"], args["jobOwner"], num)

        jobList = []
        queuedJobs = []
        runningJobs = []
        finishedJobs = []
        visualizationJobs = []
        for job in jobs:
            job.pop("jobDescriptionPath",None)
            job.pop("jobDescription",None)

            job["jobParams"] = json.loads(base64.b64decode(job["jobParams"]))

            if "endpoints" in job and job["endpoints"] is not None  and (job["endpoints"].strip()) > 0:
                job["endpoints"] = json.loads(job["endpoints"])

            if "jobStatusDetail" in job and job["jobStatusDetail"] is not None  and (job["jobStatusDetail"].strip()) > 0:
                try:
                    s = job["jobStatusDetail"]
                    s = base64.b64decode(s)
                    s = json.loads(s)
                    job["jobStatusDetail"] = s
                except Exception as e:
                    job["jobStatusDetail"] = s
                    pass

            if job["jobStatus"] == "running":
                if job["jobType"] == "training":
                    runningJobs.append(job)
                elif job["jobType"] == "visualization":
                    visualizationJobs.append(job)
            elif job["jobStatus"] == "queued" or job["jobStatus"] == "scheduling" or job["jobStatus"] == "unapproved":
                queuedJobs.append(job)
            else:
                finishedJobs.append(job)

        ret = {}
        ret["queuedJobs"] = queuedJobs
        ret["runningJobs"] = runningJobs
        ret["finishedJobs"] = finishedJobs
        ret["visualizationJobs"] = visualizationJobs
        ret["meta"] = {"queuedJobs": len(queuedJobs),"runningJobs": len(runningJobs),"finishedJobs": len(finishedJobs),"visualizationJobs": len(visualizationJobs)}
        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp
##
## Actually setup the Api resource routing here
##
api.add_resource(ListJobs, '/ListJobs')



class KillJob(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('jobId')
        parser.add_argument('userName')
        args = parser.parse_args()
        jobId = args["jobId"]
        userName = args["userName"]
        result = JobRestAPIUtils.KillJob(userName, jobId)
        ret = {}
        if result:
            ret["result"] = "Success, the job is scheduled to be terminated."
        else:
            ret["result"] = "Cannot Kill the job. Job ID:" + jobId

        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp
##
## Actually setup the Api resource routing here
##
api.add_resource(KillJob, '/KillJob')



class PauseJob(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('jobId')
        parser.add_argument('userName')
        args = parser.parse_args()
        jobId = args["jobId"]
        userName = args["userName"]
        result = JobRestAPIUtils.PauseJob(userName, jobId)
        ret = {}
        if result:
            ret["result"] = "Success, the job is scheduled to be paused."
        else:
            ret["result"] = "Cannot pause the job. Job ID:" + jobId

        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp
##
## Actually setup the Api resource routing here
##
api.add_resource(PauseJob, '/PauseJob')



class ResumeJob(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('jobId')
        parser.add_argument('userName')
        args = parser.parse_args()
        jobId = args["jobId"]
        userName = args["userName"]
        result = JobRestAPIUtils.ResumeJob(userName, jobId)
        ret = {}
        if result:
            ret["result"] = "Success, the job is scheduled to be resumed."
        else:
            ret["result"] = "Cannot resume the job. Job ID:" + jobId

        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp
##
## Actually setup the Api resource routing here
##
api.add_resource(ResumeJob, '/ResumeJob')



class CloneJob(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('jobId')
        parser.add_argument('userName')
        args = parser.parse_args()
        jobId = args["jobId"]
        userName = args["userName"]
        result = JobRestAPIUtils.CloneJob(userName, jobId)
        ret = {}
        if result:
            ret["result"] = "Success, the job is scheduled to be cloned."
        else:
            ret["result"] = "Cannot clone the job. Job ID:" + jobId

        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp
##
## Actually setup the Api resource routing here
##
api.add_resource(CloneJob, '/CloneJob')



class ApproveJob(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('jobId')
        parser.add_argument('userName')
        args = parser.parse_args()
        jobId = args["jobId"]
        userName = args["userName"]
        result = JobRestAPIUtils.ApproveJob(userName, jobId)
        ret = {}
        if result:
            ret["result"] = "Success, the job has been approved."
        else:
            ret["result"] = "Cannot approve the job. Job ID:" + jobId

        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp
##
## Actually setup the Api resource routing here
##
api.add_resource(ApproveJob, '/ApproveJob')



class GetCommands(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('jobId')
        parser.add_argument('userName')
        args = parser.parse_args()
        jobId = args["jobId"]
        userName = args["userName"]
        commands = JobRestAPIUtils.GetCommands(userName, jobId)
        resp = jsonify(commands)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp
##
## Actually setup the Api resource routing here
##
api.add_resource(GetCommands, '/GetCommands')



class GetJobDetail(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('jobId')
        parser.add_argument('userName')
        args = parser.parse_args()
        jobId = args["jobId"]
        userName = args["userName"]
        job = JobRestAPIUtils.GetJobDetail(userName, jobId)
        job["jobParams"] = json.loads(base64.b64decode(job["jobParams"]))
        if "endpoints" in job and job["endpoints"] is not None and (job["endpoints"].strip()) > 0:
            job["endpoints"] = json.loads(job["endpoints"])
        if "jobStatusDetail" in job and job["jobStatusDetail"] is not None  and (job["jobStatusDetail"].strip()) > 0:
            try:
                job["jobStatusDetail"] = Json.loads(base64.b64decode(job["jobStatusDetail"]))
            except Exception as e:
                pass
        if "jobMeta" in job:
            job.pop("jobMeta",None)
        resp = jsonify(job)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp
##
## Actually setup the Api resource routing here
##
api.add_resource(GetJobDetail, '/GetJobDetail')


class GetJobStatus(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('jobId')
        args = parser.parse_args()
        jobId = args["jobId"]
        job = JobRestAPIUtils.GetJobStatus(jobId)
        resp = jsonify(job)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp
##
## Actually setup the Api resource routing here
##
api.add_resource(GetJobStatus, '/GetJobStatus')


class GetClusterStatus(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('userName')
        args = parser.parse_args()
        userName = args["userName"]
        cluster_status, last_updated_time = JobRestAPIUtils.GetClusterStatus()
        cluster_status["last_updated_time"] = last_updated_time
        resp = jsonify(cluster_status)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp
##
## Actually setup the Api resource routing here
##
api.add_resource(GetClusterStatus, '/GetClusterStatus')


class AddCommand(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('jobId')
        parser.add_argument('command')
        parser.add_argument('userName')
        args = parser.parse_args()
        userName = args["userName"]
        jobId = args["jobId"]
        command = args["command"]
        ret = {}
        if command is None or len(command) == 0:
            ret["result"] = "Cannot Run empty Command. Job ID:" + jobId
        else:
            result = JobRestAPIUtils.AddCommand(userName, jobId, command)
            if result:
                ret["result"] = "Success, the command is scheduled to be run."
            else:
                ret["result"] = "Cannot Run the Command. Job ID:" + jobId

        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp
##
## Actually setup the Api resource routing here
##
api.add_resource(AddCommand, '/AddCommand')



class AddUser(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('userName')
        parser.add_argument('uid')
        parser.add_argument('gid')
        parser.add_argument('groups')
        args = parser.parse_args()

        ret = {}
        userName = args["userName"]
        if args["uid"] is None or len(args["uid"].strip()) == 0:
            uid = authorization.INVALID_ID
        else:
            uid = args["uid"]

        if args["gid"] is None or len(args["gid"].strip()) == 0:
            gid = authorization.INVALID_ID
        else:
            gid = args["gid"]

        if args["groups"] is None or len(args["groups"].strip()) == 0:
            groups = []
        else:
            groups = args["groups"]

        ret["status"] = JobRestAPIUtils.AddUser(userName, uid, gid, groups)
        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp
##
## Actually setup the Api resource routing here
##
api.add_resource(AddUser, '/AddUser')


class UpdateAce(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('userName')
        parser.add_argument('identityName')
        parser.add_argument('resourceType')
        parser.add_argument('resourceName')
        parser.add_argument('permissions')
        args = parser.parse_args()
        username = args["userName"]
        identityName = str(args["identityName"])
        resourceType = int(args["resourceType"])
        resourceName = str(args["resourceName"])
        permissions = int(args["permissions"])
        ret = {}
        ret["result"] = JobRestAPIUtils.UpdateAce(username, identityName, resourceType, resourceName, permissions)
        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp
##
## Actually setup the Api resource routing here
##
api.add_resource(UpdateAce, '/UpdateAce')


class DeleteAce(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('userName')
        parser.add_argument('identityName')
        parser.add_argument('resourceType')
        parser.add_argument('resourceName')
        args = parser.parse_args()
        username = args["userName"]
        identityName = str(args["identityName"])
        resourceType = int(args["resourceType"])
        resourceName = str(args["resourceName"])
        ret = {}
        ret["result"] = JobRestAPIUtils.DeleteAce(username, identityName, resourceType, resourceName)
        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp
##
## Actually setup the Api resource routing here
##
api.add_resource(DeleteAce, '/DeleteAce')


class IsClusterAdmin(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('userName')
        args = parser.parse_args()
        username = args["userName"]
        ret = {}
        ret["result"] = AuthorizationManager.IsClusterAdmin(username)
        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp
##
## Actually setup the Api resource routing here
##
api.add_resource(IsClusterAdmin, '/IsClusterAdmin')


class GetACL(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('userName')
        args = parser.parse_args()
        username = args["userName"]
        ret = {}
        ret["result"] = AuthorizationManager.GetAcl(username)
        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp
##
## Actually setup the Api resource routing here
##
api.add_resource(GetACL, '/GetACL')


class ListVCs(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('userName')
        args = parser.parse_args()
        userName = args["userName"]
        ret = {}
        ret["result"] = JobRestAPIUtils.ListVCs(userName)

        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp

##
## Actually setup the Api resource routing here
##
api.add_resource(ListVCs, '/ListVCs')


class GetVC(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('userName')
        parser.add_argument('vcName')
        args = parser.parse_args()
        userName = args["userName"]
        vcName = args["vcName"]
        ret = JobRestAPIUtils.GetVC(userName, vcName)

        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp

##
## Actually setup the Api resource routing here
##
api.add_resource(GetVC, '/GetVC')


class AddVC(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('vcName')
        parser.add_argument('quota')
        parser.add_argument('metadata')
        parser.add_argument('userName')
        args = parser.parse_args()
        vcName = args["vcName"]
        quota = args["quota"]
        metadata = args["metadata"]
        userName = args["userName"]
        ret = {}
        ret["result"] = JobRestAPIUtils.AddVC(userName, vcName, quota, metadata)

        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp
##
## Actually setup the Api resource routing here
##
api.add_resource(AddVC, '/AddVC')


class DeleteVC(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('vcName')
        parser.add_argument('userName')
        args = parser.parse_args()
        vcName = args["vcName"]
        userName = args["userName"]
        ret = {}
        ret["result"] = JobRestAPIUtils.DeleteVC(userName, vcName)
        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp
##
## Actually setup the Api resource routing here
##
api.add_resource(DeleteVC, '/DeleteVC')


class UpdateVC(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('vcName')
        parser.add_argument('quota')
        parser.add_argument('metadata')
        parser.add_argument('userName')
        args = parser.parse_args()
        vcName = args["vcName"]
        quota = args["quota"]
        metadata = args["metadata"]
        userName = args["userName"]
        ret = {}
        ret["result"] = JobRestAPIUtils.UpdateVC(userName, vcName, quota, metadata)

        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp
##
## Actually setup the Api resource routing here
##
api.add_resource(UpdateVC, '/UpdateVC')


class ListStorages(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('vcName')
        parser.add_argument('userName')
        args = parser.parse_args()
        vcName = args["vcName"]
        userName = args["userName"]
        ret = {}
        ret["result"] = JobRestAPIUtils.ListStorages(userName, vcName)
        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp
##
## Actually setup the Api resource routing here
##
api.add_resource(ListStorages, '/ListStorages')


class AddStorage(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('vcName')
        parser.add_argument('storageType')
        parser.add_argument('url')
        parser.add_argument('metadata')

        parser.add_argument('defaultMountPath')
        parser.add_argument('userName')
        args = parser.parse_args()
        vcName = args["vcName"]
        storageType = args["storageType"]
        url = args["url"]

        metadata = args["metadata"]
        defaultMountPath = args["defaultMountPath"]
        userName = args["userName"]
        ret = {}
        ret["result"] = JobRestAPIUtils.AddStorage(userName, vcName, url, storageType, metadata, defaultMountPath)
        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp
##
## Actually setup the Api resource routing here
##
api.add_resource(AddStorage, '/AddStorage')


class DeleteStorage(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('vcName')
        parser.add_argument('userName')
        parser.add_argument('url')
        args = parser.parse_args()
        vcName = args["vcName"]
        userName = args["userName"]
        url = args["url"]
        ret = {}
        ret["result"] = JobRestAPIUtils.DeleteStorage(userName, vcName, url)
        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp
##
## Actually setup the Api resource routing here
##
api.add_resource(DeleteStorage, '/DeleteStorage')


class UpdateStorage(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('vcName')
        parser.add_argument('storageType')
        parser.add_argument('url')
        parser.add_argument('metadata')

        parser.add_argument('defaultMountPath')
        parser.add_argument('userName')
        args = parser.parse_args()
        vcName = args["vcName"]
        storageType = args["storageType"]
        url = args["url"]
        metadata = args["metadata"]
        defaultMountPath = args["defaultMountPath"]
        userName = args["userName"]
        ret = {}
        ret["result"] = JobRestAPIUtils.UpdateStorage(userName, vcName, url, storageType, metadata, defaultMountPath)

        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp
##
## Actually setup the Api resource routing here
##
api.add_resource(UpdateStorage, '/UpdateStorage')

def getAlias(username):
    if "@" in username:
        return username.split("@")[0].strip()
    if "/" in username:
        return username.split("/")[1].strip()
    return username


class Endpoint(Resource):
    def get(self):
        '''return job["endpoints"]: curl -X GET /endpoints?jobId=...&userName=...'''
        parser = reqparse.RequestParser()
        parser.add_argument('jobId')
        parser.add_argument('userName')
        args = parser.parse_args()
        jobId = args["jobId"]
        username = args["userName"]
        job = JobRestAPIUtils.GetJobDetail(username, jobId)

        rets = []
        try:
            endpoints = json.loads(job["endpoints"])
        except:
            endpoints = {}

        for [_, endpoint] in endpoints.items():
            ret = {
                "id": endpoint["id"],
                "name": endpoint["name"],
                "username": endpoint["username"],
                "status": endpoint["status"],
                "hostNetwork": endpoint["hostNetwork"],
                "podName": endpoint["podName"],
                "domain": config["domain"],
            }
            if "podPort" in endpoint:
                ret["podPort"] = endpoint["podPort"]
            if endpoint["status"] == "running":
                if endpoint["hostNetwork"]:
                    port = int(endpoint["endpointDescription"]["spec"]["ports"][0]["port"])
                else:
                    port = int(endpoint["endpointDescription"]["spec"]["ports"][0]["nodePort"])
                ret["port"] = port
                if "nodeName" in endpoint:
                    ret["nodeName"] = endpoint["nodeName"]
            rets.append(ret)

        resp = jsonify(rets)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"
        return resp

    def post(self):
        '''set job["endpoints"]: curl -X POST -H "Content-Type: application/json" /endpoints --data "{'jobId': ..., 'endpoints': ['ssh', 'ipython'] }"'''
        params = request.get_json(silent=True)
        job_id = params["jobId"]
        requested_endpoints = params["endpoints"]

        # get the job
        job = JobRestAPIUtils.get_job(job_id)
        job_params = json.loads(base64.b64decode(job["jobParams"]))
        job_type = job_params["jobtrainingtype"]

        # get pods
        pod_names = []
        if job_type == "RegularJob":
            pod_names.append(job_id)
        else:
            nums = {"ps": int(job_params["numps"]), "worker": int(job_params["numpsworker"])}
            for role in ["ps", "worker"]:
                for i in range(nums[role]):
                    pod_names.append(job_id + "-" + role + str(i))

        interactive_ports = []
        # endpoints should be ["ssh", "ipython", "tensorboard", {"name": "port name", "podPort": "port on pod in 40000-49999"}]
        for interactive_port in [ elem for elem in requested_endpoints if elem not in ["ssh", "ipython", "tensorboard"] ]:
            if any(required_field not in interactive_port for required_field in ["name", "podPort"]):
                # if ["name", "port"] not in interactive_port:
                return ("Bad request, interactive port should have \"name\" and \"podPort\"]: %s" % requested_endpoints), 400
            if int(interactive_port["podPort"]) < 40000 or int(interactive_port["podPort"]) > 49999:
                return ("Bad request, interactive podPort should in range 40000-49999: %s" % requested_endpoints), 400
            if len(interactive_port["name"]) > 16:
                return ("Bad request, interactive port name length shoule be less than 16: %s" % requested_endpoints), 400
            interactive_ports.append(interactive_port)

        # HostNetwork
        if "hostNetwork" in job_params and job_params["hostNetwork"] == True:
            host_network = True
        else:
            host_network = False

        # username
        username = getAlias(job["userName"])

        endpoints = {}

        def endpoint_exist(endpoint_id):
            try:
                curr_endpoints = json.loads(job["endpoints"])
            except:
                curr_endpoints = {}

            if endpoint_id in curr_endpoints:
                return True
            return False

        if "ssh" in requested_endpoints:
            # setup ssh for each pod
            for pod_name in pod_names:
                endpoint_id = "e-" + pod_name + "-ssh"

                if endpoint_exist(endpoint_id=endpoint_id):
                    print("Endpoint {} exists. Skip.".format(endpoint_id))
                    continue
                print("Endpoint {} does not exist. Add.".format(endpoint_id))

                endpoint = {
                    "id": endpoint_id,
                    "jobId": job_id,
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

            endpoint_id = "e-" + job_id + "-ipython"

            if not endpoint_exist(endpoint_id=endpoint_id):
                print("Endpoint {} does not exist. Add.".format(endpoint_id))
                endpoint = {
                    "id": endpoint_id,
                    "jobId": job_id,
                    "podName": pod_name,
                    "username": username,
                    "name": "ipython",
                    "status": "pending",
                    "hostNetwork": host_network
                }
                endpoints[endpoint_id] = endpoint
            else:
                print("Endpoint {} exists. Skip.".format(endpoint_id))

        # Only open tensorboard on the master
        if 'tensorboard' in requested_endpoints:
            if job_type == "RegularJob":
                pod_name = pod_names[0]
            else:
                # For a distributed job, we set up jupyter on first worker node.
                # PS node does not have GPU access.
                # TODO: Simplify code logic after removing PS
                pod_name = pod_names[1]

            endpoint_id = "e-" + job_id + "-tensorboard"

            if not endpoint_exist(endpoint_id=endpoint_id):
                print("Endpoint {} does not exist. Add.".format(endpoint_id))
                endpoint = {
                    "id": endpoint_id,
                    "jobId": job_id,
                    "podName": pod_name,
                    "username": username,
                    "name": "tensorboard",
                    "status": "pending",
                    "hostNetwork": host_network
                }
                endpoints[endpoint_id] = endpoint
            else:
                print("Endpoint {} exists. Skip.".format(endpoint_id))

        # interactive port
        for interactive_port in interactive_ports:
            if job_type == "RegularJob":
                pod_name = pod_names[0]
            else:
                # For a distributed job, we set up jupyter on first worker node.
                # PS node does not have GPU access.
                # TODO: Simplify code logic after removing PS
                pod_name = pod_names[1]

            endpoint_id = "e-" + job_id + "-" + interactive_port["name"]
            if not endpoint_exist(endpoint_id=endpoint_id):
                print("Endpoint {} does not exist. Add.".format(endpoint_id))
                endpoint = {
                    "id": endpoint_id,
                    "jobId": job_id,
                    "podName": pod_name,
                    "username": username,
                    "name": interactive_port["name"],
                    "podPort": interactive_port["podPort"],
                    "status": "pending",
                    "hostNetwork": host_network
                }
                endpoints[endpoint_id] = endpoint
            else:
                print("Endpoint {} exists. Skip.".format(endpoint_id))

        data_handler = DataHandler()
        for [_, endpoint] in endpoints.items():
            data_handler.UpdateEndpoint(endpoint)

        resp = jsonify(endpoints)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"
        return resp


##
## Actually setup the Endpoint resource routing here
##
api.add_resource(Endpoint, '/endpoints')

if __name__ == '__main__':
    app.run(debug=False,host="0.0.0.0",threaded=True)

