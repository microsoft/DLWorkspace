import json
import os
import time
import argparse
import uuid
import subprocess32
import sys
from datetime import datetime
from tzlocal import get_localzone
import pytz


sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../storage"))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../utils"))

from jobs_tensorboard import GenTensorboardMeta

import yaml
from jinja2 import Environment, FileSystemLoader, Template
from config import config, GetStoragePath
import base64

import re

import thread
import threading
import random
import pycurl
from StringIO import StringIO


def curl_get(url):
    curl = pycurl.Curl()
    curl.setopt(pycurl.URL, url)
    curl.setopt(pycurl.SSL_VERIFYPEER, 1)
    curl.setopt(pycurl.SSL_VERIFYHOST, 0)
    curl.setopt(pycurl.CAINFO, config["certificate-authority"])
    curl.setopt(pycurl.SSLKEYTYPE, "PEM")
    curl.setopt(pycurl.SSLKEY, config["client-key"])
    curl.setopt(pycurl.SSLCERTTYPE, "PEM")
    curl.setopt(pycurl.SSLCERT, config["client-certificate"])
    curl.setopt(curl.FOLLOWLOCATION, True)
    buff = StringIO()
    curl.setopt(pycurl.WRITEFUNCTION, buff.write)
    curl.perform()
    responseStr = buff.getvalue()
    curl.close()
    return responseStr


def kubectl_create(jobfile, EXEC=True):
    if EXEC:
        try:
            output = subprocess32.check_output(["bash", "-c", config["kubelet-path"] + " create -f " + jobfile])
        except Exception as e:
            print e
            output = ""
    else:
        output = "Job " + jobfile + " is not submitted to kubernetes cluster"
    return output


def kubectl_delete(jobfile, EXEC=True):
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

# timeout=0 means never timeout


def kubectl_exec(params, timeout=None):
    """As defalut, never timeout."""
    try:
        #print ("bash -c %s %s" % (config["kubelet-path"], params))
        # TODO set the timeout
        output = subprocess32.check_output(["bash", "-c", config["kubelet-path"] + " " + params], timeout=timeout)
    except Exception as e:
        print "EXCEPTION: " + str(e)
        output = ""
    return output


def kubectl_exec_output_to_file(params, file):
    os.system("%s %s 2>&1 | tee %s" % (config["kubelet-path"], params, file))


def Split(text, spliter):
    return [x for x in text.split(spliter) if len(x.strip()) > 0]


def GetServiceAddress(jobId):
    ret = []

    #output = kubectl_exec(" describe svc -l run=" + jobId)
    #print "output=\n" + output
    #svcs = output.split("\n\n\n")
    outputYaml = kubectl_exec("  get svc -l run={0} -o=yaml".format(jobId))
    output = yaml.load(outputYaml)
    svcs = output["items"]

    for svc in svcs:
        # lines = [Split(x,"\t") for x in Split(svc,"\n")]
        # containerPort = None
        # hostPort = None
        # selector = None
        # hostIP = None
        # hostName = None

        # for line in lines:
        #     if len(line) > 1:
        #         if line[0] == "Port:":
        #             containerPort = line[-1]
        #             if "/" in containerPort:
        #                 containerPort = containerPort.split("/")[0]
        #         if line[0] == "NodePort:":
        #             hostPort = line[-1]
        #             if "/" in hostPort:
        #                 hostPort = hostPort.split("/")[0]

        #         if line[0] == "Selector:" and line[1] != "<none>":
        #             selector = line[-1]

        containerPort = svc["spec"]["ports"][0]["port"]
        hostPort = svc["spec"]["ports"][0]["nodePort"]
        labelIndex = 0
        selector = ""
        for label in svc["spec"]["selector"]:
            if (labelIndex > 0):
                selector += ","
            selector += "{0}={1}".format(label, svc["spec"]["selector"][label])
            labelIndex += 1
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

            if "." not in hostName and "domain" in config and (not config["domain"] is None) and len(config["domain"].strip()) > 0:
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
                    containerID = item["status"]["containerStatuses"][0]["containerID"].replace("docker://", "")
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
            return "Unknown"  # host is dead/cannot be reached.
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
             ret += [item.strip() for item in line.replace("fit failure summary on nodes : ", "").replace("(.*)", "").strip().split(",")]
    return ret


def get_pod_pending_detail(pod):
    description = kubectl_exec("describe pod %s" % pod["metadata"]["name"])
    ret = []
    for line in description.split("\n"):
        if "fit failure summary on nodes" in line:
             ret += [item.strip() for item in line.replace("fit failure summary on nodes : ", "").replace("(.*)", "").strip().split(",")]
    return ret


def check_pending_reason(pod, reason):
    reasons = get_pod_pending_detail(pod)
    return any([reason in item for item in reasons])


def get_pod_events(podname):
    url = "%s/api/v1/namespaces/default/events?fieldSelector=involvedObject.name=%s" % (config["apiserver"], podname)
    responseStr = curl_get(url)
    events = json.loads(responseStr)
    return events


def get_pod_unscheduled_reason(podname):
    events = get_pod_events(podname)
    ret = ""
    if "items" in events:
        for event in events["items"]:
            if "reason" in event and event["reason"] == "FailedScheduling":
                ret = event["message"]
    return ret


def get_pod_status(pod):
    podstatus = {}
    if "status" in pod and "conditions" in pod["status"]:
        for condition in pod["status"]["conditions"]:
            try:
                if condition["type"] == "PodScheduled" and condition["status"] == "False" and "reason" in condition:
                    unscheduledReason = get_pod_unscheduled_reason(pod["metadata"]["name"])
                    podstatus["message"] = condition["reason"] + ":" + unscheduledReason
            except Exception as e:
                pass

    if "status" in pod and "containerStatuses" in pod["status"]:
        # assume we only have one container in every pod
        containerStatus = pod["status"]["containerStatuses"][0]
        if "state" in containerStatus and "waiting" in containerStatus["state"]:
            ret = ""
            if "reason" in containerStatus["state"]["waiting"]:
                ret += containerStatus["state"]["waiting"]["reason"]
            if "message" in containerStatus["state"]["waiting"]:
                ret += ":\n" + containerStatus["state"]["waiting"]["message"]
            podstatus["message"] = ret
        elif "state" in containerStatus and "terminated" in containerStatus["state"]:
            ret = ""
            if "reason" in containerStatus["state"]["terminated"]:
                ret += containerStatus["state"]["terminated"]["reason"]
            if "message" in containerStatus["state"]["terminated"]:
                ret += ":\n" + containerStatus["state"]["terminated"]["message"]
            podstatus["message"] = ret
            if "finishedAt" in containerStatus["state"]["terminated"]:
                podstatus["finishedAt"] = pytz.utc.localize(containerStatus["state"]["terminated"]["finishedAt"]).isoformat()

            if "startedAt" in containerStatus["state"]["terminated"]:
                podstatus["startedAt"] = pytz.utc.localize(containerStatus["state"]["terminated"]["startedAt"]).isoformat()
        elif "state" in containerStatus and "running" in containerStatus["state"] and "startedAt" in containerStatus["state"]["running"]:
            podstatus["message"] = "started at: " + pytz.utc.localize(containerStatus["state"]["running"]["startedAt"]).isoformat()
            if "startedAt" in containerStatus["state"]["running"]:
                podstatus["startedAt"] = pytz.utc.localize(containerStatus["state"]["running"]["startedAt"]).isoformat()

        if "finishedAt" not in podstatus:
            podstatus["finishedAt"] = datetime.now(get_localzone()).isoformat()
    if "status" in pod and "podIP" in pod["status"]:
        podstatus["podIP"] = pod["status"]["podIP"]
    if "status" in pod and "hostIP" in pod["status"]:
        podstatus["hostIP"] = pod["status"]["hostIP"]
    return podstatus


def GetJobStatus(jobId):
    podInfo = GetPod("run=" + jobId)
    output = "Unknown"

    if podInfo is None:
        output = "kubectlERR"
    elif "items" in podInfo:
        podStatus = [check_pod_status(pod) for pod in podInfo["items"]]
        #detail = "=====================\n=====================\n=====================\n".join([yaml.dump(pod["status"], default_flow_style=False) for pod in podInfo["items"] if "status" in podInfo["items"]])

        ######!!!!!!!!!!!!!!!!CAUTION!!!!!! since "any and all are used here, the order of if cause is IMPORTANT!!!!!, we need to deail with Faild,Error first, and then "Unknown" then "Pending", at last " Successed and Running"
        if len(podStatus) == 0:
            output = "Pending"
        elif any([status == "Error" for status in podStatus]):
            output = "Failed"
        elif any([status == "Failed" for status in podStatus]):
            output = "Failed"
        elif any([status == "Unknown" for status in podStatus]):
            output = "Unknown"
        elif any([status == "Pending" for status in podStatus]):
            if any([check_pending_reason(pod, "PodFitsHostPorts") for pod in podInfo["items"]]):
                output = "PendingHostPort"
            else:
                output = "Pending"
        # there is a bug: if podStatus is empty, all (**) will be trigered.
        elif all([status == "Succeeded" for status in podStatus]):
            output = "Succeeded"
        elif any([status == "Running" for status in podStatus]):   # as long as there are no "Unknown", "Pending" nor "Error" pods, once we see a running pod, the job should be in running status.
            output = "Running"

        detail = [get_pod_status(pod) for i, pod in enumerate(podInfo["items"])]

    return output, detail


def all_pod_ready(job_id):
    pods = GetPod("run=" + job_id)
    print("\n\n\n--------------------------------------------\n\n")
    print("=======%s" % pods)
    if pods is None:
        return False
    if "items" in pods:
        pod_status = [check_pod_status(pod) for pod in pods["items"]]
        if any([status != "Running" for status in pod_status]):
            return False
    return True


def get_node_labels(key):
    url = "%s/api/v1/nodes" % (config["apiserver"])
    responseStr = curl_get(url)
    nodes = json.loads(responseStr)
    ret = []

    if "items" in nodes:
        for node in nodes["items"]:
            if "metadata" in node and "labels" in node["metadata"]:
                if key in node["metadata"]["labels"]:
                    v = node["metadata"]["labels"][key]
                    if not v in ret:
                        ret.append(v)
    return ret


if __name__ == '__main__':

    #Run()
    print get_node_labels("rack")

    pass
