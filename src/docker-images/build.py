import os
import time
import datetime
import argparse
import uuid
import subprocess
import sys
sys.path.append("../utils")
from DockerUtils import buildDocker, runDocker

# prefix and tag will be filled by argument parser.
dockerprefix = ""
dockertag = ""

def buildAllDockers(rootdir):
	fnames = os.listdir(rootdir)
	for fname in fnames:
		entry = os.path.join(rootdir, fname )
		if os.path.isdir(entry):
			dockername = dockerprefix + os.path.basename(entry)+":"+dockertag
			buildDocker(dockername, entry)

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description = "Build all dockers of DL Workspace")
	parser.add_argument("-p", "--prefix", 
		help="Prefix of the docker name, or [dlws-]", 
		action="store", 
		default="dlws-" )
	parser.add_argument("-t", "--tag", 
		help="Tag of the docker build, or [default]", 
		action = "store", 
		default = "latest" )
	args = parser.parse_args()
	dockerprefix = args.prefix
	dockertag = args.tag
	# print "Docker prefix : " + dockerprefix
	# print "Docker tag : " + dockertag
	if True:
		buildAllDockers(".")
