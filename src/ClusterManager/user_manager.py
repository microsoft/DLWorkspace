#!/usr/bin/env python3

import os
import time
import argparse
import sys
import yaml
import random
import logging
import logging.config

sys.path.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../utils"))

from cluster_manager import setup_exporter_thread, manager_iteration_histogram, register_stack_trace_dump, update_file_modification_time
from DataHandler import DataHandler
from config import config

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)


def create_log(logdir='/var/log/dlworkspace'):
    if not os.path.exists(logdir):
        os.system("mkdir -p " + logdir)
    with open('logging.yaml') as f:
        logging_config = yaml.full_load(f)
        f.close()
        logging_config["handlers"]["file"]["filename"] = logdir + \
            "/usermanager.log"
        logging.config.dictConfig(logging_config)


def set_user_directory():
    dataHandler = DataHandler()
    users = dataHandler.GetUsers()
    for username, userid, public_key, private_key in users:
        update_file_modification_time("user_manager")

        if "@" in username:
            username = username.split("@")[0]
        if "/" in username:
            username = username.split("/")[1]
        if "\\" in username:
            username = username.split("\\")[1]
        userpath = os.path.join(config["storage-mount-path"],
                                "work/" + username)
        if not os.path.exists(userpath):
            logger.info("Found a new user %s" % username)
            logger.info("Creating home directory %s for user %s" %
                        (userpath, username))
            os.system("mkdir -p " + userpath)
            os.system("chown -R " + str(userid) + ":" + "500000513 " + userpath)

        ssh_path = os.path.join(userpath, ".ssh")
        if not os.path.exists(ssh_path):
            os.system("mkdir -p " + ssh_path)

        sshkeypath = os.path.join(userpath, ".ssh/id_rsa")
        pubkeypath = os.path.join(userpath, ".ssh/id_rsa.pub")
        authorized_keyspath = os.path.join(userpath, ".ssh/authorized_keys")

        if not os.path.exists(sshkeypath):
            logger.info("Creating sshkey for user %s" % (username))
            with open(sshkeypath, "w") as wf:
                wf.write(private_key)
            with open(pubkeypath, "w") as wf:
                wf.write(public_key)
            os.system("chown -R " + str(userid) + ":" + "500000513 " + userpath)
            # Permission of .ssh has to be 700, otherwise, users cannot access
            # .ssh via Samba file share.
            os.system("chmod 700 " + os.path.dirname(sshkeypath))
            os.system("chmod 600 " + sshkeypath)
            os.system("chmod 600 " + pubkeypath)

        if not os.path.exists(authorized_keyspath):
            logger.info("Creating authorized_keys for user %s" % (username))
            with open(authorized_keyspath, "w") as wf:
                wf.write("\n")
                wf.write(public_key)
            os.system("chown -R " + str(userid) + ":" + "500000513 " +
                      authorized_keyspath)
            os.system("chmod 644 " + authorized_keyspath)


def Run():
    register_stack_trace_dump()
    create_log()
    logger.info("start to update user directory...")

    while True:
        update_file_modification_time("user_manager")

        with manager_iteration_histogram.labels("user_manager").time():
            try:
                set_user_directory()
            except Exception as e:
                logger.exception("set user directory failed")
        time.sleep(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--port",
                        "-p",
                        help="port of exporter",
                        type=int,
                        default=9201)
    args = parser.parse_args()
    setup_exporter_thread(args.port)

    Run()
