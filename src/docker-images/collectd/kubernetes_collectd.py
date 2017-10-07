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
            rsset = json.loads(curl_get("https://127.0.0.1/apis/extensions/v1beta1/replicasets"))

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

            rsset = json.loads(curl_get("https://127.0.0.1/apis/extensions/v1/ReplicationController"))

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


            dpset = json.loads(curl_get("https://127.0.0.1/apis/extensions/v1beta1/daemonsets"))
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
            pass
collectd.register_config(configure)
collectd.register_read(read)
