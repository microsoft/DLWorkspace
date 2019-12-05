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
from JobLogUtils import GetJobLog

from cluster_manager import setup_exporter_thread, manager_iteration_histogram, register_stack_trace_dump, update_file_modification_time, record

logger = logging.getLogger(__name__)

def create_log(logdir = '/var/log/dlworkspace'):
    if not os.path.exists( logdir ):
        os.system("mkdir -p " + logdir)
    with open('logging.yaml') as f:
        logging_config = yaml.load(f)
        f.close()
        logging_config["handlers"]["file"]["filename"] = logdir+"/joblogmanager.log"
        logging.config.dictConfig(logging_config)



@record
def extract_job_log(jobId,logPath,userId):
    try:
        dataHandler = DataHandler()

        old_cursor_text = dataHandler.GetJobTextField(jobId, "jobLog")
        if old_cursor_text is not None and old_cursor_text.startswith("$$cursor: "):
            old_cursor = old_cursor_text[10:]
        else:
            old_cursor = None
        (log, new_cursor) = GetJobLog(jobId, cursor=old_cursor)

        jobLogDir = os.path.dirname(logPath)
        if not os.path.exists(jobLogDir):
            mkdirsAsUser(jobLogDir,userId)

        for (podName, log_text) in log.items():
            try:
                podLogPath = os.path.join(jobLogDir, "log-pod-" + podName + ".txt")
                with open(podLogPath, 'a') as f:
                    f.write(log_text)
                os.system("chown -R %s %s" % (userId, podLogPath))
            except Exception as e:
                logger.exception("write container log failed")

        logging.info("cursor of job %s: %s" % (jobId, new_cursor))
        if new_cursor is not None:
            dataHandler.UpdateJobTextField(jobId, "jobLog", "$$cursor: %d" % (new_cursor,))

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
    register_stack_trace_dump()
    create_log()
    logging.info("start to update job logs ...")

    while True:
        update_file_modification_time("joblog_manager")

        with manager_iteration_histogram.labels("joblog_manager").time():
            try:
                update_job_logs()
            except Exception as e:
                logger.exception("update job logs failed")
        time.sleep(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", "-p", help="port of exporter", type=int, default=9203)
    args = parser.parse_args()
    setup_exporter_thread(args.port)

    Run()
