#!/usr/bin/python
import os
import time
import datetime
import argparse
import uuid
import subprocess
import sys
import tempfile
import getpass
import pwd
import grp
from os.path import expanduser
sys.path.append("src/utils")
from DockerUtils import run_docker, build_docker

# prefix and tag will be filled by argument parser.

dirname = "devenv"

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = "Run a docker for development of DL workspace")
    parser.add_argument("-p", "--prefix", 
        help="Prefix of the docker name, or [dev]", 
        action="store", 
        default="dev" )
    parser.add_argument("-t", "--tag", 
        help="Tag of the docker build, or [current]", 
        action = "store", 
        default = "latest" )
    parser.add_argument("--nocache", 
        help="Tag of the docker build, or [current]", 
        action = "store_true")
    args = parser.parse_args()
    dockerprefix = args.prefix
    dockertag = args.tag
    dockername = dockerprefix + ":" + dockertag
    #print args.nocache
    dockername = build_docker(dockername, dirname, nocache = args.nocache)
    run_docker(dockername, "DevDocker")
