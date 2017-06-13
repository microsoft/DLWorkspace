import json
import os
import time
import argparse
import uuid
import subprocess
import sys
import datetime

import yaml
from jinja2 import Environment, FileSystemLoader, Template
import base64

import re

import thread
import threading
import random

import textwrap
import logging
import logging.config

from multiprocessing import Process, Manager



sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../storage"))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../utils"))

from jobs_tensorboard import GenTensorboardMeta
import k8sUtils

from config import config
from DataHandler import DataHandler



def create_log( logdir = '/var/log/dlworkspace' ):
	if not os.path.exists( logdir ):
		os.system("mkdir -p " + logdir )
	with open('logging.yaml') as f:
		logging_config = yaml.load(f)
		f.close()
		logging_config["handlers"]["file"]["filename"] = logdir+"/nodemanager.log"
		logging.config.dictConfig(logging_config)



def get_cluster_status():
	cluster_status={}
	try:
		output = k8sUtils.kubectl_exec(" get nodes -o yaml")
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

				if "status" in node and "conditions" in node["status"]:
					for condi in node["status"]:
						if "type" in condi and condi["type"] == "Ready" and "status" in condi and condi["status"] == "Unknown":
							node_status["unschedulable"] = True


				nodes_status[node_status["name"]] = node_status


		output = k8sUtils.kubectl_exec(" get pods -o yaml")
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


def Run():
	create_log()
	logging.info("start to update nodes usage information ...")

	while True:
		try:
			get_cluster_status()
		except Exception as e:
			print e
		time.sleep(30)

if __name__ == '__main__':
	Run()