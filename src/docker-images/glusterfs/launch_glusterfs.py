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
import re


def create_log( logdir ):
    if not os.path.exists( logdir ):
        os.system("sudo mkdir -p " + logdir )
        # os.system("sudo chmod og+w " + logdir )

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
                curnode = nodename
            else:
                if nodename < hostname:
                    isFirst = False
                othernodes.append( nodename )
        if in_group: 
            othernodes.sort()
            return ( group, group_config, othernodes, curnode, isFirst )
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
    logging.debug( output )
    return (retcode, output)
    
def all_glusterfs_peers( ):
    retcode, output = run_command( "gluster peer status" )
    peers = []
    split_output = output.split()
    isHostnameLast = False
    for word in split_output:
        if isHostnameLast:
            peers.append(word)
        isHostnameLast = ( word == "Hostname:" )
    return peers
    
def start_glusterfs( command, inp, logdir = '/var/log/glusterfs/launch' ):
    create_log( logdir )
    with open('logging.yaml') as f:
        logging_config = yaml.load(f)
        f.close()
        print logging_config
        logging.config.dictConfig(logging_config)
    logging.debug (".................... Start Launch GlusterFS .......................... " )
    logging.debug ("Argument : %s" % inp )
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
    # logging.debug( "sudo /usr/sbin/init" )
    # subprocess.Popen( "/usr/sbin/init" )
    # run_command( "systemctl start glusterd.service" )
    # run_command( "systemctl status glusterd.service" )
    # Start glusterFS setup 
    group = groupinfo[0]
    group_config = groupinfo[1]
    othernodes = groupinfo[2]
    curnode = groupinfo[3]
    isFirst = groupinfo[4]
    leadnode = curnode if isFirst else othernodes[0]
    logging.debug( "Configuration: " + str(config) )
    logging.debug( "The current node %s is in glusterfs group %s, other nodes are %s .... " % ( hostname, group, othernodes) )
    # Mount is now done during glusterfs create stage
    # devicename = "/dev/%s/%s" % ( config["volumegroup"], config["volumename"] )
    localvolumename = config["mountpoint"]
    # run_command ( "mkdir -p %s " % localvolumename ) 
    # run_command ( "mount %s %s " % ( devicename, localvolumename) ) 
    if command == "detach":
        peers = all_glusterfs_peers()
        for peer in peers:
            run_command( "gluster peer detach %s" % peer )
        exit()
    elif command == "stop":
        logging.debug( "Stop further execution ..... "  )
        exit()
    logging.debug ("Start launch glusterfs ...." )

    gluster_volumes = group_config["gluster_volumes"]
    min_tolerance = len(othernodes)
    for volume, volume_config in gluster_volumes.iteritems():
        if volume_config["tolerance"] < min_tolerance:
            min_tolerance = volume_config["tolerance"]

    bRun = ( command =="start" or command=="format" or command=="run")
    bStart = ( command =="start" or command=="format" )
    bFormat = ( command=="format" )

    # during start, 
    if bRun and isFirst:
        connected_nodes = {} 
        retries = 1000
        while len(connected_nodes)<len(othernodes) and retries >0:
            retries -= 1
            for node in othernodes:
                if not node in connected_nodes:
                    retcode, output = run_command( "gluster peer probe %s" % node )
                    if retcode == 0:
                        logging.debug( "Node %s succeed in peer probe ..." % node )
                        connected_nodes[node] = True
                    else:
                        logging.debug( "Node %s failed in peer probe, wait for it to come alive ..." % node )
            if len(connected_nodes)<len(othernodes):
                time.sleep(1) 

    livenodes = 0
    logging.debug( "Min failure tolerance is %d, wait for at least %d nodes in the group to come alive " % (min_tolerance, len(othernodes) - min_tolerance + 1) )
    while livenodes < len(othernodes) - min_tolerance:
        peers = all_glusterfs_peers()
        npeers = len(peers)
        livenodes = npeers + 1
        logging.debug( "Number of nodes alive is %d, %s ..." % (livenodes, str(peers)) )
        if livenodes < len(othernodes) - min_tolerance:
            time.sleep(1)

    
    
    if bStart and isFirst:
        for volume, volume_config in gluster_volumes.iteritems():
            multiple = volume_config["multiple"]
            numnodes = len(othernodes) + 1
            # Find the number of subvolume needed. 
            subvolumes = 1
            while ( numnodes * subvolumes ) % multiple !=0:
                subvolumes +=1; 
            # Volume has already been created 
            # logging.debug( "Volume %s, multiple is %d, # of nodes = %d, make %d volumes ..." % (volume, multiple, numnodes, subvolumes) )
            # for sub in range(1, subvolumes + 1 ):
            #    run_command( "mkdir -p " + os.path.join( localvolumename, volume ) + str(sub) )
            if bFormat:
                cmd = "gluster --mode=script volume stop %s force; " % volume
                run_command( cmd )
                cmd = "gluster --mode=script volume delete %s; " % volume
                run_command( cmd )
            cmd = "gluster volume create %s " % volume
            volumeinfo = gluster_volumes[volume]
            # replication property 
            cmd += " " + volumeinfo["property"] 
            cmd += " transport " + volumeinfo["transport"]
            allnodes = [ curnode ] + othernodes
            for sub in range(1, subvolumes + 1 ):
                for node in allnodes:
                    cmd += " " + node + ":" + os.path.join( localvolumename, volume ) + str(sub)
            cmd += " force; "
            run_command( cmd )     
        for volume in gluster_volumes:
            run_command( "gluster volume set %s nfs.disable off" % volume )
            run_command( "gluster volume start " + volume )
        glusterfs_mountpoint = config["glusterfs_mountpoint"]
        # glusterfs_symlink = config["glusterfs_symlink" ]
        # run_command( "mkdir -p " + glusterfs_symlink )
        run_command( "mkdir -p " + glusterfs_mountpoint )
        filename = "WARNING_PLEASE_DO_NOT_WRITE_DIRECTLY_IN_THIS_DIRECTORY"
        # Create a warning file to guard against people writing directly in glusterFS mount
        open( os.path.join( glusterfs_mountpoint, filename ), 'a' ).close()
        
    if bRun:
        glusterfs_mountpoint = config["glusterfs_mountpoint"]
        for volume in gluster_volumes:
            run_command( "gluster volume set %s nfs.disable off" % volume )
            run_command( "gluster volume start " + volume )
            volume_mount = os.path.join( glusterfs_mountpoint, volume ) 
            run_command( "sudo mkdir -p %s" % volume_mount ) 
            run_command( "sudo umount %s " % volume_mount ) 
            run_command( "mount -t glusterfs %s:%s %s" % ( leadnode, volume, volume_mount ) )
            #dirname = "rootdir"
            #if isFirst:
            #    run_command( "mkdir -p "+ os.path.join( volume_mount, dirname ) )
            # run_command( "ln -s %s %s" % ( os.path.join( volume_mount, dirname ), os.path.join( glusterfs_symlink, volume ) ) )

if __name__ == '__main__':
    os.chdir("/opt/glusterfs")
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
    default_input = "stop"
    if os.path.exists("./argument"):
        default_input = os.listdir("./argument")[0]
    # Obtain argument from environment variable. 
    inp = default_input 
    if len(inp)==0:
        inp = default_input 
    args = parser.parse_args(inp.split("_"))
    
    start_glusterfs(args.command, inp )
    logging.debug( "End launch glusterfs, time ... " )
    while True:
        logging.debug( "Sleep 5 ... " )
        time.sleep(5)

