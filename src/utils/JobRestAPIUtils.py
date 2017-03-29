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


def LoadJobParams(jobParamsJsonStr):
	return json.loads(jobParamsJsonStr)


def SubmitJob(jobParamsJsonStr):
	ret = {}

	jobParams = LoadJobParams(jobParamsJsonStr)
	print jobParamsJsonStr

	dataHandler = DataHandler()

	if "jobId" not in jobParams or jobParams["jobId"] == "":
		#jobParams["jobId"] = jobParams["jobName"] + "-" + str(uuid.uuid4()) 
		#jobParams["jobId"] = jobParams["jobName"] + "-" + str(time.time())
		jobParams["jobId"] = str(uuid.uuid4()) 
	#jobParams["jobId"] = jobParams["jobId"].replace("_","-").replace(".","-")


	if "cmd" not in jobParams:
		jobParams["cmd"] = ""

	if "jobPath" in jobParams and len(jobParams["jobPath"].strip()) > 0: 
		jobPath = jobParams["jobPath"]
	else:
		jobPath = time.strftime("%y%m%d")+"/"+jobParams["jobId"]
		jobParams["jobPath"] = jobPath

	if "workPath" not in jobParams or len(jobParams["workPath"].strip()) == 0: 
	   ret["error"] = "ERROR: work-path cannot be empty"

	if "dataPath" not in jobParams or len(jobParams["dataPath"].strip()) == 0: 
		ret["error"] = "ERROR: data-path cannot be empty"


	if "logDir" in jobParams and len(jobParams["logDir"].strip()) > 0:
		tensorboardParams = jobParams.copy()

		tensorboardParams["jobId"] = str(uuid.uuid4()) 
		tensorboardParams["jobName"] = "tensorboard-"+jobParams["jobName"]
		tensorboardParams["jobPath"] = jobPath
		tensorboardParams["jobType"] = "visualization"
		tensorboardParams["cmd"] = "tensorboard --logdir " + jobParams["logDir"] + " --host 0.0.0.0"
		tensorboardParams["image"] = jobParams["image"]
		tensorboardParams["resourcegpu"] = "0"

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



def GetJobList(userName):
	dataHandler = DataHandler()
	jobs =  dataHandler.GetJobList(userName)
	for job in jobs:
		job.pop('jobMeta', None)
	dataHandler.Close()
	return jobs



def KillJob(jobId):
	dataHandler = DataHandler()
	ret = False
	jobs =  dataHandler.GetJob(jobId)
	if len(jobs) == 1:
		ret = dataHandler.KillJob(jobId)
	dataHandler.Close()
	return ret


def GetJobDetail(jobId):
	job = None
	dataHandler = DataHandler()
	jobs =  dataHandler.GetJob(jobId)
	if len(jobs) == 1:
		job = jobs[0]
		job["log"] = ""
		#jobParams = json.loads(base64.b64decode(job["jobMeta"]))
		#jobPath,workPath,dataPath = GetStoragePath(jobParams["jobPath"],jobParams["workPath"],jobParams["dataPath"])
		#localJobPath = os.path.join(config["storage-mount-path"],jobPath)
		#logPath = os.path.join(localJobPath,"joblog.txt")
		#print logPath
		#if os.path.isfile(logPath):
		#	with open(logPath, 'r') as f:
		#		log = f.read()
		#		job["log"] = log
		#	f.close()
		if "jobDescription" in job:
			job.pop("jobDescription",None)
		try:
			log = dataHandler.GetJobTextField(jobId,"jobLog")
			if log is not None:
				job["log"] = log
		except:
			job["log"] = "fail-to-get-logs"
	dataHandler.Close()
	return job



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
