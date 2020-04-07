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
import copy

def istrue( config, arg, default=False):
    if arg in config:
        val = config[arg]
        if isinstance( val, bool):
            return val
        elif isinstance( val, basestring):
            return val.lower()[0] == 'y'
        else:
            return val
    else:
        return default        

def tolist( server ):
    if isinstance( server, basestring):
        return [server]
    else:
        return server

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


def confirm_mounted(mount_status_line, target_path, umounts, existmounts, verbose=True):
    words = mount_status_line.split()
    if len(words)>3 and words[1]=="on" and words[2] == target_path:
        if verbose:
            logging.debug( "%s on %s" % (words[0], words[2]) )
        # check if mount point exists, automatic create directory if non exist
        bMount = False
        if os.path.exists(target_path):
            bMount = True
        else:
            try:
                os.system("mkdir -m 0777 " + target_path)
            except:
                logging.debug("Failed to create directory " + target_path)
            if os.path.exists(target_path):
                bMount = True
        if not bMount:
            umounts.append(words[2])
        else:
            existmounts.append(words[2])
    return umounts, existmounts


def mount_fileshare(verbose=True):
    with open("mounting.yaml", 'r') as datafile:
        config = yaml.load(datafile)
        datafile.close()
    nMounts = 0
    for mnt_itm in config.values():
        # gives mounted information only, would not write anything or carry out mount action
        for triplet in mnt_itm["fileshares"]:
            output = pipe_with_output("mount", "grep {}".format(triplet["remote_mount_path"]), verbose=False)
            umounts, existmounts = [], []
            # we would have only 1 line, since we now mount at leaf-path level
            for line in output.splitlines():
                umounts, existmounts = confirm_mounted(line, triplet["remote_mount_path"], umounts, existmounts, verbose)
            umounts.sort()
            # Examine mount point, unmount those file shares that fails. 
            for um in umounts:
                cmd = "umount -v %s" % um
                logging.debug( "Mount fails, to examine mount %s " % um )                
                exec_with_output(cmd, verbose=verbose)
                time.sleep(3)
            if len(existmounts) <= 0:
                nMounts += 1
                exec_with_output("mount {}:{} {} -o {} ".format(mnt_itm["private_ip"],
                    triplet["nfs_local_path"], triplet["remote_mount_path"], mnt_itm["options"]), verbose=verbose)
    if nMounts > 0:
        time.sleep(1)

def link_fileshare():
    with open("mounting.yaml", 'r') as datafile:
        config = yaml.load(datafile)
        datafile.close()
    (retcode, output, err) = exec_with_output("sudo mount")
    for mnt_itm in config.values():
        for triplet in mnt_itm["fileshares"]:
            if output.find(triplet["remote_mount_path"]) < 0:
                logging.debug("!!!Warning!!! {} has not been mounted at {} ".format(triplet["nfs_local_path"], triplet["remote_mount_path"]))
                logging.debug(output)
                continue
            if not os.path.exists(triplet["remote_link_path"]):
                exec_wo_output("mkdir -p {}; sudo ln -s {} {}; ".format(
                    os.path.dirname(triplet["remote_link_path"]), triplet["remote_mount_path"], triplet["remote_link_path"]))

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
    try:
        mount_fileshare()
        link_fileshare()
    except:
        logging.debug( "Exception when mounting files... "  )    
    else:
        logging.debug( "Examined all mounting points... "  )    
    logging.debug( "End auto_share ... " )

