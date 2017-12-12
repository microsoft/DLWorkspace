import sys
import json
import os

from flask import Flask
from flask_restful import reqparse, abort, Api, Resource
from flask import request, jsonify
import base64
import yaml

import logging
from logging.config import dictConfig

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../utils"))
#from JobRestAPIUtils import SubmitDistJob, GetJobList, GetJobStatus, DeleteJob, GetTensorboard, GetServiceAddress, GetLog, GetJob
import JobRestAPIUtils
from config import config
from config import global_vars

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


parser = reqparse.RequestParser()

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
        parser.add_argument('jobName')
        parser.add_argument('resourcegpu')
        parser.add_argument('workPath')
        parser.add_argument('dataPath')
        parser.add_argument('jobPath')
        parser.add_argument('image')
        parser.add_argument('cmd')
        parser.add_argument('logDir')
        parser.add_argument('interactivePort')
        parser.add_argument('userName')
        parser.add_argument('userId')
        parser.add_argument('runningasroot')
        parser.add_argument('containerUserId')
        
        parser.add_argument('familyToken')
        parser.add_argument('isParent')
        parser.add_argument('jobType')
        

        parser.add_argument('jobtrainingtype')
        parser.add_argument('numps')
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
        elif args["resourcegpu"] is None or len(args["resourcegpu"].strip()) == 0:
            ret["error"] = "Number of GPU cannot be empty"        
        elif args["dataPath"] is None or len(args["dataPath"].strip()) == 0:
            ret["error"] = "datapath cannot be empty"            
        elif args["image"] is None or len(args["image"].strip()) == 0:
            ret["error"] = "docker image cannot be empty"            
        elif args["jobType"] is None or len(args["jobType"].strip()) == 0:
            ret["error"] = "jobType cannot be empty"        
        else:
            params["jobName"] = args["jobName"]
            params["resourcegpu"] = args["resourcegpu"]
            params["workPath"] = args["workPath"]
            params["dataPath"] = args["dataPath"]
            params["image"] = args["image"]
            params["cmd"] = args["cmd"]
            params["jobType"] = args["jobType"]

            params["jobtrainingtype"] = args["jobtrainingtype"]

            if args["jobtrainingtype"] == "PSDistJob":
                params["numps"] = args["numps"]
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
        parser.add_argument('userName')
        parser.add_argument('num')
        args = parser.parse_args()    
        num = None
        if args["num"] is not None:
            try:
                num = int(args["num"])
            except:
                pass
        if args["userName"] is not None and len(args["userName"].strip()) > 0:
            jobs = JobRestAPIUtils.GetJobList(args["userName"],num)
        else:
            jobs = []
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
                job["endpoints"] = json.loads(base64.b64decode(job["endpoints"]))

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
        parser.add_argument('jobId')
        args = parser.parse_args()    
        jobId = args["jobId"]
        result = JobRestAPIUtils.KillJob(jobId)
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



class ApproveJob(Resource):
    def get(self):
        parser.add_argument('jobId')
        args = parser.parse_args()    
        jobId = args["jobId"]
        result = JobRestAPIUtils.ApproveJob(jobId)
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
        parser.add_argument('jobId')
        args = parser.parse_args()    
        jobId = args["jobId"]
        commands = JobRestAPIUtils.GetCommands(jobId)        
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
        parser.add_argument('jobId')
        args = parser.parse_args()    
        jobId = args["jobId"]
        job = JobRestAPIUtils.GetJobDetail(jobId)
        job["jobParams"] = json.loads(base64.b64decode(job["jobParams"]))
        if "endpoints" in job and job["endpoints"] is not None and (job["endpoints"].strip()) > 0:
            job["endpoints"] = json.loads(base64.b64decode(job["endpoints"]))    
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



class GetClusterStatus(Resource):
    def get(self):
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
        parser.add_argument('jobId')
        parser.add_argument('command')
        args = parser.parse_args()    
        jobId = args["jobId"]
        command = args["command"]
        result = JobRestAPIUtils.AddCommand(jobId, command)
        ret = {}
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
        parser.add_argument('userName')
        parser.add_argument('userId')
        args = parser.parse_args()
        username = args["userName"]
        userId = args["userId"]
        ret = {}
        ret["status"] = JobRestAPIUtils.AddUser(username,userId)
        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp
##
## Actually setup the Api resource routing here
##
api.add_resource(AddUser, '/AddUser')




if __name__ == '__main__':
    app.run(debug=False,host="0.0.0.0",threaded=True)
