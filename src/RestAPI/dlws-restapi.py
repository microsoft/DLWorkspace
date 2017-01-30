import sys
import json
import os

from flask import Flask
from flask_restful import reqparse, abort, Api, Resource
from flask import request, jsonify


sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../utils"))
from JobUtils import SubmitRegularJob, SubmitDistJob, GetJobList, GetJobStatus, DeleteJob, GetTensorboard, GetServiceAddress, GetLog, GetJob


app = Flask(__name__)
api = Api(app)



parser = reqparse.RequestParser()


class SubmitJob(Resource):
    def get(self):
        parser.add_argument('jobname')
        parser.add_argument('resourcegpu')
        parser.add_argument('workpath')
        parser.add_argument('datapath')
        parser.add_argument('jobpath')
        parser.add_argument('image')
        parser.add_argument('cmd')
        parser.add_argument('logdir')
        parser.add_argument('interactiveport')
        parser.add_argument('username')
        

        args = parser.parse_args()

        params = {}
        ret = {}

        for key, value in args.iteritems():
            if value is not None:
                params[key] = value

        if args["jobname"] is None or len(args["jobname"].strip()) == 0:
            ret["error"] = "job name cannot be empty"
        elif args["resourcegpu"] is None or len(args["resourcegpu"].strip()) == 0:
            ret["error"] = "Number of GPU cannot be empty"
        elif args["workpath"] is None or len(args["workpath"].strip()) == 0:
            ret["error"] = "workpath cannot be empty"            
        elif args["datapath"] is None or len(args["datapath"].strip()) == 0:
            ret["error"] = "datapath cannot be empty"            
        elif args["image"] is None or len(args["image"].strip()) == 0:
            ret["error"] = "docker image cannot be empty"            
        else:
            params["job-name"] = args["jobname"]
            params["work-path"] = args["workpath"]
            params["data-path"] = args["datapath"]
            params["data-path"] = args["datapath"]
            params["image"] = args["image"]
            params["cmd"] = args["cmd"]


            if args["jobpath"] is not None and len(args["jobpath"].strip()) > 0:
                params["job-path"] = args["jobpath"]

            if args["logdir"] is not None and len(args["logdir"].strip()) > 0:
                params["logdir"] = args["logdir"]

            if args["interactiveport"] is not None and len(args["interactiveport"].strip()) > 0:
                params["interactive-port"] = args["jobpath"]

            if args["username"] is not None and len(args["username"].strip()) > 0:
                params["username-port"] = args["username"]
            else:
                params["username-port"] = "default"


            output = SubmitRegularJob(json.dumps(params))
            
            if "id" in output:
                ret["jobId"] = output["id"]
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


# shows a list of all todos, and lets you POST to add new tasks
class ListJobs(Resource):
    def get(self):
        jobs = GetJobList()
        jobList = []
        queuedJobs = []
        runningJobs = []
        finishedJobs = []
        interactiveJobs = []
        visualizationJobs = []
        for job in jobs:
            #svcs = GetServiceAddress(job["job_id"])
            #job["services_ip"] = []
            #if len(svcs)>0:
            #    for (port,hostIP,nodeport) in svcs:
            #        job["services_ip"].append("http://"+hostIP+":"+nodeport)


            #(port,hostIP,nodeport) = GetTensorboard(job["job_id"])
            #if port is not None and hostIP is not None and nodeport is not None:
            #    job["tensorboard"] = "http://"+hostIP+":"+nodeport


            #status, status_detail = GetJobStatus(job["job_id"])
            #job["status"] = status
	    #job["status_detail"] = status_detail
	    job.pop("job_meta",None)
            runningJobs.append(job)
        ret = {}
        ret["queuedJobs"] = jobList
        ret["runningJobs"] = runningJobs
        ret["finishedJobs"] = finishedJobs
        ret["interactiveJobs"] = interactiveJobs
        ret["visualizationJobs"] = visualizationJobs
        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"


        return resp

    def post(self):
        jobs = GetJobList()
        jobList = []
        for job in jobs:
            jobobj = []
            jobobj.append("<a href='http://onenet39/jobs/jobdetail.html?jobId="+job["job_id"]+"' title='click for detail'>"+job["job_id"]+"</a>")
            jobobj.append(job["job_name"])
            jobobj.append(job["user_id"])

            svcs = GetServiceAddress(job["job_id"])
            if len(svcs)>0:
                for (port,hostIP,nodeport) in svcs:
                    jobobj.append("<a href='http://"+hostIP+":"+nodeport+"' target='_blank'> "+port+"->"+hostIP+":"+nodeport+" </a> <br/>")
            else:
                jobobj.append("N/A")
            

            (port,hostIP,nodeport) = GetTensorboard(job["job_id"])
            if port is not None and hostIP is not None and nodeport is not None:
                jobobj.append("<a href='http://"+hostIP+":"+nodeport+"' target='_blank'> "+hostIP+":"+nodeport+" </a>")
            else:
                jobobj.append("N/A")
            

            status, status_detail = GetJobStatus(job["job_id"])
            jobobj.append("<div title='"+status_detail+"'>"+status+"</div>")
            jobobj.append(str(job["time"]))
            jobobj.append("<a href='http://onenet39/jobs/delete_job.php?jobId="+job["job_id"]+"' > terminate job </a>")
            jobobj.append("<a href='http://onenet39/jobs/joblog.php?jobId="+job["job_id"]+"' target='_blank'> log </a>")
            jobList.append(jobobj)
        ret = {}
        ret["data"] = jobList
        return json.dumps(ret),200, {"Access-Control-Allow-Origin":"*"}

##
## Actually setup the Api resource routing here
##
api.add_resource(ListJobs, '/ListJobs')


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



class GetJobDetail(Resource):
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
api.add_resource(GetJobDetail, '/GetJobDetail')



if __name__ == '__main__':
    app.run(debug=True,host="0.0.0.0")
