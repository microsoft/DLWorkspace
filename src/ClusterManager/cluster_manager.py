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
import random

import textwrap
import logging
import logging.config

import job_manager
import user_manager
import node_manager
import joblog_manager
import command_manager
import endpoint_manager

from multiprocessing import Process, Manager


def create_log(logdir='/var/log/dlworkspace'):
    if not os.path.exists(logdir):
        os.system("mkdir -p " + logdir)
    with open('logging.yaml') as f:
        logging_config = yaml.load(f)
        f.close()
        logging_config["handlers"]["file"]["filename"] = logdir+"/clustermanager.log"
        logging.config.dictConfig(logging_config)


def Run():
    create_log()

    logging.info("Starting job manager... ")
    proc_job = Process(target=job_manager.Run)
    proc_job.start()

    logging.info("Starting user manager... ")
    proc_user = Process(target=user_manager.Run)
    proc_user.start()

    logging.info("Starting node manager... ")
    proc_node = Process(target=node_manager.Run)
    proc_node.start()

    logging.info("Starting joblogging manager... ")
    proc_joblog = Process(target=joblog_manager.Run)
    proc_joblog.start()

    logging.info("Starting command manager... ")
    proc_command = Process(target=command_manager.Run)
    proc_command.start()

    logging.info("Starting endpoint manager... ")
    proc_endpoint = Process(target=endpoint_manager.Run)
    proc_endpoint.start()

    proc_job.join()
    proc_user.join()
    proc_node.join()
    proc_joblog.join()
    proc_command.join()
    proc_endpoint.join()
    pass


if __name__ == '__main__':

    #parser = argparse.ArgumentParser( prog='cluster_manager.py',
    #    formatter_class=argparse.RawDescriptionHelpFormatter,
    #    description=textwrap.dedent('''\
 # ''') )
    #parser.add_argument("help",
    #    help = "Show the usage of this program" )

    #args = parser.parse_args()

    Run()
