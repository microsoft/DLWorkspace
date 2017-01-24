import os
import time
import datetime
import argparse
import uuid
import subprocess
import sys

# prefix and tag will be filled by argument parser.
dockerprefix = ""
dockertag = ""

class cd:
    """Context manager for changing the current working directory"""
    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)

def buildDocker(dirname):
	dockername = dockerprefix+os.path.basename(dirname)+":"+dockertag
	print "Building docker ... " + dockername + " @" + dirname
	with cd(dirname):
		os.system("docker build -t "+ dockername + " .")

def buildAllDockers(rootdir):
	fnames = os.listdir(rootdir)
	for fname in fnames:
		entry = os.path.join(rootdir, fname )
		if os.path.isdir(entry):
			buildDocker(entry)

def printUsage():
	print "Usage: python build.py"
	print "  Build all docker images. "
	print ""

	print "Prerequest:"
	print "  * Docker engine and python is installed. "
	print ""

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
