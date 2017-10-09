#!/usr/bin/python 
# Automatic monitoring mount process
# The program will run as root, as service started by systemd
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
import getpass

def pipe_with_output( cmd1, cmd2, verbose=False ):
	try:
		# https://stackoverflow.com/questions/4814970/subprocess-check-output-doesnt-seem-to-exist-python-2-6-5                
		if verbose:
			logging.debug ( "Pipe: %s | %s " % (cmd1, cmd2 ) )
		p1 = subprocess.Popen( cmd1.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE )
		p2 = subprocess.Popen( cmd2.split(), stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
		output = p2.communicate()[0]
		if verbose:
			logging.debug ( output )
	except subprocess.CalledProcessError as e:
		print "Exception " + str(e.returncode) + ", output: " + e.output.strip()
		if verbose: 
			logging.debug ( "Exception: %s, output: %s" % (str(e.returncode), e.output.strip()) )
		return ""
	return output

def exec_with_output( cmd, verbose=False, max_run=30 ):
	try:
		# https://stackoverflow.com/questions/4814970/subprocess-check-output-doesnt-seem-to-exist-python-2-6-5                
		cmds = cmd.split()
		if verbose:
			logging.debug ( "Execute: %s" % cmd )
		sp = subprocess.Popen( cmds, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True )
		output, err = sp.communicate()
		count = 0
		while sp.poll() == None and count < max_run:
			time.sleep(1)
			count += 1
		if verbose:
			logging.debug ( "Return: %d, Output: %s, Error: %s" % (sp.returncode, output, err) )
		return (sp.returncode, output, err)
	except subprocess.CalledProcessError as e:
		print "Exception " + str(e.returncode) + ", output: " + e.output.strip()
		if verbose: 
			logging.debug ( "Exception: %s, output: %s" % (str(e.returncode), e.output.strip()) )
		return (e.returncode, e.output, "Error")

def exec_wo_output( cmd, verbose=False ):
	try:
		# https://stackoverflow.com/questions/4814970/subprocess-check-output-doesnt-seem-to-exist-python-2-6-5                
		if verbose:
			logging.debug ( "Execute: %s" % cmd )
		os.system( cmd )
	except subprocess.CalledProcessError as e:
		print "Exception " + str(e.returncode) + ", output: " + e.output.strip()

def mount_one_hdfs( v, physicalmountpoint, server, verbose=True):
	exec_with_output( "hadoop-fuse-dfs hdfs://%s %s %s " % (server, physicalmountpoint, v["options"]), verbose=verbose )

def test_one_hdfs( server, verbose=True):
	(retcode, output, err) = exec_with_output("hdfs dfs -test -e hdfs://%s" % server, verbose=verbose)
	if err.find("not supported in state standy")>=0:
		# standby namenode
		logging.debug ( "HDFS namenode %s is standby namenode" % server )
		return False
	elif err.find("Connection refused")>=0:
		logging.debug ( "HDFS namenode %s fails" % server )
		return False
	elif err.find("Incomplete HDFS URI")>=0:
		logging.debug ( "Wrongly formatted namenode %s: fails" % server )
		return False
	else:
		logging.debug ( "HDFS namenode %s is active" % server )
		return True

# Mount HDFS, with support of high availablability
def mount_hdfs( v, physicalmountpoint, verbose=True ):
	if len(v["server"])==0:
		# No HDFS server specified, unable to mount
		return False
	elif len(v["server"])==1:
		mount_one_hdfs( v, physicalmountpoint, v["server"][0], verbose=verbose)
		return True
	else:
		for server in v["server"]:
			if test_one_hdfs(server, verbose):
				mount_one_hdfs( v, physicalmountpoint, server, verbose=verbose)
				return True

def mount_fileshare(verbose=True):
	with open("mounting.yaml", 'r') as datafile:
		config = yaml.load(datafile)
		datafile.close()
#	print config
	allmountpoints = config["mountpoints"]
	nMounts = 0
	for k,v in allmountpoints.iteritems():
		if "curphysicalmountpoint" in v:
			physicalmountpoint = v["curphysicalmountpoint"] 
			output = pipe_with_output("mount", "grep %s" % v["curphysicalmountpoint"], verbose=False)
			umounts = []
			existmounts = []
			for line in output.splitlines():
				words = line.split()
				if len(words)>3 and words[1]=="on":
					if verbose:
						logging.debug( "%s on %s" % (words[0], words[2]) )
					# check if mount point exists, automatic create directory if non exist
					bMount = False
					for mountpoint in v["mountpoints"]:
						try:
							targetdir = os.path.join(physicalmountpoint, mountpoint)
							if os.path.exists( targetdir ):
								bMount = True
							else:
								try:
									os.system("mkdir -m 0777 "+targetdir)
								except:
									logging.debug( "Failed to create directory " + targetdir )
								if os.path.exists( targetdir ):
									bMount = True
						except:
							logging.debug( "Failed to check for existence of directory " + targetdir )
					if not bMount:
						# Failing
						umounts.append( words[2] )
					else:
						existmounts.append( words[2])
			umounts.sort()
			# Examine mount point, unmount those file shares that fails. 
			for um in umounts:
				cmd = "umount -l %s" % um
				logging.debug( "Mount fails, to examine mount %s " % um )				
				exec_with_output( cmd, verbose=verbose )
				time.sleep(1)
			if len(existmounts) <= 0:
				nMounts += 1
				if v["type"] == "azurefileshare":
					exec_with_output( "mount -t cifs %s %s -o %s " % (v["url"], physicalmountpoint, v["options"] ), verbose=verbose )
				elif v["type"] == "glusterfs":
					exec_with_output( "mount -t glusterfs -o %s %s:%s %s " % (v["options"], v["node"], v["filesharename"], physicalmountpoint ), verbose=verbose )
				elif v["type"] == "nfs":
					exec_with_output( "mount %s:%s %s -o %s " % (v["server"], v["filesharename"], physicalmountpoint, v["options"]), verbose=verbose )
				elif v["type"] == "hdfs":
					mount_hdfs( v, physicalmountpoint, verbose=verbose )
				elif v["type"] == "local" or v["type"] == "localHDD":
					exec_with_output( "mount %s %s " % ( v["device"], physicalmountpoint ), verbose=verbose )
				else:
					nMounts -= 1
	if nMounts > 0:
		time.sleep(1)

def start_logging( logdir = '/var/log/auto_share' ):
	if not os.path.exists( logdir ):
		os.system("mkdir -p " + logdir )
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
	logging.debug( "Run as user %s" % getpass.getuser() )
	lockfile = os.path.join(dir_path, "lock")
	try:
		lockfd = os.open( lockfile, os.O_CREAT | os.O_WRONLY | os.O_EXCL )
		try:
			mount_fileshare()
		except:
			logging.debug( "Exception when mounting files... "  )	
		else:
			logging.debug( "Examined all mounting points... "  )	
		os.close( lockfd )
		os.remove( lockfile )
		logging.debug( "Remove lock ... " )
	except OSError:
		logging.debug( "Lock file %s exist, another autho_share still running? Do nothing. " %lockfile )	
	
	logging.debug( "End auto_share ... " )

