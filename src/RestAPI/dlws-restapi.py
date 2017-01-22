import sys
import json
import os

from flask import Flask
from flask_restful import reqparse, abort, Api, Resource
from flask import request


sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../utils"))
from JobUtils import SubmitRegularJob, SubmitDistJob, GetJobList, GetJobStatus, DeleteJob, GetTensorboard, GetServiceAddress, GetLog, GetJob


app = Flask(__name__)
api = Api(app)



parser = reqparse.RequestParser()


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


# shows a list of all todos, and lets you POST to add new tasks
class ListJobs(Resource):
    def get(self):
        return {}, 201

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
        return json.dumps(ret)

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
