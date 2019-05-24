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
        logging_config["handlers"]["file"]["filename"] = logdir+"/usermanager.log"
        logging.config.dictConfig(logging_config)


def set_user_directory():
    dataHandler = DataHandler()
    users = dataHandler.GetUsers()
    for username,userid in users:
        if "@" in username:
            username = username.split("@")[0]
        if "/" in username:
            username = username.split("/")[1]
        if "\\" in username:
            username = username.split("\\")[1]    
        userpath = os.path.join(config["storage-mount-path"],"work/"+username)
        if not os.path.exists(userpath):
            logging.info("Found a new user %s" %username)
            logging.info("Creating home directory %s for user %s" % (userpath, username))
            os.system("mkdir -p "+userpath)
            os.system("chown -R "+str(userid)+":"+"500000513 "+userpath)

        sshkeypath = os.path.join(userpath,".ssh/id_rsa")
        pubkeypath = os.path.join(userpath,".ssh/id_rsa.pub")
        authorized_keyspath = os.path.join(userpath,".ssh/authorized_keys")
        if not os.path.exists(sshkeypath):
            logging.info("Creating sshkey for user %s" % (username))
            os.system("mkdir -p "+os.path.dirname(sshkeypath))
            os.system("ssh-keygen -t rsa -b 4096 -f %s -P ''" % sshkeypath)
            os.system("chown -R "+str(userid)+":"+"500000513 "+userpath)
            os.system("chmod 700 -R "+os.path.dirname(sshkeypath))

        if not os.path.exists(authorized_keyspath):
            logging.info("Creating authorized_keys for user %s" % (username))
            os.system("chown -R "+str(userid)+":"+"500000513 "+authorized_keyspath)
            os.system("cat "+pubkeypath+" >> "+authorized_keyspath)
            os.system("chmod 644 "+authorized_keyspath)

def Run():
    create_log()
    logging.info("start to update user directory...")
    while True:
        try:
            set_user_directory()
        except Exception as e:
            print e
        time.sleep(1)


if __name__ == '__main__':
    Run()
