#!/usr/bin/python 
import os
import time
import datetime
import argparse
import uuid
import subprocess
import sys
sys.path.append("../utils")
sys.path.append("../../../utils")
from DockerUtils import build_docker, build_dockers

# prefix and tag will be filled by argument parser.
dockerprefix = ""
dockertag = ""

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = "Build one or more dockers of DL Workspace")
    parser.add_argument("-p", "--prefix", 
        help="Prefix of the docker name, or [dlws-]", 
        action="store", 
        default="dlws-" )
    parser.add_argument("-t", "--tag", 
        help="Tag of the docker build, or [default]", 
        action = "store", 
        default = "latest" )
    parser.add_argument('nargs', nargs=argparse.REMAINDER, 
        help="Additional command argument", 
        )
    args = parser.parse_args()
    dockerprefix = args.prefix
    dockertag = args.tag
    # print "Docker prefix : " + dockerprefix
    # print "Docker tag : " + dockertag
    print "Please use ./deploy.py docker build <> to build images"
    if False:
        build_dockers(".", dockerprefix, dockertag, args.nargs )
