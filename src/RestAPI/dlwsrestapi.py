import sys
import json
import os

from flask import Flask
from flask_restful import reqparse, abort, Api, Resource
from flask import request, jsonify
import base64

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
		parser.add_argument('interactivePort')
		parser.add_argument('userName')
		parser.add_argument('userId')
		parser.add_argument('runningasroot')

		
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
		visualizationJobs = []
		for job in jobs:
			job.pop("jobDescriptionPath",None)
			job.pop("jobDescription",None)

			job["jobParams"] = json.loads(base64.b64decode(job["jobParams"]))

			if "endpoints" in job and job["endpoints"] is not None  and (job["endpoints"].strip()) > 0:
				job["endpoints"] = json.loads(base64.b64decode(job["endpoints"]))

			if job["jobStatus"] == "running":
				if job["jobType"] == "training":
					runningJobs.append(job)
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
		job = JobRestAPIUtils.GetJobDetail(jobId)
		job["jobParams"] = json.loads(base64.b64decode(job["jobParams"]))
		if "endpoints" in job and job["endpoints"] is not None and (job["endpoints"].strip()) > 0:
			job["endpoints"] = json.loads(base64.b64decode(job["endpoints"]))		
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
