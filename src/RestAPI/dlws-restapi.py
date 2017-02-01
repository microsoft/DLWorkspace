import sys
import json
import os

from flask import Flask
from flask_restful import reqparse, abort, Api, Resource
from flask import request, jsonify


sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../utils"))
#from JobRestAPIUtils import SubmitDistJob, GetJobList, GetJobStatus, DeleteJob, GetTensorboard, GetServiceAddress, GetLog, GetJob
import JobRestAPIUtils

app = Flask(__name__)
api = Api(app)



parser = reqparse.RequestParser()


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
        parser.add_argument('interactiveport')
        parser.add_argument('userName')
        parser.add_argument('jobType')
        

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
        elif args["workPath"] is None or len(args["workPath"].strip()) == 0:
            ret["error"] = "workpath cannot be empty"            
        elif args["dataPath"] is None or len(args["dataPath"].strip()) == 0:
            ret["error"] = "datapath cannot be empty"            
        elif args["image"] is None or len(args["image"].strip()) == 0:
            ret["error"] = "docker image cannot be empty"            
        elif args["jobType"] is None or len(args["jobType"].strip()) == 0:
            ret["error"] = "jobType cannot be empty"        
        else:
            params["jobName"] = args["jobName"]
            params["workPath"] = args["workPath"]
            params["dataPath"] = args["dataPath"]
            params["image"] = args["image"]
            params["cmd"] = args["cmd"]
            params["jobType"] = args["jobType"]


            if args["jobPath"] is not None and len(args["jobPath"].strip()) > 0:
                params["jobPath"] = args["jobPath"]

            if args["logDir"] is not None and len(args["logDir"].strip()) > 0:
                params["logDir"] = args["logDir"]

            if args["interactiveport"] is not None and len(args["interactiveport"].strip()) > 0:
                params["interactive-port"] = args["jobpath"]

            if args["userName"] is not None and len(args["userName"].strip()) > 0:
                params["userName"] = args["userName"]
            else:
                params["userName"] = "default"


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




# shows a list of all todos, and lets you POST to add new tasks
class ListJobs(Resource):
    def get(self):
        parser.add_argument('userName')
        args = parser.parse_args()    
        if args["userName"] is not None and len(args["userName"].strip()) > 0:
            jobs = JobRestAPIUtils.GetJobList(args["userName"])
        else:
            jobs = []
        jobList = []
        queuedJobs = []
        runningJobs = []
        finishedJobs = []
        interactiveJobs = []
        visualizationJobs = []
        for job in jobs:
            job.pop("jobDescriptionPath",None)
            job.pop("jobDescription",None)


            if job["jobStatus"] == "running":
                if job["jobType"] == "training":
                    runningJobs.append(job)
                elif job["jobType"] == "interactive":
                    interactiveJobs.append(job)
                elif job["jobType"] == "visualization":
                    visualizationJobs.append(job)
            elif job["jobStatus"] == "queued" or job["jobStatus"] == "scheduling":
                queuedJobs.append(job)
            else:
                finishedJobs.append(job)


        ret = {}
        ret["queuedJobs"] = queuedJobs
        ret["runningJobs"] = runningJobs
        ret["finishedJobs"] = finishedJobs
        ret["interactiveJobs"] = interactiveJobs
        ret["visualizationJobs"] = visualizationJobs
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



class GetJobDetail(Resource):
    def get(self):
        parser.add_argument('jobId')
        args = parser.parse_args()    
        jobId = args["jobId"]
        log = JobRestAPIUtils.GetJobDetail(jobId)

        resp = jsonify(log)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp
##
## Actually setup the Api resource routing here
##
api.add_resource(GetJobDetail, '/GetJobDetail')





#################################################################################################################################



class KubeJob(Resource):
    def get(self):
        # ToDo: Return information on how to use the submission of training job for kubenete cluster 
        return {}

    def post(self):
        #parser.add_argument('cmd')
        #parser.add_argument('params')
        #args = parser.parse_args()
        data = dict(request.form)
        args = {}
        for key, value in data.iteritems():
            if len(value) > 0 and len(value[0]) > 0:
                args[key] = value[0]
        print args
        if args["apicmd"] == "CreateJob":
            output = SubmitRegularJob(json.dumps(args))
            return output, 201
        else:
            return {"msg":"No such command", "args":args}, 201

##
## Actually setup the Api resource routing here
##
api.add_resource(KubeJob, '/KubeJob')


class KubeDistJob(Resource):
    def get(self):
        # ToDo: Return information on how to use the submission of a distributed training job for kubenete cluster 
        return {}

    def post(self):
        #parser.add_argument('cmd')
        #parser.add_argument('params')
        #args = parser.parse_args()
        data = dict(request.form)
        args = {}
        for key, value in data.iteritems():
            if len(value) > 0 and len(value[0]) > 0:
                args[key] = value[0]
        print args
        if args["apicmd"] == "CreateJob":
            output = SubmitDistJob(json.dumps(args))
            return output, 201
        else:
            return {"msg":"No such command", "args":args}, 201

##
## Actually setup the Api resource routing here
##
api.add_resource(KubeDistJob, '/KubeDistJob')


@app.route("/ListJob")
def ListJob():
    resp = Response("")
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp




class DelJob(Resource):
    def post(self):
        jobId = request.form["jobId"]
        print jobId
        return DeleteJob(jobId)

##
## Actually setup the Api resource routing here
##
api.add_resource(DelJob, '/DeleteJob')

class GetJobLog(Resource):
    def post(self):
        jobId = request.form["jobId"]
        print jobId
        return GetLog(jobId).replace("\n","<br />")

##
## Actually setup the Api resource routing here
##
api.add_resource(GetJobLog, '/GetJobLog')



class GetJobDetail_old(Resource):
    def post(self):
        jobId = request.form["jobId"]
        jobs = GetJob(jobId)
        rows = []
        print jobId
        
        if len(jobs) == 1:
            job = jobs[0]
            rows.append(("1. Job ID",job["job_id"]))
            rows.append(("2. Job Name",job["job_name"]))
            rows.append(("3. User ID",job["user_id"]))

            svcs = GetServiceAddress(job["job_id"])
            if len(svcs)>0:
                svcaddress = ""
                for (port,hostIP,nodeport) in svcs:
                    svcaddress += "<a href='http://"+hostIP+":"+nodeport+"' target='_blank'> "+port+"->"+hostIP+":"+nodeport+" </a> <br/>"
                rows.append(("4. Service Address",svcaddress))
            else:
                rows.append(("4. Service Address","N/A"))
            

            (port,hostIP,nodeport) = GetTensorboard(job["job_id"])
            if port is not None and hostIP is not None and nodeport is not None:
                rows.append(("5. Visualization Tool Address","<a href='http://"+hostIP+":"+nodeport+"' target='_blank'> "+hostIP+":"+nodeport+" </a>"))
            else:
                rows.append(("5. Visualization Tool Address","N/A"))
            

            status, status_detail = GetJobStatus(job["job_id"])
            rows.append(("6. Job Status",status))
            rows.append(("7. Job Status",status_detail.replace("\n","<br/>").replace(" ","&nbsp;")))
   

        ret = {}
        ret["data"] = rows
        return json.dumps(ret)

##
## Actually setup the Api resource routing here
##
api.add_resource(GetJobDetail_old, '/GetJobDetail_old')



if __name__ == '__main__':
    app.run(debug=True,host="0.0.0.0")
