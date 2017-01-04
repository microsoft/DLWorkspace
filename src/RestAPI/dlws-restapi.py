import sys
import json

from flask import Flask
from flask_restful import reqparse, abort, Api, Resource
from flask import request

sys.path.append("../utils")
from JobUtils import SubmitRegularJob, SubmitDistJob, GetJobList, GetJobStatus, DeleteJob, GetTensorboard, GetServiceAddress, GetLog


app = Flask(__name__)
api = Api(app)



parser = reqparse.RequestParser()


class KubeJob(Resource):
    def get(self):
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
            jobobj.append(job["job_id"])
            jobobj.append(job["job_name"])
            jobobj.append(job["user_id"])

            svclink = GetServiceAddress(job["job_id"])
            if svclink is not None:
                jobobj.append("<a href='"+svclink+"' target='_blank'> link </a>")
            else:
                jobobj.append("N/A")
            

            tblink = GetTensorboard(job["job_id"])
            if tblink is not None:
                jobobj.append("<a href='"+tblink+"' target='_blank'> link </a>")
            else:
                jobobj.append("N/A")
            

            status = GetJobStatus(job["job_id"])
            if len(status.strip()) == 0:
                status = job["status"] 
            jobobj.append(status)
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
        return GetLog(jobId)

##
## Actually setup the Api resource routing here
##
api.add_resource(GetJobLog, '/GetJobLog')



if __name__ == '__main__':
    app.run(debug=True)
