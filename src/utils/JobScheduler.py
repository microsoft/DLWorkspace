import json
import os
import time
import argparse
import uuid
import subprocess
import sys
from jobs_tensorboard import GenTensorboardMeta
import datetime

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../storage"))

import yaml
from jinja2 import Environment, FileSystemLoader, Template
from config import config
from DataHandler import DataHandler
import base64

import re

import thread
import threading
import random

nvidiaDriverPath = config["nvidiaDriverPath"]

def mkdirsAsUser(path, userId):
	pdir = os.path.dirname(path)
	if not os.path.exists(pdir):
		mkdirsAsUser(pdir, userId)
	if not os.path.exists(path):
		os.system("mkdir %s ; chown -R %s %s" % (path,userId, path))


def GetStoragePath(jobpath, workpath, datapath):
    jobPath = "work/"+jobpath
    workPath = "work/"+workpath
    dataPath = "storage/"+datapath
    return jobPath,workPath,dataPath


def printlog(msg):
	print "%s - %s" % (datetime.datetime.utcnow().strftime("%x %X"),msg)

def LoadJobParams(jobParamsJsonStr):
	return json.loads(jobParamsJsonStr)

def kubectl_create(jobfile,EXEC=True):
	if EXEC:
		try:
			output = subprocess.check_output(["bash","-c", config["kubelet-path"] + " create -f " + jobfile])
		except Exception as e:
			print e
			output = ""
	else:
		output = "Job " + jobfile + " is not submitted to kubernetes cluster"
	return output

def kubectl_delete(jobfile,EXEC=True):
	if EXEC:
		try:
			cmd = "bash -c '" + config["kubelet-path"] + " delete -f " + jobfile + "'"
			print cmd
			output = os.system(cmd)
		except Exception as e:
			print e
			output = -1
	else:
		output = -1
	return output

def kubectl_exec(params):
	try:
		output = subprocess.check_output(["bash","-c", config["kubelet-path"] + " " + params])
	except Exception as e:
		print e
		output = ""
	return output


def kubectl_exec_output_to_file(params,file):
	os.system("%s %s 2>&1 | tee %s" % (config["kubelet-path"], params, file))

def cmd_exec(cmdStr):
	try:
		output = subprocess.check_output(["bash","-c", cmdStr])
	except Exception as e:
		print e
		output = ""
	return output





def Split(text,spliter):
	return [x for x in text.split(spliter) if len(x.strip()) > 0]

def GetServiceAddress(jobId):
	ret = []

	output = kubectl_exec(" describe svc -l run=" + jobId)
	svcs = output.split("\n\n\n")
	
	for svc in svcs:
		lines = [Split(x,"\t") for x in Split(svc,"\n")]
		containerPort = None
		hostPort = None
		selector = None
		hostIP = None

		for line in lines:
			if len(line) > 1:
				if line[0] == "Port:":
					containerPort = line[-1]
					if "/" in containerPort:
						containerPort = containerPort.split("/")[0]
				if line[0] == "NodePort:":
					hostPort = line[-1]
					if "/" in hostPort:
						hostPort = hostPort.split("/")[0]

				if line[0] == "Selector:" and line[1] != "<none>":
					selector = line[-1]

		if selector is not None:
			podInfo = GetPod(selector)
			if podInfo is not None and "items" in podInfo:
				for item in podInfo["items"]:
					if "status" in item and "hostIP" in item["status"]:
						hostIP = item["status"]["hostIP"]
		if containerPort is not None and hostIP is not None and hostPort is not None:
			svcMapping = {}
			svcMapping["containerPort"] = containerPort
			svcMapping["hostIP"] = hostIP
			svcMapping["hostPort"] = hostPort
			ret.append(svcMapping)
	return ret



def GetPod(selector):
	podInfo = {}
	try:
		output = kubectl_exec(" get pod -o yaml --show-all -l " + selector)
		podInfo = yaml.load(output)
	except Exception as e:
		print e
		podInfo = None
	return podInfo

def GetLog(jobId):
	# assume our job only one container per pod.

	selector = "run=" + jobId
	podInfo = GetPod(selector)
	logs = []

	if podInfo is not None and "items" in podInfo:
		for item in podInfo["items"]:
			log = {}
			if "metadata" in item and "name" in item["metadata"]:
				log["podName"] = item["metadata"]["name"]
				log["podMetadata"] = item["metadata"]
				if "status" in item and "containerStatuses" in item["status"] and "containerID" in item["status"]["containerStatuses"][0]:
					containerID = item["status"]["containerStatuses"][0]["containerID"].replace("docker://","")
					log["containerID"] = containerID
					log["containerLog"] = kubectl_exec(" logs " + log["podName"])
					logs.append(log)
	return logs



def check_pod_status(pod):

	try:
		if pod["status"]["containerStatuses"][0]["restartCount"] > 0:
			return "Error"
	except Exception as e:
		pass

	try:
		if pod["status"]["phase"] == "Succeeded":
			return "Succeeded"
	except Exception as e:
		pass

	try:
		if pod["status"]["phase"] == "Unknown":
			return "Unknown"  #host is dead/cannot be reached.
	except Exception as e:
		pass

	try:
		if pod["status"]["phase"] == "Failed":
			return "Failed"
	except Exception as e:
		pass


	try:
		if pod["status"]["phase"] == "Pending":
			return "Pending"
	except Exception as e:
		pass
	
	try:
		if pod["status"]["phase"] == "Running" and all("ready" in item and item["ready"] for item in pod["status"]["containerStatuses"]):
			return "Running"
	except Exception as e:
		return "Pending"

	return "Unknown"

def get_pod_events(pod):
	description = kubectl_exec("describe pod %s" % pod["metadata"]["name"])
	ret = []
	for line in description.split("\n"):
		if "fit failure summary on nodes" in line:
			 ret += [item.strip() for item in line.replace("fit failure summary on nodes : ","").replace("(.*)","").strip().split(",")]
	return ret

def get_pod_pending_detail(pod):
	description = kubectl_exec("describe pod %s" % pod["metadata"]["name"])
	ret = []
	for line in description.split("\n"):
		if "fit failure summary on nodes" in line:
			 ret += [item.strip() for item in line.replace("fit failure summary on nodes : ","").replace("(.*)","").strip().split(",")]
	return ret

def check_pending_reason(pod,reason):
	reasons = get_pod_pending_detail(pod)
	return any([reason in item for item in reasons])

def GetJobStatus(jobId):
	podInfo = GetPod("run=" + jobId)
	output = "Unknown"
	detail = "Unknown Status"

	if podInfo is None:
		output = "kubectlERR"
	elif "items" in podInfo:
		podStatus = [check_pod_status(pod) for pod in  podInfo["items"]]
		detail = "=====================\n=====================\n=====================\n".join([yaml.dump(pod["status"], default_flow_style=False) for pod in podInfo["items"] if "status" in podInfo["items"]])


		######!!!!!!!!!!!!!!!!CAUTION!!!!!! since "any and all are used here, the order of if cause is IMPORTANT!!!!!, we need to deail with Faild,Error first, and then "Unknown" then "Pending", at last " Successed and Running"
		if len(podStatus) ==0:
			output = "Pending"
		elif any([status == "Error" for status in podStatus]):
			output = "Failed"
		elif any([status == "Failed" for status in podStatus]):
			output = "Failed"
		elif any([status == "Unknown" for status in podStatus]):
			output = "Unknown"
		elif  any([status == "Pending" for status in podStatus]):
			if any([check_pending_reason(pod,"PodFitsHostPorts") for pod in podInfo["items"]]):
				output = "PendingHostPort"
			else:
				output = "Pending"
		# there is a bug: if podStatus is empty, all (**) will be trigered. 
		elif all([status == "Succeeded" for status in podStatus]):
			output = "Succeeded"
		elif any([status == "Running" for status in podStatus]):   # as long as there are no "Unknown", "Pending" nor "Error" pods, once we see a running pod, the job should be in running status.  
			output = "Running"

	return output, detail



def SubmitJob(job):
	jobParams = json.loads(base64.b64decode(job["jobParams"]))
	if jobParams["jobtrainingtype"] == "RegularJob":
		SubmitRegularJob(job)
	elif jobParams["jobtrainingtype"] == "PSDistJob":
		SubmitPSDistJob(job)

def SubmitRegularJob(job):
	ret = {}
	dataHandler = DataHandler()

	try:
		jobParams = json.loads(base64.b64decode(job["jobParams"]))

		jobParams["pvc_job"] = "jobs-" + jobParams["jobId"]
		jobParams["pvc_work"] = "work-" + jobParams["jobId"]
		jobParams["pvc_data"] = "storage-" + jobParams["jobId"]


		if "jobPath" not in jobParams or len(jobParams["jobPath"].strip()) == 0: 
			dataHandler.SetJobError(jobParams["jobId"],"ERROR: job-path does not exist")
			return False

		if "workPath" not in jobParams or len(jobParams["workPath"].strip()) == 0: 
			dataHandler.SetJobError(jobParams["jobId"],"ERROR: work-path does not exist")
			return False

		if "dataPath" not in jobParams or len(jobParams["dataPath"].strip()) == 0: 
			dataHandler.SetJobError(jobParams["jobId"],"ERROR: data-path does not exist")
			return False


		jobPath,workPath,dataPath = GetStoragePath(jobParams["jobPath"],jobParams["workPath"],jobParams["dataPath"])


		localJobPath = os.path.join(config["storage-mount-path"],jobPath)

		if not os.path.exists(localJobPath):
			if "userId" in jobParams:
				mkdirsAsUser(localJobPath,jobParams["userId"])
				mkdirsAsUser(os.path.join(localJobPath,"models"),jobParams["userId"])
			else:
				mkdirsAsUser(localJobPath,"0")
				mkdirsAsUser(os.path.join(localJobPath,"models"),"0")

		jobParams["LaunchCMD"] = ""
		if "cmd" not in jobParams:
			jobParams["cmd"] = ""
			
		if isinstance(jobParams["cmd"], basestring) and not jobParams["cmd"] == "":
			launchScriptPath = os.path.join(localJobPath,"launch-%s.sh" % jobParams["jobId"])
			with open(launchScriptPath, 'w') as f:
				f.write(jobParams["cmd"] + "\n")
			f.close()	
			if "userId" in jobParams:
				os.system("chown -R %s %s" % (jobParams["userId"], launchScriptPath))
			jobParams["LaunchCMD"] = "[\"bash\", \"/job/launch-%s.sh\"]" % jobParams["jobId"]


		jobParams["jobDescriptionPath"] = "jobfiles/" + time.strftime("%y%m%d") + "/" + jobParams["jobId"] + "/" + jobParams["jobId"] + ".yaml"

		jobParams["jobNameLabel"] = ''.join(e for e in jobParams["jobName"] if e.isalnum())

		ENV = Environment(loader=FileSystemLoader("/"))

		jobTempDir = os.path.join(config["root-path"],"Jobs_Templete")
		jobTemp = os.path.join(jobTempDir, "RegularJob.yaml.template")

		jobParams["hostjobPath"] = os.path.join(config["storage-mount-path"], jobPath)
		jobParams["hostworkPath"] = os.path.join(config["storage-mount-path"], workPath)
		jobParams["hostdataPath"] = os.path.join(config["storage-mount-path"], dataPath)
		jobParams["nvidiaDriverPath"] = nvidiaDriverPath


		userName = jobParams["userName"]
		if "@" in userName:
			userName = userName.split("@")[0].strip()

		if "/" in userName:
			userName = userName.split("/")[1].strip()
		jobParams["userNameLabel"] = userName

		template = ENV.get_template(os.path.abspath(jobTemp))
		job_description = template.render(job=jobParams)

		jobDescriptionList = []

		jobDescriptionList.append(job_description)

		if ("interactivePort" in jobParams and len(jobParams["interactivePort"].strip()) > 0):
			ports = [p.strip() for p in re.split(",|;",jobParams["interactivePort"]) if len(p.strip()) > 0 and p.strip().isdigit()]
			for portNum in ports:
				jobParams["serviceId"] = "interactive-" + jobParams["jobId"] + "-" + portNum
				jobParams["port"] = portNum
				jobParams["port-name"] = "interactive"
				jobParams["port-type"] = "TCP"

				serviceTemplate = ENV.get_template(os.path.join(jobTempDir,"KubeSvc.yaml.template"))

				template = ENV.get_template(serviceTemplate)
				interactiveMeta = template.render(svc=jobParams)
				jobDescriptionList.append(interactiveMeta)


		jobDescription = "\n---\n".join(jobDescriptionList)

		jobDescriptionPath = os.path.join(config["storage-mount-path"], jobParams["jobDescriptionPath"])
		if not os.path.exists(os.path.dirname(os.path.realpath(jobDescriptionPath))):
			os.makedirs(os.path.dirname(os.path.realpath(jobDescriptionPath)))
		if os.path.isfile(jobDescriptionPath):
			output = kubectl_delete(jobDescriptionPath) 

		with open(jobDescriptionPath, 'w') as f:
			f.write(jobDescription)

		output = kubectl_create(jobDescriptionPath)	

		ret["output"] = output
		
		ret["jobId"] = jobParams["jobId"]


		if "userName" not in jobParams:
			jobParams["userName"] = ""

		dataHandler.UpdateJobTextField(jobParams["jobId"],"jobStatus","scheduling")
		dataHandler.UpdateJobTextField(jobParams["jobId"],"jobDescriptionPath",jobParams["jobDescriptionPath"])
		dataHandler.UpdateJobTextField(jobParams["jobId"],"jobDescription",base64.b64encode(jobDescription))


		jobMeta = {}
		jobMeta["jobDescriptionPath"] = jobParams["jobDescriptionPath"]
		jobMeta["jobPath"] = jobParams["jobPath"]
		jobMeta["workPath"] = jobParams["workPath"]
		jobMeta["jobPath"] = jobParams["jobPath"]
		jobMeta["LaunchCMD"] = jobParams["LaunchCMD"]

		jobMetaStr = base64.b64encode(json.dumps(jobMeta))
		dataHandler.UpdateJobTextField(jobParams["jobId"],"jobMeta",jobMetaStr)
	except Exception as e:
		print e
		ret["error"] = str(e)
		retries = dataHandler.AddandGetJobRetries(jobParams["jobId"])
		if retries >= 5:
			dataHandler.UpdateJobTextField(jobParams["jobId"],"jobStatus","error")
			dataHandler.UpdateJobTextField(jobParams["jobId"],"errorMsg","Cannot submit job!" + str(e))

	return ret



def SubmitPSDistJob(job):
	ret = {}
	dataHandler = DataHandler()

	try:
		jobParams = json.loads(base64.b64decode(job["jobParams"]))
		distJobParams = {}
		distJobParams["ps"] = []
		distJobParams["worker"] = []
		if jobParams["jobtrainingtype"] == "PSDistJob":
			jobDescriptionList = []
			nums = {"ps":int(jobParams["numps"]),"worker":int(jobParams["numpsworker"])}
			for role in ["ps","worker"]:
				for i in range(nums[role]):
					distJobParam={}
					jobParams["distId"] = "%s%d" % (role,i)
					jobParams["distRole"] = role

					if "jobPath" not in jobParams or len(jobParams["jobPath"].strip()) == 0: 
						dataHandler.SetJobError(jobParams["jobId"],"ERROR: job-path does not exist")
						return False

					jobParams["distJobPath"] = os.path.join(jobParams["jobPath"],jobParams["distId"])

					if "workPath" not in jobParams or len(jobParams["workPath"].strip()) == 0: 
						dataHandler.SetJobError(jobParams["jobId"],"ERROR: work-path does not exist")
						return False

					if "dataPath" not in jobParams or len(jobParams["dataPath"].strip()) == 0: 
						dataHandler.SetJobError(jobParams["jobId"],"ERROR: data-path does not exist")
						return False

					jobPath,workPath,dataPath = GetStoragePath(jobParams["distJobPath"],jobParams["workPath"],jobParams["dataPath"])

					localJobPath = os.path.join(config["storage-mount-path"],jobPath)
					if not os.path.exists(localJobPath):
						if "userId" in jobParams:
							mkdirsAsUser(localJobPath,jobParams["userId"])
						else:
							mkdirsAsUser(localJobPath,0)


					jobParams["LaunchCMD"] = ""
					if "cmd" not in jobParams:
						jobParams["cmd"] = ""

################One choice is that we only wait for certain time.			
#					launchCMD = """
##!/bin/bash
#mkdir -p /opt
#echo "[DLWorkspace System]: Waiting for all containers are ready..."
## wait for at most 10 mins. 
#for i in {1..200}; do
#	if [ ! -f /opt/run_dist_job ] || [ ! -f /opt/run_dist_job.sh ]; then
#		sleep 3
#	else
#		break
#	fi
#done
#if [ ! -f /opt/run_dist_job ] || [ ! -f /opt/run_dist_job.sh ]; then
#	echo "[DLWorkspace System]: Waiting for containers: timeout! Restarting..."
#	exit 1
#else
#	echo "[DLWorkspace System]: All containers are ready, launching training job..."
#	chmod +x /opt/run_dist_job.sh
#	/opt/run_dist_job.sh
#fi
#"""


					launchCMD = """
#!/bin/bash
mkdir -p /opt
echo "[DLWorkspace System]: Waiting for all containers are ready..."
while [ ! -f /opt/run_dist_job ] || [ ! -f /opt/run_dist_job.sh ]; do
	sleep 3
done
echo "[DLWorkspace System]: All containers are ready, launching training job..."
chmod +x /opt/run_dist_job.sh
/opt/run_dist_job.sh
"""

					launchScriptPath = os.path.join(localJobPath,"launch-%s.sh" % jobParams["jobId"])
					with open(launchScriptPath, 'w') as f:
						f.write(launchCMD)
					f.close()		
					jobParams["LaunchCMD"] = "[\"bash\", \"/job/launch-%s.sh\"]" % jobParams["jobId"]



					jobParams["jobNameLabel"] = ''.join(e for e in jobParams["jobName"] if e.isalnum())

					ENV = Environment(loader=FileSystemLoader("/"))

					jobTempDir = os.path.join(config["root-path"],"Jobs_Templete")
					jobTemp = os.path.join(jobTempDir, "DistJob.yaml.template")

					jobParams["hostjobPath"] = os.path.join(config["storage-mount-path"], jobPath)
					jobParams["hostworkPath"] = os.path.join(config["storage-mount-path"], workPath)
					jobParams["hostdataPath"] = os.path.join(config["storage-mount-path"], dataPath)
					jobParams["nvidiaDriverPath"] = nvidiaDriverPath

					random.seed(datetime.datetime.now())
					jobParams["containerPort"] = int(random.random()*1000+3000)

					template = ENV.get_template(os.path.abspath(jobTemp))
					job_description = template.render(job=jobParams)

					jobDescriptionList.append(job_description)

					distJobParam["distId"] =jobParams["distId"] 
					distJobParam["distRole"] =jobParams["distRole"] 
					distJobParam["distJobPath"] = jobParams["distJobPath"]
					distJobParam["containerPort"] = jobParams["containerPort"]
					distJobParams[role].append(distJobParam)

			jobParams["jobDescriptionPath"] = "jobfiles/" + time.strftime("%y%m%d") + "/" + jobParams["jobId"] + "/" + jobParams["jobId"] + ".yaml"
			jobDescription = "\n---\n".join(jobDescriptionList)


		jobDescriptionPath = os.path.join(config["storage-mount-path"], jobParams["jobDescriptionPath"])
		if not os.path.exists(os.path.dirname(os.path.realpath(jobDescriptionPath))):
			os.makedirs(os.path.dirname(os.path.realpath(jobDescriptionPath)))
		if os.path.isfile(jobDescriptionPath):
			output = kubectl_delete(jobDescriptionPath) 

		with open(jobDescriptionPath, 'w') as f:
			f.write(jobDescription)

		output = kubectl_create(jobDescriptionPath)	

		ret["output"] = output
		
		ret["jobId"] = jobParams["jobId"]


		if "userName" not in jobParams:
			jobParams["userName"] = ""

		dataHandler.UpdateJobTextField(jobParams["jobId"],"jobStatus","scheduling")
		dataHandler.UpdateJobTextField(jobParams["jobId"],"jobDescriptionPath",jobParams["jobDescriptionPath"])
		dataHandler.UpdateJobTextField(jobParams["jobId"],"jobDescription",base64.b64encode(jobDescription))


		jobMeta = {}
		jobMeta["jobDescriptionPath"] = jobParams["jobDescriptionPath"]
		jobMeta["jobPath"] = jobParams["jobPath"]
		jobMeta["workPath"] = jobParams["workPath"]
		jobMeta["jobPath"] = jobParams["jobPath"]
		jobMeta["LaunchCMD"] = jobParams["LaunchCMD"]
		jobMeta["distJobParams"] = distJobParams

		jobMetaStr = base64.b64encode(json.dumps(jobMeta))
		dataHandler.UpdateJobTextField(jobParams["jobId"],"jobMeta",jobMetaStr)
	except Exception as e:
		print e
		ret["error"] = str(e)
		retries = dataHandler.AddandGetJobRetries(jobParams["jobId"])
		if retries >= 5:
			dataHandler.UpdateJobTextField(jobParams["jobId"],"jobStatus","error")
			dataHandler.UpdateJobTextField(jobParams["jobId"],"errorMsg","Cannot submit job!" + str(e))

	return ret



def KillJob(job):
	dataHandler = DataHandler()
	if "jobDescriptionPath" in job and job["jobDescriptionPath"] is not None:
		jobDescriptionPath = os.path.join(config["storage-mount-path"], job["jobDescriptionPath"])
		if os.path.isfile(jobDescriptionPath):
			if kubectl_delete(jobDescriptionPath) == 0:
				dataHandler.UpdateJobTextField(job["jobId"],"jobStatus","killed")
				return True
			else:
				dataHandler.UpdateJobTextField(job["jobId"],"errorMsg","Cannot delete job from Kubernetes Cluster!")
	else:
		dataHandler.UpdateJobTextField(job["jobId"],"errorMsg","Cannot find job description file!")

	dataHandler.UpdateJobTextField(job["jobId"],"jobStatus","error")
	return False



def ExtractJobLog(jobId,logPath,userId):
	dataHandler = DataHandler()

	logs = GetLog(jobId)
	
	logStr = ""
	jobLogDir = os.path.dirname(logPath)
	if not os.path.exists(jobLogDir):
		mkdirsAsUser(jobLogDir,userId)

	for log in logs:
		if "podName" in log and "containerID" in log and "containerLog" in log:
			logStr += "=========================================================\n"
			logStr += "=========================================================\n"
			logStr += "=========================================================\n"
			logStr += "        logs from pod: %s\n" % log["podName"]
			logStr += "=========================================================\n"
			logStr += "=========================================================\n"
			logStr += "=========================================================\n"
			logStr += log["containerLog"]
			logStr += "\n\n\n"
			logStr += "=========================================================\n"
			logStr += "        end of logs from pod: %s\n" % log["podName"] 
			logStr += "=========================================================\n"
			logStr += "\n\n\n"

			try:
				containerLogPath = os.path.join(jobLogDir,"log-container-" + log["containerID"] + ".txt")
				with open(containerLogPath, 'w') as f:
					f.write(log["containerLog"])
				f.close()
				os.system("chown -R %s %s" % (userId, containerLogPath))
			except Exception as e:
				print e


	if len(logStr.strip()) > 0:
		dataHandler.UpdateJobTextField(jobId,"jobLog",logStr)
		with open(logPath, 'w') as f:
			f.write(logStr)
		f.close()
		os.system("chown -R %s %s" % (userId, logPath))




UnusualJobs = {}

def UpdateJobStatus(job):
	dataHandler = DataHandler()
	jobParams = json.loads(base64.b64decode(job["jobParams"]))


	if job["jobStatus"] == "scheduling" and jobParams["jobtrainingtype"] == "PSDistJob":
		launch_ps_dist_job(jobParams)


	jobPath,workPath,dataPath = GetStoragePath(jobParams["jobPath"],jobParams["workPath"],jobParams["dataPath"])
	localJobPath = os.path.join(config["storage-mount-path"],jobPath)
	logPath = os.path.join(localJobPath,"joblog.txt")
	

	result, detail = GetJobStatus(job["jobId"])
	dataHandler.UpdateJobTextField(job["jobId"],"jobStatusDetail",base64.b64encode(detail))

	printlog("job %s status: %s" % (job["jobId"], result))
	
	jobDescriptionPath = os.path.join(config["storage-mount-path"], job["jobDescriptionPath"]) if "jobDescriptionPath" in job else None
	if "userId" not in jobParams:
		jobParams["userId"]	= "0"
	if result.strip() == "Succeeded":
		ExtractJobLog(job["jobId"],logPath,jobParams["userId"])
		dataHandler.UpdateJobTextField(job["jobId"],"jobStatus","finished")
		if jobDescriptionPath is not None and os.path.isfile(jobDescriptionPath):
			kubectl_delete(jobDescriptionPath) 

	elif result.strip() == "Running":
		ExtractJobLog(job["jobId"],logPath,jobParams["userId"])
		if job["jobStatus"] != "running":
			dataHandler.UpdateJobTextField(job["jobId"],"jobStatus","running")
		if "interactivePort" in jobParams:
			serviceAddress = GetServiceAddress(job["jobId"])
			serviceAddress = base64.b64encode(json.dumps(serviceAddress))
			dataHandler.UpdateJobTextField(job["jobId"],"endpoints",serviceAddress)

	elif result.strip() == "Failed":
		printlog("Job %s fails, cleaning..." % job["jobId"])
		ExtractJobLog(job["jobId"],logPath,jobParams["userId"])
		dataHandler.UpdateJobTextField(job["jobId"],"jobStatus","failed")
		dataHandler.UpdateJobTextField(job["jobId"],"errorMsg",detail)
		if jobDescriptionPath is not None and os.path.isfile(jobDescriptionPath):
			kubectl_delete(jobDescriptionPath) 

	elif result.strip() == "Unknown":
		if job["jobId"] not in UnusualJobs:
			UnusualJobs[job["jobId"]] = datetime.datetime.now()
		elif (datetime.datetime.now() - UnusualJobs[job["jobId"]]).seconds > 300:
			del UnusualJobs[job["jobId"]]
			retries = dataHandler.AddandGetJobRetries(job["jobId"])
			if retries >= 5:
				printlog("Job %s fails for more than 5 times, abort" % job["jobId"])
				dataHandler.UpdateJobTextField(job["jobId"],"jobStatus","error")
				dataHandler.UpdateJobTextField(job["jobId"],"errorMsg","cannot launch the job.")
				if jobDescriptionPath is not None and os.path.isfile(jobDescriptionPath):
					kubectl_delete(jobDescriptionPath)				 
			else:
				printlog("Job %s fails in Kubernetes, delete and re-submit the job. Retries %d" % (job["jobId"] , retries))
				SubmitJob(job)
	elif result.strip() == "PendingHostPort":
		printlog("Cannot find host ports for job :%s, re-launch the job with different host ports " % (job["jobId"]))
	
		SubmitJob(job)

	if result.strip() != "Unknown" and job["jobId"] in UnusualJobs:
		del UnusualJobs[job["jobId"]]

def UpdateDistJobStatus(job):
	dataHandler = DataHandler()
	jobParams = json.loads(base64.b64decode(job["jobParams"]))

	if "userId" not in jobParams:
		jobParams["userId"]	= "0"

	jobPath,workPath,dataPath = GetStoragePath(jobParams["jobPath"],jobParams["workPath"],jobParams["dataPath"])
	localJobPath = os.path.join(config["storage-mount-path"],jobPath)
	logPath = os.path.join(localJobPath,"joblog.txt")
	

	result, detail = GetJobStatus(job["jobId"])
	dataHandler.UpdateJobTextField(job["jobId"],"jobStatusDetail",base64.b64encode(detail))

	printlog("job %s status: %s" % (job["jobId"], result))
	
	jobDescriptionPath = os.path.join(config["storage-mount-path"], job["jobDescriptionPath"]) if "jobDescriptionPath" in job else None


	jobId = jobParams["jobId"]
	workerPodInfo = GetPod("distRole=worker,run=" + jobId)
	psPodInfo = GetPod("distRole=ps,run=" + jobId)
	if "items" in workerPodInfo and len(workerPodInfo["items"]) == int(jobParams["numpsworker"]) and "items" in psPodInfo and len(psPodInfo["items"]) == int(jobParams["numps"]):
		if job["jobStatus"] == "scheduling" :
			launch_ps_dist_job(jobParams)
		if job["jobStatus"] == "running":
			result, detail = GetDistJobStatus(job["jobId"])
			dataHandler.UpdateJobTextField(job["jobId"],"jobStatusDetail",base64.b64encode(detail))

			printlog("job %s status: %s" % (job["jobId"], result))
	
			jobDescriptionPath = os.path.join(config["storage-mount-path"], job["jobDescriptionPath"]) if "jobDescriptionPath" in job else None

			if result.strip() == "Succeeded":
				ExtractJobLog(job["jobId"],logPath,jobParams["userId"])
				dataHandler.UpdateJobTextField(job["jobId"],"jobStatus","finished")
				if jobDescriptionPath is not None and os.path.isfile(jobDescriptionPath):
					kubectl_delete(jobDescriptionPath) 

			elif result.strip() == "Running":
				ExtractJobLog(job["jobId"],logPath,jobParams["userId"])
				if job["jobStatus"] != "running":
					dataHandler.UpdateJobTextField(job["jobId"],"jobStatus","running")
				if "interactivePort" in jobParams:
					serviceAddress = GetServiceAddress(job["jobId"])
					serviceAddress = base64.b64encode(json.dumps(serviceAddress))
					dataHandler.UpdateJobTextField(job["jobId"],"endpoints",serviceAddress)

			elif result.strip() == "Failed":
				printlog("Job %s fails, cleaning..." % job["jobId"])
				ExtractJobLog(job["jobId"],logPath,jobParams["userId"])
				dataHandler.UpdateJobTextField(job["jobId"],"jobStatus","failed")
				dataHandler.UpdateJobTextField(job["jobId"],"errorMsg",detail)
				if jobDescriptionPath is not None and os.path.isfile(jobDescriptionPath):
					kubectl_delete(jobDescriptionPath) 

			elif result.strip() == "Unknown":
				if job["jobId"] not in UnusualJobs:
					UnusualJobs[job["jobId"]] = datetime.datetime.now()
				elif (datetime.datetime.now() - UnusualJobs[job["jobId"]]).seconds > 300:
					del UnusualJobs[job["jobId"]]
					retries = dataHandler.AddandGetJobRetries(job["jobId"])
					if retries >= 5:
						printlog("Job %s fails for more than 5 times, abort" % job["jobId"])
						dataHandler.UpdateJobTextField(job["jobId"],"jobStatus","error")
						dataHandler.UpdateJobTextField(job["jobId"],"errorMsg","cannot launch the job.")
						if jobDescriptionPath is not None and os.path.isfile(jobDescriptionPath):
							kubectl_delete(jobDescriptionPath)				 
					else:
						printlog("Job %s fails in Kubernetes, delete and re-submit the job. Retries %d" % (job["jobId"] , retries))
						SubmitJob(job)

			if result.strip() != "Unknown" and job["jobId"] in UnusualJobs:
				del UnusualJobs[job["jobId"]]

	pass

def ScheduleJob():
	last_update_time = datetime.datetime.now()
	while True:
		try:
			dataHandler = DataHandler()
			pendingJobs = dataHandler.GetPendingJobs()
			printlog("updating status for %d jobs" % len(pendingJobs))
			for job in pendingJobs:
				try:
					print "Processing job: %s, status: %s" % (job["jobId"], job["jobStatus"])
					if job["jobStatus"] == "queued":
						SubmitJob(job)
					elif job["jobStatus"] == "killing":
						KillJob(job)
					elif job["jobStatus"] == "scheduling" or job["jobStatus"] == "running" :
						UpdateJobStatus(job)
				except Exception as e:
					print e
		except Exception as e:
			print e
		try:
			if (datetime.datetime.now() - last_update_time).seconds >= 120:
				print "updating cluster status..."
				get_cluster_status()
				last_update_time = datetime.datetime.now()
		except Exception as e:
			print e

		try:
			print "updating user directory..."
			set_user_directory()
		except Exception as e:
			print e

		time.sleep(1)







def run_dist_cmd_on_pod(podId, cmd, outputfile):
	remotecmd = "exec %s -- %s" % (podId,cmd)
	print remotecmd
	kubectl_exec_output_to_file(remotecmd,outputfile)



class Kube_RemoteCMD_Thread(threading.Thread):
	def __init__(self, jobId, podId, cmd, outputfile):
		threading.Thread.__init__(self)
		self.jobId = jobId
		self.podId = podId
		self.cmd = cmd
		self.outputfile = outputfile
	def run(self):
		run_dist_cmd_on_pod(self.podId, self.cmd, self.outputfile)


def launch_ps_dist_job(jobParams):
	jobId = jobParams["jobId"]
	workerPodInfo = GetPod("distRole=worker,run=" + jobId)
	psPodInfo = GetPod("distRole=ps,run=" + jobId)
	if "items" in workerPodInfo and len(workerPodInfo["items"]) == int(jobParams["numpsworker"]) and "items" in psPodInfo and len(psPodInfo["items"]) == int(jobParams["numps"]):
		podStatus = [check_pod_status(pod) for pod in  workerPodInfo["items"] + psPodInfo["items"] ]
		if all([status == "Running" for status in podStatus]):
			ps_pod_names = [pod["metadata"]["name"] for pod in psPodInfo["items"]]
			worker_pod_names = [pod["metadata"]["name"] for pod in workerPodInfo["items"]]

			ps_pod_ips = [pod["status"]["hostIP"] for pod in psPodInfo["items"]]
			worker_pod_ips = [pod["status"]["hostIP"] for pod in workerPodInfo["items"]]

			ps_num = len(psPodInfo["items"])
			worker_num = len(workerPodInfo["items"])

			ps_ports = [int(item["metadata"]["labels"]["distPort"]) for item in psPodInfo["items"]]
			worker_ports = [int(item["metadata"]["labels"]["distPort"]) for item in workerPodInfo["items"]]

			#port range: 30000~31000
			#rndList = range(max(1000,ps_num + worker_num))
			#random.shuffle(rndList)
			#ps_ports = [rndList[i] + 30000 for i in range(ps_num)]
			#worker_ports = [rndList[i + ps_num] + 30000 for i in range(worker_num)]

			ps_hosts = ",".join(["%s:%s" % (ps_pod_ips[i],ps_ports[i]) for i in range(ps_num)])
			worker_hosts = ",".join(["%s:%s" % (worker_pod_ips[i],worker_ports[i]) for i in range(worker_num)])

			ps_files = ["/tmp/" + str(uuid.uuid4()) for i in range(ps_num)]
			worker_files = ["/tmp/" + str(uuid.uuid4()) for i in range(worker_num)]

			ps_cmd = ["%s --ps_hosts=%s --worker_hosts=%s --job_name=ps --task_index=%d 2>&1 | tee %s" % (jobParams["cmd"], ps_hosts,worker_hosts,i,ps_files[i]) for i in range(ps_num)]
			worker_cmd = ["%s --ps_hosts=%s --worker_hosts=%s --job_name=worker --task_index=%d 2>&1 | tee %s" % (jobParams["cmd"], ps_hosts,worker_hosts,i,worker_files[i]) for i in range(worker_num)]


			for i in range(ps_num):
				os.system("mkdir -p %s" % ps_files[i])
				ps_files[i] = os.path.join(ps_files[i],"run_dist_job.sh")
				with open(ps_files[i], 'w') as f:
					f.write(ps_cmd[i] + "\n")
				f.close()		
				if "userId" in jobParams:
					os.system("chown -R %s %s" % (jobParams["userId"], ps_files[i]))
				remotecmd = "cp %s %s:/opt/run_dist_job.sh" % (ps_files[i],ps_pod_names[i])
				kubectl_exec(remotecmd)
				kubectl_exec("exec %s touch /opt/run_dist_job" % ps_pod_names[i])


			for i in range(worker_num):
				os.system("mkdir -p %s" % worker_files[i])
				worker_files[i] = os.path.join(worker_files[i],"run_dist_job.sh")
				with open(worker_files[i], 'w') as f:
					f.write(worker_cmd[i] + "\n")
				f.close()	
				if "userId" in jobParams:
					os.system("chown -R %s %s" % (jobParams["userId"], worker_files[i]))
				remotecmd = "cp %s %s:/opt/run_dist_job.sh" % (worker_files[i],worker_pod_names[i])
				kubectl_exec(remotecmd)
				kubectl_exec("exec %s touch /opt/run_dist_job" % worker_pod_names[i])

			dataHandler = DataHandler()
			dataHandler.UpdateJobTextField(job["jobId"],"jobStatus","running")

			#ps_threads = [Kube_RemoteCMD_Thread(jobId,ps_pod_names[i],ps_cmd[i],ps_logfiles[i]) for i in range(ps_num)]
			#worker_threads = [Kube_RemoteCMD_Thread(jobId,worker_pod_names[i],worker_cmd[i],worker_logfiles[i]) for i in range(worker_num)]
			
			#for t in ps_threads:
			#	t.start()

			#for t in worker_threads:
			#	t.start()


			#while (True):
				#for t in ps_threads:
				#	print t.isAlive()
				#time.sleep(5)

			#cmd = "test"
			#thread.start_new_thread( run_dist_cmd_on_pod,
			#(workerPodInfo["items"][0]["metadata"]["name"], cmd) )

def set_user_directory():
	dataHandler = DataHandler()
	users = dataHandler.GetUsers()
	for username,userid in users:
		if "@" in username:
			username = username.split("@")[0]
		if "/" in username:
			username = username.split("/")[1]
		if "\\" in username:
			username = username.split("\\")[1]	
		userpath = os.path.join(config["storage-mount-path"],"work/"+username)
		if not os.path.exists(userpath):
			os.system("mkdir -p "+userpath)
			os.system("chown -R "+userid+":"+"500000513 "+userpath)

		sshkeypath = os.path.join(userpath,".ssh/id_rsa")
		if not os.path.exists(sshkeypath):
			os.system("mkdir -p "+os.path.dirname(sshkeypath))
			os.system("ssh-keygen -t rsa -b 4096 -f %s -P ''" % sshkeypath)
			os.system("chown -R "+userid+":"+"500000513 "+userpath)
			os.system("chmod 700 -R "+os.path.dirname(sshkeypath))

def get_cluster_status():
	cluster_status={}
	try:
		output = kubectl_exec(" get nodes -o yaml")
		nodeInfo = yaml.load(output)
		nodes_status = {}
		user_status = {}

		if "items" in nodeInfo:
			for node in nodeInfo["items"]:
				node_status	= {}
				node_status["name"] = node["metadata"]["name"]
				node_status["labels"] = node["metadata"]["labels"]
				node_status["gpu_allocatable"] = int(node["status"]["allocatable"]["alpha.kubernetes.io/nvidia-gpu"])
				node_status["gpu_capacity"] = int(node["status"]["capacity"]["alpha.kubernetes.io/nvidia-gpu"])
				node_status["gpu_used"] = 0
				node_status["InternalIP"] = "unknown"
				node_status["pods"] = []

				if "addresses" in node["status"]:
					for addr in node["status"]["addresses"]:
						if addr["type"] == "InternalIP":
							node_status["InternalIP"]  = addr["address"] 


				node_status["scheduled_service"] = []
				for l,s in node_status["labels"].iteritems():
					if s == "active" and l != "all" and l != "default":
						node_status["scheduled_service"].append(l)

				if "unschedulable" in node["spec"] and node["spec"]["unschedulable"]:
					node_status["unschedulable"] = True
				else:
					node_status["unschedulable"] = False
				nodes_status[node_status["name"]] = node_status


		output = kubectl_exec(" get pods -o yaml")
		podsInfo = yaml.load(output)
		if "items" in podsInfo:
			for pod in podsInfo["items"]:
				gpus = 0
				username = None
				if "metadata" in pod and "labels" in pod["metadata"] and "userName" in pod["metadata"]["labels"]:
					username = pod["metadata"]["labels"]["userName"]
				if "spec" in pod and "nodeName" in pod["spec"]:
					node_name = pod["spec"]["nodeName"]
					pod_name = pod["metadata"]["name"]
					if username is not None:
						pod_name += " : " + username
					if "containers" in pod["spec"] :
						for container in pod["spec"]["containers"]:
							
							if "resources" in container and "requests" in container["resources"] and "alpha.kubernetes.io/nvidia-gpu" in container["resources"]["requests"]:
								gpus += int(container["resources"]["requests"]["alpha.kubernetes.io/nvidia-gpu"])
					if node_name in nodes_status:
						nodes_status[node_name]["gpu_used"] += gpus
						nodes_status[node_name]["pods"].append(pod_name)

				if username is not None:
					if username not in user_status:
						user_status[username] = gpus
					else:
						user_status[username] += gpus
				




		gpu_avaliable	= 0
		gpu_reserved	= 0
		gpu_capacity = 0
		gpu_unschedulable = 0
		gpu_schedulable = 0
		gpu_used = 0


		for node_name, node_status in nodes_status.iteritems():
			if node_status["unschedulable"]:
				gpu_unschedulable += node_status["gpu_capacity"]
			else:
				gpu_avaliable	+= (node_status["gpu_allocatable"] - node_status["gpu_used"])
				gpu_schedulable	+= node_status["gpu_capacity"]
				gpu_unschedulable += (node_status["gpu_capacity"] - node_status["gpu_allocatable"])

			gpu_reserved += (node_status["gpu_capacity"] - node_status["gpu_allocatable"])
			gpu_used +=node_status["gpu_used"]
			gpu_capacity	+= node_status["gpu_capacity"]

		cluster_status["user_status"] = []
		for user_name, user_gpu in user_status.iteritems():
			cluster_status["user_status"].append({"userName":user_name, "userGPU":user_gpu})

		cluster_status["gpu_avaliable"] = gpu_avaliable
		cluster_status["gpu_capacity"] = gpu_capacity
		cluster_status["gpu_unschedulable"] = gpu_unschedulable
		cluster_status["gpu_used"] = gpu_used
		cluster_status["gpu_reserved"] = gpu_reserved
		cluster_status["node_status"] = [node_status for node_name, node_status in nodes_status.iteritems()] 

	except Exception as e:
		print e
	dataHandler = DataHandler()

	cluster_status["AvaliableJobNum"] = dataHandler.GetActiveJobsCount()
	cluster_status["TotalJobNum"] = dataHandler.GetALLJobsCount()
	dataHandler.UpdateClusterStatus(cluster_status)
	dataHandler.Close()
	return cluster_status


if __name__ == '__main__':
	TEST_SUB_REG_JOB = False
	TEST_JOB_STATUS = False
	TEST_DEL_JOB = False
	TEST_GET_TB = False
	TEST_GET_SVC = False
	TEST_GET_LOG = False

	job = {}
	job["jobId"] = "d3477fc6-8389-4058-b666-fd306695d03d"
	job["numps"] = "1"
	job["numworker"] = "2"
	job["distcmd"] = "/work/tensorflow/models/inception/bazel-bin/inception/imagenet_distributed_train --batch_size=32 --train_dir=/job/model --data_dir=/data/tensor"
	#launch_ps_dist_job(job)
	#get_cluster_status()
	ScheduleJob()
	#set_user_directory()



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
