import json
import os
import time
import argparse
import uuid
import subprocess
import sys
import datetime

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../storage"))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../utils"))

from jobs_tensorboard import GenTensorboardMeta

import yaml
from jinja2 import Environment, FileSystemLoader, Template
from config import config
from DataHandler import DataHandler
import base64

import re

import thread
import threading
import random


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
		hostName = None

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
					if "spec" in item and "nodeName" in item["spec"]:
						hostName = item["spec"]["nodeName"]
		if containerPort is not None and hostIP is not None and hostPort is not None:
			svcMapping = {}
			svcMapping["containerPort"] = containerPort
			svcMapping["hostPort"] = hostPort

			if "." not in hostName and "domain" in config and len(config["domain"].strip()) >0:
				hostName += "."+config["domain"]

			svcMapping["hostIP"] = hostIP
			svcMapping["hostName"] = hostName
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
