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
from osUtils import mkdirsAsUser
from config import config, GetStoragePath
from DataHandler import DataHandler


def create_log( logdir = '/var/log/dlworkspace' ):
    if not os.path.exists( logdir ):
        os.system("mkdir -p " + logdir )
    with open('logging.yaml') as f:
        logging_config = yaml.load(f)
        f.close()
        logging_config["handlers"]["file"]["filename"] = logdir+"/joblogmanager.log"
        logging.config.dictConfig(logging_config)



def extract_job_log(jobId,logPath,userId):
    try:
        dataHandler = DataHandler()

        logs = k8sUtils.GetLog(jobId)
    
        jobLogDir = os.path.dirname(logPath)
        if not os.path.exists(jobLogDir):
            mkdirsAsUser(jobLogDir,userId)
        logStr = ""
        trimlogstr = ""


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


                trimlogstr += "=========================================================\n"
                trimlogstr += "=========================================================\n"
                trimlogstr += "=========================================================\n"
                trimlogstr += "        logs from pod: %s\n" % log["podName"]
                trimlogstr += "=========================================================\n"
                trimlogstr += "=========================================================\n"
                trimlogstr += "=========================================================\n"
                logLines = log["containerLog"].split('\n')
                if (len(logLines) < 3000):
                    trimlogstr += log["containerLog"]
                    trimlogstr += "\n\n\n"
                    trimlogstr += "=========================================================\n"
                    trimlogstr += "        end of logs from pod: %s\n" % log["podName"] 
                    trimlogstr += "=========================================================\n"
                    trimlogstr += "\n\n\n"
                else:
                    trimlogstr += "\n".join(logLines[-2000:])
                    trimlogstr += "\n\n\n"
                    trimlogstr += "=========================================================\n"
                    trimlogstr += "        end of logs from pod: %s\n" % log["podName"] 
                    trimlogstr += "        Note: the log is too long to display in the webpage.\n"
                    trimlogstr += "        Only the last 2000 lines are shown here.\n"
                    trimlogstr += "        Please check the log file (in Job Folder) for the full logs.\n"
                    trimlogstr += "=========================================================\n"
                    trimlogstr += "\n\n\n"

                try:
                    containerLogPath = os.path.join(jobLogDir,"log-container-" + log["containerID"] + ".txt")
                    with open(containerLogPath, 'w') as f:
                        f.write(log["containerLog"])
                    f.close()
                    os.system("chown -R %s %s" % (userId, containerLogPath))
                except Exception as e:
                    print e


        if len(trimlogstr.strip()) > 0:
            dataHandler.UpdateJobTextField(jobId,"jobLog",base64.b64encode(trimlogstr))
            with open(logPath, 'w') as f:
                f.write(logStr)
            f.close()
            os.system("chown -R %s %s" % (userId, logPath))

    except Exception as e:
        logging.error(e)



def update_job_logs():
    while True:
        try:
            dataHandler = DataHandler()
            pendingJobs = dataHandler.GetPendingJobs()
            for job in pendingJobs:
                try:
                    if job["jobStatus"] == "running" :
                        logging.info("updating job logs for job %s" % job["jobId"])
                        jobParams = json.loads(base64.b64decode(job["jobParams"]))
                        jobPath,workPath,dataPath = GetStoragePath(jobParams["jobPath"],jobParams["workPath"],jobParams["dataPath"])
                        localJobPath = os.path.join(config["storage-mount-path"],jobPath)
                        logPath = os.path.join(localJobPath,"logs/joblog.txt")

                        extract_job_log(job["jobId"],logPath,jobParams["userId"])
                except Exception as e:
                    logging.error(e)
        except Exception as e:
            logging.error(e)

        time.sleep(1)



def Run():
    create_log()
    logging.info("start to update job logs ...")

    while True:
        try:
            update_job_logs()
        except Exception as e:
            print e
        time.sleep(1)

if __name__ == '__main__':
    Run()