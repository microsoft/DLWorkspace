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
from ResourceInfo import ResourceInfo

import re

import thread
import threading
import random

import textwrap
import logging
import logging.config
import copy

import pycurl
from StringIO import StringIO

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



def check_cluster_status_change(o_cluster_status,cluster_status):
    if o_cluster_status is None:
        return True

    checkList = ["TotalJobNum","AvaliableJobNum","gpu_used","user_status","node_status"]
    for item in checkList:
        if item not in o_cluster_status or item not in cluster_status or o_cluster_status[item] != cluster_status[item]:
            return True
    return False


def get_job_gpu_usage(jobId):
    try:
        hostaddress = config.get("prometheus_node", "127.0.0.1")

        url = """http://"""+hostaddress+""":9091/prometheus/api/v1/query?query=avg%28avg_over_time%28task_gpu_percent%7Bpod_name%3D%22""" + jobId + """%22%7D%5B4h%5D%29%29+by+%28pod_name%2C+instance%2C+username%29"""

        curl = pycurl.Curl()
        curl.setopt(pycurl.URL, url)
        curl.setopt(pycurl.SSL_VERIFYPEER, 1)
        curl.setopt(pycurl.SSL_VERIFYHOST, 0)
        curl.setopt(curl.FOLLOWLOCATION, True)
        buff = StringIO()
        curl.setopt(pycurl.WRITEFUNCTION, buff.write)
        curl.perform()
        responseStr = buff.getvalue()
        curl.close()
        gpuUsage = int(float(json.loads(responseStr)["data"]["result"][0]["value"][1]))
    except Exception as e:
        gpuUsage = None

    return gpuUsage

def get_cluster_status():
    cluster_status={}
    gpuStr = "nvidia.com/gpu"
    try:
        output = k8sUtils.kubectl_exec(" get nodes -o yaml")
        nodeInfo = yaml.load(output)
        nodes_status = {}
        user_status = {}

        if "items" in nodeInfo:
            for node in nodeInfo["items"]:
                node_status    = {}
                node_status["name"] = node["metadata"]["name"]
                node_status["labels"] = node["metadata"]["labels"]
                node_status["gpuType"] = ""

                node_status["scheduled_service"] = []
                for l,s in node_status["labels"].iteritems():
                    if s == "active" and l != "all" and l != "default":
                        node_status["scheduled_service"].append(l)
                    if l == "gpuType":
                        node_status["scheduled_service"].append(s)
                        node_status["gpuType"] = s

                if (gpuStr in node["status"]["allocatable"]):
                    node_status["gpu_allocatable"] = ResourceInfo({node_status["gpuType"]: int(node["status"]["allocatable"][gpuStr])}).ToSerializable()
                else:
                    node_status["gpu_allocatable"] = ResourceInfo().ToSerializable()
                if (gpuStr in node["status"]["capacity"]):
                    node_status["gpu_capacity"] = ResourceInfo({node_status["gpuType"] : int(node["status"]["capacity"][gpuStr])}).ToSerializable()
                else:
                    node_status["gpu_capacity"] = ResourceInfo().ToSerializable()
                node_status["gpu_used"] = ResourceInfo().ToSerializable()
                node_status["InternalIP"] = "unknown"
                node_status["pods"] = []
                if "annotations" in node["metadata"]:
                    if "node.alpha/DeviceInformation" in node["metadata"]["annotations"]:
                        node_info = json.loads(node["metadata"]["annotations"]["node.alpha/DeviceInformation"])
                        if (int(node_info["capacity"]["alpha.gpu/numgpu"]) > ResourceInfo(node_status["gpu_capacity"]).TotalCount()):
                            node_status["gpu_capacity"] = ResourceInfo({node_status["gpuType"]: int(node_info["capacity"]["alpha.gpu/numgpu"])}).ToSerializable()
                        if (int(node_info["allocatable"]["alpha.gpu/numgpu"]) > ResourceInfo(node_status["gpu_allocatable"]).TotalCount()):
                            node_status["gpu_allocatable"] = ResourceInfo({node_status["gpuType"] : int(node_info["allocatable"]["alpha.gpu/numgpu"])}).ToSerializable()

                if "addresses" in node["status"]:
                    for addr in node["status"]["addresses"]:
                        if addr["type"] == "InternalIP":
                            node_status["InternalIP"]  = addr["address"] 

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
                    gpuUsage = get_job_gpu_usage(pod["metadata"]["name"])
                    if gpuUsage is not None:
                        pod_name += " (gpu usage:" + str(gpuUsage) + "%)"
                        if gpuUsage <= 25:
                            pod_name += "!!!!!!"
                    pod_info_cont = {}
                    pod_info_initcont = {}
                    if "annotations" in pod["metadata"]:
                        if "pod.alpha/DeviceInformation" in pod["metadata"]["annotations"]:
                            pod_info = json.loads(pod["metadata"]["annotations"]["pod.alpha/DeviceInformation"])
                            if "runningcontainer" in pod_info:
                                pod_info_cont = pod_info["runningcontainer"]
                            if "initcontainer" in pod_info:
                                pod_info_initcont = pod_info["initcontainer"]
                    if "containers" in pod["spec"] :
                        for container in pod["spec"]["containers"]:
                            containerGPUs = 0
                            if "resources" in container and "requests" in container["resources"] and gpuStr in container["resources"]["requests"]:
                                containerGPUs = int(container["resources"]["requests"][gpuStr])
                            if container["name"] in pod_info_cont:
                                if "requests" in pod_info_cont[container["name"]] and "alpha.gpu/numgpu" in pod_info_cont[container["name"]]["requests"]:
                                    containerGPUs = max(int(pod_info_cont[container["name"]]["requests"]["alpha.gpu/numgpu"]), containerGPUs)
                            gpus += containerGPUs
                            pod_name += " (gpu #:" + str(containerGPUs) + ")"

                    if node_name in nodes_status:
                        nodes_status[node_name]["gpu_used"] = ResourceInfo(nodes_status[node_name]["gpu_used"]).Add(ResourceInfo({nodes_status[node_name]["gpuType"] : gpus})).ToSerializable()
                        nodes_status[node_name]["pods"].append(pod_name)

                        if username is not None:
                            if username not in user_status:
                                user_status[username] = ResourceInfo({nodes_status[node_name]["gpuType"] : gpus})
                            else:
                                user_status[username].Add(ResourceInfo({nodes_status[node_name]["gpuType"] : gpus}))

        gpu_avaliable    = ResourceInfo()
        gpu_reserved    = ResourceInfo()
        gpu_capacity = ResourceInfo()
        gpu_unschedulable = ResourceInfo()
        gpu_schedulable = ResourceInfo()
        gpu_used = ResourceInfo()

        for node_name, node_status in nodes_status.iteritems():
            if node_status["unschedulable"]:
                gpu_unschedulable.Add(ResourceInfo(node_status["gpu_capacity"]))
            else:
                gpu_avaliable.Add(ResourceInfo.Difference(ResourceInfo(node_status["gpu_allocatable"]), ResourceInfo(node_status["gpu_used"])))
                gpu_schedulable.Add(ResourceInfo(node_status["gpu_capacity"]))
                gpu_unschedulable.Add(ResourceInfo.Difference(ResourceInfo(node_status["gpu_capacity"]), ResourceInfo(node_status["gpu_allocatable"])))

            gpu_reserved.Add(ResourceInfo.Difference(ResourceInfo(node_status["gpu_capacity"]), ResourceInfo(node_status["gpu_allocatable"])))
            gpu_used.Add(ResourceInfo(node_status["gpu_used"]))
            gpu_capacity.Add(ResourceInfo(node_status["gpu_capacity"]))

        cluster_status["user_status"] = []
        for user_name, user_gpu in user_status.iteritems():
            cluster_status["user_status"].append({"userName":user_name, "userGPU":user_gpu.ToSerializable()})

        cluster_status["gpu_avaliable"] = gpu_avaliable.ToSerializable()
        cluster_status["gpu_capacity"] = gpu_capacity.ToSerializable()
        cluster_status["gpu_unschedulable"] = gpu_unschedulable.ToSerializable()
        cluster_status["gpu_used"] = gpu_used.ToSerializable()
        cluster_status["gpu_reserved"] = gpu_reserved.ToSerializable()
        cluster_status["node_status"] = [node_status for node_name, node_status in nodes_status.iteritems()] 

    except Exception as e:
        print(e)

    dataHandler = DataHandler()
    cluster_status["AvaliableJobNum"] = dataHandler.GetActiveJobsCount()

    if "cluster_status" in config and check_cluster_status_change(config["cluster_status"],cluster_status):
        logging.info("updating the cluster status...")
        dataHandler.UpdateClusterStatus(cluster_status)
    else:
        logging.info("nothing changed in cluster, skipping the cluster status update...")

    config["cluster_status"] = copy.deepcopy(cluster_status)
    dataHandler.Close()
    return cluster_status


def Run():
    create_log()
    logging.info("start to update nodes usage information ...")
    config["cluster_status"] = None
    while True:
        try:
            get_cluster_status()
        except Exception as e:
            print e
            logging.info(str(e))
        time.sleep(30)

if __name__ == '__main__':
    Run()
