#!/usr/bin/env python

import collectd

import json
import os
import subprocess
import sys


import yaml

import re

import pycurl
from StringIO import StringIO
import traceback

def curl_get(url):
    curl = pycurl.Curl()
    curl.setopt(pycurl.URL, url)
    curl.setopt(pycurl.SSL_VERIFYPEER, 1)
    curl.setopt(pycurl.SSL_VERIFYHOST, 0)
    curl.setopt(pycurl.CAINFO, "/etc/kubernetes/ssl/ca.pem")
    curl.setopt(pycurl.SSLKEYTYPE, "PEM")
    curl.setopt(pycurl.SSLKEY, "/etc/kubernetes/ssl/apiserver-key.pem")
    curl.setopt(pycurl.SSLCERTTYPE, "PEM")
    curl.setopt(pycurl.SSLCERT, "/etc/kubernetes/ssl/apiserver.pem")
    curl.setopt(curl.FOLLOWLOCATION, True)
    buff = StringIO()
    curl.setopt(pycurl.WRITEFUNCTION, buff.write)
    curl.perform()
    responseStr = buff.getvalue()
    curl.close()
    return responseStr



def configure(conf):
        collectd.info('Configured with')


def read(data=None):
        vl = collectd.Values(type='gauge')
        vl.plugin = 'kubernetes'
        try:
            rsset = json.loads(curl_get(os.environ['K8SAPI']+"/apis/apps/v1/replicasets"))

            if "items" in rsset:
                for rs in rsset["items"]:
                    if "metadata" in rs and "name" in rs["metadata"] and "status" in rs:
                            vl.plugin_instance = rs["metadata"]["name"]

                            if "availableReplicas" in rs["status"]:
                                numberAvailable = float(rs["status"]["availableReplicas"])
                            else:
                                numberAvailable = 0

                            if "replicas" in rs["status"]:
                                desiredNumber = float(rs["status"]["replicas"])
                            else:
                                desiredNumber = 0

                            if "readyReplicas" in rs["status"]:
                                readyNumber = float(rs["status"]["readyReplicas"])
                            else:
                                readyNumber = 0

                            collectd.info('kubernetes plugin: replicaset "%s" with values: %f %f %f' % (rs["metadata"]["name"],desiredNumber,numberAvailable,readyNumber))
                            if desiredNumber > 0 and desiredNumber == readyNumber and desiredNumber == numberAvailable:
                                res = 0
                            else:
                                res = 1
                            vl.dispatch(values=[float(res)])

            rsset = json.loads(curl_get(os.environ['K8SAPI']+"/apis/extensions/v1/ReplicationController"))

            if "items" in rsset:
                for rs in rsset["items"]:
                    if "metadata" in rs and "name" in rs["metadata"] and "status" in rs:
                            vl.plugin_instance = rs["metadata"]["name"]

                            if "availableReplicas" in rs["status"]:
                                numberAvailable = float(rs["status"]["availableReplicas"])
                            else:
                                numberAvailable = 0

                            if "replicas" in rs["status"]:
                                desiredNumber = float(rs["status"]["replicas"])
                            else:
                                desiredNumber = 0

                            if "readyReplicas" in rs["status"]:
                                readyNumber = float(rs["status"]["readyReplicas"])
                            else:
                                readyNumber = 0

                            collectd.info('kubernetes plugin: ReplicationController "%s" with values: %f %f %f' % (rs["metadata"]["name"],desiredNumber,numberAvailable,readyNumber))
                        
                            if desiredNumber > 0 and desiredNumber == readyNumber and desiredNumber == numberAvailable:
                                res = 0
                            else:
                                res = 1
                            vl.dispatch(values=[float(res)])


            dpset = json.loads(curl_get(os.environ['K8SAPI']+"/apis/apps/v1/daemonsets"))
            if "items" in dpset:
                for dp in dpset["items"]:
                    if "metadata" in dp and "name" in dp["metadata"] and "status" in dp:
                            vl.plugin_instance = dp["metadata"]["name"]
                            if "numberAvailable" in dp["status"]:
                                numberAvailable = float(dp["status"]["numberAvailable"])
                            else:
                                numberAvailable = 0

                            if "desiredNumberScheduled" in dp["status"]:
                                desiredNumber = float(dp["status"]["desiredNumberScheduled"])
                            else:
                                desiredNumber = 0

                            if "numberReady" in dp["status"]:
                                readyNumber = float(dp["status"]["numberReady"])
                            else:
                                readyNumber = 0

                            collectd.info('kubernetes plugin: deployment "%s" with values: %f %f %f' % (dp["metadata"]["name"],desiredNumber,numberAvailable,readyNumber))
                        
                            if desiredNumber > 0 and desiredNumber == readyNumber and desiredNumber == numberAvailable:
                                res = 0
                            else:
                                res = 1
                            vl.dispatch(values=[float(res)])

        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print "*** print_tb:"
            traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
            print "*** print_exception:"
            traceback.print_exception(exc_type, exc_value, exc_traceback,
                                      limit=2, file=sys.stdout)
            print "*** print_exc:"
            traceback.print_exc()

        try:
            used_gpus = 0
            pods = json.loads( curl_get(os.environ['K8SAPI']+"/api/v1/pods"))
            if "items" in pods:
                for item in pods["items"]:
                    if "spec" in item and "containers" in item["spec"]:
                        if "status" in item and "phase" in item["status"] and item["status"]["phase"] == "Running":
                            for container in item["spec"]["containers"]:
                                if "resources" in container and "requests" in container["resources"] and "nvidia.com/gpu" in container["resources"]["requests"]:
                                    used_gpus += int(container["resources"]["requests"]["nvidia.com/gpu"])
            vl = collectd.Values(type='gauge')
            vl.plugin = 'gpu'
            vl.plugin_instance = "usedgpu"
            vl.dispatch(values=[float(used_gpus)])
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print "*** print_tb:"
            traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
            print "*** print_exception:"
            traceback.print_exception(exc_type, exc_value, exc_traceback,
                                      limit=2, file=sys.stdout)
            print "*** print_exc:"
            traceback.print_exc()

        try:
            total_gpus = 0
            nodes = json.loads( curl_get(os.environ['K8SAPI']+"/api/v1/nodes"))
            if "items" in nodes:
                for item in nodes["items"]:
                    if "status" in item and "capacity" in item["status"] and "nvidia.com/gpu" in item["status"]["capacity"]:
                        total_gpus += int(item["status"]["capacity"]["nvidia.com/gpu"])
            vl = collectd.Values(type='gauge')
            vl.plugin = 'gpu'
            vl.plugin_instance = "totalgpu"
            vl.dispatch(values=[float(total_gpus)])

        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print "*** print_tb:"
            traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
            print "*** print_exception:"
            traceback.print_exception(exc_type, exc_value, exc_traceback,
                                      limit=2, file=sys.stdout)
            print "*** print_exc:"
            traceback.print_exc()

collectd.register_config(configure)
collectd.register_read(read)
