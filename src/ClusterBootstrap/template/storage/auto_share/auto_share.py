#!/usr/bin/python 
# Automatic monitoring mount process
import time
import os
from datetime import datetime
import yaml
import logging
import logging.config
import argparse
import textwrap
import socket
import subprocess
import re
import sys

def exec_with_output( cmd ):
	try:
		# https://stackoverflow.com/questions/4814970/subprocess-check-output-doesnt-seem-to-exist-python-2-6-5                
		output = subprocess.Popen( cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT ).communicate()[0]
	except subprocess.CalledProcessError as e:
		print "Exception " + str(e.returncode) + ", output: " + e.output.strip()
		return ""
	return output

def mount_fileshare():
	with open("mounting.yaml", 'r') as datafile:
		config = yaml.load(datafile)
		datafile.close()
#	print config
	allmountpoints = config["mountpoints"]
	for k,v in allmountpoints.iteritems():
		if "curphysicalmountpoint" in v:
			physicalmountpoint = v["curphysicalmountpoint"] 
			output = exec_with_output("sudo mount | grep %s" % v["curphysicalmountpoint"])
			umounts = []
			for line in output.splitlines():
				words = line.split()
				if len(words)>3 and words[1]=="on":
					umounts.append( words[2] )
			umounts.sort()
			# Examine mount point, unmount those file shares that fails. 
			for um in umounts:
				cmd = "sudo umount %s; " % um
				print "To examine mount %s " % um
			if len(umounts) <= 0:
				if v["type"] == "azurefileshare":
					exec_with_output( "sudo mount -t cifs %s %s -o %s" % (v["url"], physicalmountpoint, v["options"] ) )
				elif v["type"] == "glusterfs":
					exec_with_output( "sudo mount -t glusterfs %s:%s %s -o %s" % (v["node"], v["filesharename"], physicalmountpoint, v["options"] ) )
				elif v["type"] == "nfs":
					exec_with_output( "sudo mount %s:%s %s -o %s " % (v["server"], v["filesharename"], physicalmountpoint, v["options"]) )
				elif v["type"] == "hdfs":
					exec_with_output( "sudo hadoop-fuse-dfs dfs://%s %s %s; " % (v["server"], physicalmountpoint, v["options"]) )

def start_logging( logdir = '/var/log/auto_share' ):
	if not os.path.exists( logdir ):
		os.system("sudo mkdir -p " + logdir )
	with open('logging.yaml') as f:
		logging_config = yaml.load(f)
		f.close()
		# print logging_config
		logging.config.dictConfig(logging_config)
	logging.debug (".................... Start auto_share at %s .......................... " % datetime.now() )
	logging.debug ( "Argument : %s" % sys.argv )

if __name__ == '__main__':
	parser = argparse.ArgumentParser( prog='auto_share.py',
		formatter_class=argparse.RawDescriptionHelpFormatter,
		description=textwrap.dedent('''\
Automatically monitor and mount file share. 
  ''') )
	parser.add_argument('nargs', nargs=argparse.REMAINDER, 
		help="Additional command argument", 
		)
	dir_path = os.path.dirname(os.path.realpath(__file__))
	os.chdir(dir_path)
	args = parser.parse_args()
	start_logging()
	mount_fileshare()
	logging.debug( "End auto_share ... " )

