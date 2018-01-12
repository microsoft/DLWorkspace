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
import copy

import pycurl
from StringIO import StringIO

from multiprocessing import Process, Manager


sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../storage"))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../utils"))

from jobs_tensorboard import GenTensorboardMeta
import k8sUtils
from JobRestAPIUtils import KillJob
from sendmail import sendmail

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
        if "webportal_node" in config:
            hostaddress = config["webportal_node"]
        else:
            hostaddress = "127.0.0.1"
        url = """http://"""+hostaddress+""":8086/query?db=collectd&epoch=ms&q=SELECT+max%28%22value%22%29+FROM+%22jobcuda_value%22+WHERE+%28%22host%22+%3D~+%2F%5E"""+jobId+"""%24%2F+AND+%22type%22+%3D+%27percent%27+AND+%22type_instance%22+%3D+%27gpu_util%27+AND+%22instance%22+%3D~+%2F%5Egpu0%24%2F%29+AND+time+%3E%3D+now%28%29+-+480m+fill%28null%29%3B"""

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
        gpuUsage = int(json.loads(responseStr)["results"][0]["series"][0]["values"][0][1])
    except Exception as e:
        gpuUsage = None

    return gpuUsage

lastGPUUsedTime = {}
GPUUsageSample = {}
lastEmailSend = {}
def auto_kill_low_usage_job(gpu_usage,jobId, userId):
    try:
        dt = datetime.datetime.now()
        if jobId in lastGPUUsedTime:
            logging.info("Checking gpu usage of job %s (user: %s, gpuUsage: %s) , job has been idel for %d" % (jobId,userId, gpu_usage, (dt - lastGPUUsedTime[jobId]).seconds))


        if gpu_usage <= 10 and jobId in lastGPUUsedTime:
            if jobId not in GPUUsageSample:
                GPUUsageSample[jobId] = []
            GPUUsageSample[jobId].append(dt)
            low_usage_count = 0
            for item in GPUUsageSample[jobId]:
                if (dt - item).seconds <= 28800:
                    low_usage_count += 1

            low_usage_count1 = 0
            for item in GPUUsageSample[jobId]:
                if (dt - item).seconds <= 3600:
                    low_usage_count1 += 1
            logging.info("Checking gpu usage of job %s (user: %s, gpuUsage: %s) , low_usage_count %d, low_usage_count1 %d" % (jobId,userId, gpu_usage, low_usage_count, low_usage_count1))

            if (dt - lastGPUUsedTime[jobId]).seconds > 28800 and low_usage_count > 500 and low_usage_count1 >=100:
                KillJob(jobId)
                logging.info("Job %s is killed due to low gpu usage" % jobId)
                msg = "Hi %s, Your job [%s] in DLWorkspace cluster has low gpu usage for more than 8 hours and has been terminated." % (userId, jobId)
                msg_html = """
                    Hi %s, <br />
                    Your job <a href = 'http://vig-dlworkspace.redmond.corp.microsoft.com/Home/JobDetail/?jobId=%s'>[%s] </a>  in DLWorkspace cluster has low gpu usage for more than 8 hours and has been terminated. <br />
                    <br />
                    <br />
                    Best, <br />
                    DLWorkspace Cluster Admins
                """ % (userId, jobId, jobId)
                sendmail(userId+"@microsoft.com", "[DLWorkspace Notice] Your Job %s has been terminated" % jobId, msg,msg_html)


            if (dt - lastGPUUsedTime[jobId]).seconds > 14400:
                if jobId not in lastEmailSend or (dt - lastEmailSend[jobId]).seconds > 3600:
                    lastEmailSend[jobId] = dt
                    msg = "Hi %s, Your job [%s] in DLWorkspace cluster has low gpu usage for %f hours. Your job will be killed if the gpu is not used for 8 hours." % (userId, jobId, ((dt - lastGPUUsedTime[jobId]).seconds) / 3600)
                    msg_html = """
                        Hi %s, <br />
                        Your job <a href = 'http://vig-dlworkspace.redmond.corp.microsoft.com/Home/JobDetail/?jobId=%s'>[%s] </a>  in DLWorkspace cluster has low gpu usage for %f hours. Your job will be killed if the gpu is not used for 8 hours. <br />
                        <br />
                        Please make sure all of your data is copied to persistent storage, including /work, /job, /data, etc. The data stored in other place (e.g. /tmp, home folder, root folder) will be lost after the job is killed.
                        <br />
                        Best, <br />
                        DLWorkspace Cluster Admins
                    """ % (userId, jobId, jobId, ((dt - lastGPUUsedTime[jobId]).seconds) / 3600)
                    sendmail(userId+"@microsoft.com", "DLWorkspace Notice", msg,msg_html)
                    logging.info("Send low gpu usage for job %s" % jobId)

        else:
            lastGPUUsedTime[jobId] = dt
            GPUUsageSample[jobId] = []
        for jobId, t in lastGPUUsedTime.iteritems():
            if (datetime.datetime.now() - t).seconds >= 259200: # 3600 * 24 * 3
                if jobId in lastGPUUsedTime:
                    lastGPUUsedTime.pop(jobId, None)
                if jobId in GPUUsageSample:
                    GPUUsageSample.pop(jobId, None)
                if jobId in lastEmailSend:
                    lastEmailSend.pop(jobId, None)

    except Exception as e:
        logging.info(str(e))
        pass
def get_cluster_status():
    cluster_status={}
    gpuStr = "alpha.kubernetes.io/nvidia-gpu"
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
                if (gpuStr in node["status"]["allocatable"]):
                    node_status["gpu_allocatable"] = int(node["status"]["allocatable"][gpuStr])
                else:
                    node_status["gpu_allocatable"] = 0
                if (gpuStr in node["status"]["capacity"]):
                    node_status["gpu_capacity"] = int(node["status"]["capacity"][gpuStr])
                else:
                    node_status["gpu_capacity"] = 0
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
                    gpuUsage = get_job_gpu_usage(pod["metadata"]["name"])
                    if gpuUsage is not None:
                        pod_name += " (gpu usage:" + str(gpuUsage) + "%)"
                        if gpuUsage <= 25:
                            pod_name += "!!!!!!"
                    if "containers" in pod["spec"] :
                        for container in pod["spec"]["containers"]:
                            if "resources" in container and "requests" in container["resources"] and gpuStr in container["resources"]["requests"]:
                                gpus += int(container["resources"]["requests"][gpuStr])
                                pod_name += " (gpu #:" + container["resources"]["requests"][gpuStr] + ")"
                    if gpus >=2 and gpuUsage is not None:
                        auto_kill_low_usage_job(gpuUsage,pod["metadata"]["name"],username)
                    if node_name in nodes_status:
                        nodes_status[node_name]["gpu_used"] += gpus
                        nodes_status[node_name]["pods"].append(pod_name)

                if username is not None:
                    if username not in user_status:
                        user_status[username] = gpus
                    else:
                        user_status[username] += gpus

        gpu_avaliable    = 0
        gpu_reserved    = 0
        gpu_capacity = 0
        gpu_unschedulable = 0
        gpu_schedulable = 0
        gpu_used = 0


        for node_name, node_status in nodes_status.iteritems():
            if node_status["unschedulable"]:
                gpu_unschedulable += node_status["gpu_capacity"]
            else:
                gpu_avaliable    += (node_status["gpu_allocatable"] - node_status["gpu_used"])
                gpu_schedulable    += node_status["gpu_capacity"]
                gpu_unschedulable += (node_status["gpu_capacity"] - node_status["gpu_allocatable"])

            gpu_reserved += (node_status["gpu_capacity"] - node_status["gpu_allocatable"])
            gpu_used +=node_status["gpu_used"]
            gpu_capacity    += node_status["gpu_capacity"]

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