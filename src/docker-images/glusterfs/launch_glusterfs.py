#!/usr/bin/python 
# launch gluster fs 
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


def create_log( logdir ):
	if not os.path.exists( logdir ):
		os.system("mkdir -p " + logdir )
	curtime = datetime.utcnow()
	fname = os.path.join( logdir, str(curtime) + ".log" )
	
def find_group( config, hostname ):
	glusterfs_groups = config["groups"]
	for group, group_config in glusterfs_groups.iteritems():
		nodes = group_config["nodes"]
		othernodes = []
		in_group = False
		isFirst = True
		for nodename in nodes:
			if nodename.find(hostname) >=0: 
				in_group = True
			else:
				if nodename < hostname:
					isFirst = False
				othernodes.append( nodename )
		if in_group:
			return ( group, group_config, othernodes, isFirst )
	return None
				
def run_command( cmd, sudo = True ):
	if sudo and cmd.find( "sudo" ) < 0:
		cmd = "sudo " + cmd; 
	logging.debug( cmd ) 
	retcode = 0; 
	try:
		output = subprocess.check_output( cmd, stderr=subprocess.STDOUT, shell=True )
	except subprocess.CalledProcessError as e:
		output = "Return code: " + str(e.returncode) + ", output: " + e.output.strip()
		retcode = e.returncode
	return retcode
	
def start_glusterfs( logdir = '/var/log/glusterfs/launch' ):
	create_log( logdir )
	with open('logging.yaml') as f:
		logging_config = yaml.load(f)
		f.close()
		logging.config.dictConfig(logging_config)	
	# set up logging to file - see previous section for more details
	logging.debug ("Mounting local volume of glusterFS ...." )
	cmd = "";	
	with open('glusterfs_config.yaml') as f:
		config = yaml.load(f)
		f.close()
	hostname = socket.gethostname()
	logging.debug( "Hostname: " + hostname )
	groupinfo = find_group( config, hostname ) 
	if groupinfo is None:
		# The current node is not in any glusterFS group, nothing to do. 
		logging.debug( "Configuration: " + str(config) )
		logging.debug( "The current node %s is not in any glusterfs group, the program will exit .... " + hostname )
		return; 
	# Original command in glusterfs docker
	run_command( "/usr/sbin/init" )
	run_command( "systemctl start glusterd.service" )
	run_command( "systemctl status glusterd.service" )
	# Start glusterFS setup 
	group = groupinfo[0]
	group_config = groupinfo[1]
	othernodes = groupinfo[2]
	logging.debug( "Configuration: " + str(config) )
	logging.debug( "The current node %s is in glusterfs group %s, other nodes are %s .... " % ( hostname, group, othernodes) )
	devicename = "/dev/%s/%s" % ( config["volumegroup"], config["volumename"] )
	localvolumename = config["mountpoint"]
	run_command ( "mkdir -p %s " % localvolumename ) 
	run_command ( "mount %s %s " % ( devicename, localvolumename) ) 
	logging.debug ("Start launch glusterfs ...." )		
	group = groupinfo[0]
	group_config = groupinfo[1]
	othernodes = groupinfo[2]
	isFirst = groupinfo[3]
	gluster_volumes = group_config["gluster_volumes"]
	for volume in gluster_volumes:		
		run_command( "mkdir -p " + os.path.join( localvolumename, volume ) )
	someNode = False
	while not someNode:
		for node in othernodes:
			retcode = run_command( "gluster peer probe %s" % node )
			if retcode == 0:
				logging.debug( "Node %s succeed in peer probe ..." % node )
				someNode = True
			else:
				logging.debug( "Node %s failed in peer probe ..." % node )
		if not someNode:
			time.sleep(5)
	for volume in gluster_volumes:
		cmd = "gluster volume create %s " % volume
		volumeinfo = gluster_volumes[volume]
		# replication property 
		cmd += " " + volumeinfo["property"] 
		cmd += " transport " + volumeinfo["transport"] 
		for node in othernodes:
			cmd += " " + node + ":" + os.path.join( localvolumename, volume )
		run_command( cmd ) 	
	time.sleep(5)
	for volume in gluster_volumes:
		run_command( "gluster volume start " + volume )
	glusterfs_mountpoint = config["glusterfs_mountpoint"]
	glusterfs_symlink = config["glusterfs_symlink" ]
	run_command( "mkdir -p " + glusterfs_symlink )
	run_command( "mkdir -p " + glusterfs_mountpoint )
	filename = "WARNING_PLEASE_DO_NOT_WRITE_DIRECTLY_IN_THIS_DIRECTORY_USE_SYM_LINK"
	dirname = "rootdir"
	# Create a warning file to guard against people writing directly in glusterFS mount
	open( os.path.join( glusterfs_mountpoint, filename ), 'a' ).close()
	for volume in gluster_volumes:
		volume_mount = os.path.join( glusterfs_mountpoint, volume ) 
		run_command( "mount -t glusterfs %s:%s %s" % ( hostname, os.path.join( localvolumename, volume ), volume_mount ) )
		if isFirst:
			open( os.path.join( volume_mount, filename ), 'a' ).close()
			run_command( "mkdir -p "+ os.path.join( volume_mount, dirname ) )
		run_command( "ln -s %s %s" % ( os.path.join( volume_mount, dirname ), os.path.join( glusterfs_symlink, volume ) ) )

if __name__ == '__main__':
	parser = argparse.ArgumentParser( prog='launch_glusterfs.py',
		formatter_class=argparse.RawDescriptionHelpFormatter,
		description=textwrap.dedent('''\
Format, manage and deploy a glusterFS cluster.

Prerequest:
This command is expected to be executed on every glusterFS brick node.

Command:
  mkfs [dev] format & mount the glusterFS partition. 
  ''') )
	parser.add_argument("command", 
		help = "See above for the list of valid command" )
	parser.add_argument('nargs', nargs=argparse.REMAINDER, 
		help="Additional command argument", 
		)
	args = parser.parse_args()
	

	start_glusterfs()
	logging.debug( "End launch glusterfs, time ... " )

