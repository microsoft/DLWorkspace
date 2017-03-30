#!/usr/bin/python 
import json
import os
import time
import datetime
import argparse
import uuid
import subprocess
import sys
import textwrap
import re
import math
import distutils.dir_util
import distutils.file_util
import shutil
import glob

import yaml
from jinja2 import Environment, FileSystemLoader, Template
import base64

from shutil import copyfile,copytree
import urllib
import socket;

binarytypes = {".png"}
verbose = False; 

def render_template(template_file, target_file, config, verbose=False):
	filename, file_extension = os.path.splitext(template_file)
	if file_extension in binarytypes:
		copyfile(template_file, target_file)
		if verbose:
			print "Copy tempalte " + template_file + " --> " + target_file
	else:
		if verbose:
			print "Render tempalte " + template_file + " --> " + target_file
		ENV_local = Environment(loader=FileSystemLoader("/"))
		template = ENV_local.get_template(os.path.abspath(template_file))
		content = template.render(cnf=config)
		with open(target_file, 'w') as f:
			f.write(content)
		f.close()
	
def render_template_directory(template_dir, target_dir,config, verbose=False):
	os.system("mkdir -p "+target_dir)
	filenames = os.listdir(template_dir)
	for filename in filenames:
		if os.path.isfile(os.path.join(template_dir, filename)):
			render_template(os.path.join(template_dir, filename), os.path.join(target_dir, filename),config, verbose)
		else:
			render_template_directory(os.path.join(template_dir, filename), os.path.join(target_dir, filename),config, verbose)

# Execute a remote SSH cmd with identity file (private SSH key), user, host
def SSH_exec_cmd(identity_file, user,host,cmd,showCmd=True):
	if showCmd or verbose:
		print ("""ssh -o "StrictHostKeyChecking no" -i %s "%s@%s" "%s" """ % (identity_file, user, host, cmd) ) 
	os.system("""ssh -o "StrictHostKeyChecking no" -i %s "%s@%s" "%s" """ % (identity_file, user, host, cmd) )

# SSH Connect to a remote host with identity file (private SSH key), user, host
# Program usually exit here. 
def SSH_connect(identity_file, user,host):
	if verbose:
		print ("""ssh -o "StrictHostKeyChecking no" -i %s "%s@%s" """ % (identity_file, user, host) ) 
	os.system("""ssh -o "StrictHostKeyChecking no" -i %s "%s@%s" """ % (identity_file, user, host) )

# Copy a local file or directory (source) to remote (target) with identity file (private SSH key), user, host 
def scp (identity_file, source, target, user, host):
	cmd = 'scp -i %s -r "%s" "%s@%s:%s"' % (identity_file, source, user, host, target)
	os.system(cmd)

# Copy a local file (source) or directory to remote (target) with identity file (private SSH key), user, host, and  
def sudo_scp (identity_file, source, target, user, host,changePermission=False):
	tmp = str(uuid.uuid4())	
	scp(identity_file, source,"~/%s" % tmp, user, host )
	targetPath = os.path.dirname(target)
	cmd = "sudo mkdir -p %s ; sudo mv ~/%s %s" % (targetPath, tmp, target)
	if changePermission:
		cmd += " ; sudo chmod +x %s" % target

	SSH_exec_cmd(identity_file, user, host, cmd, False)

# Execute a remote SSH cmd with identity file (private SSH key), user, host
# Return the output of the remote command to local
def SSH_exec_cmd_with_output1(identity_file, user,host,cmd, supressWarning = False):
	tmpname = os.path.join("/tmp", str(uuid.uuid4()))
	execcmd = cmd + " > " + tmpname
	if supressWarning:
		execcmd += " 2>/dev/null"
	SSH_exec_cmd(identity_file, user, host, execcmd )
	scpcmd = 'scp -i %s "%s@%s:%s" "%s"' % (identity_file, user, host, tmpname, tmpname)
	# print scpcmd
	os.system( scpcmd )
	SSH_exec_cmd(identity_file, user, host, "rm " + tmpname )
	with open(tmpname, "r") as outputfile:
		output = outputfile.read()
	os.remove(tmpname)
	return output
	
def SSH_exec_cmd_with_output(identity_file, user,host,cmd, supressWarning = False):
	if supressWarning:
		cmd += " 2>/dev/null"
	execmd = """ssh -o "StrictHostKeyChecking no" -i %s "%s@%s" "%s" """ % (identity_file, user, host, cmd )
	if verbose:
		print execmd
	try:
		output = subprocess.check_output( execmd, shell=True )
	except subprocess.CalledProcessError as e:
		output = "Return code: " + str(e.returncode) + ", output: " + e.output.strip()
	# print output
	return output
	
def exec_cmd_local(execmd, supressWarning = False):
	if supressWarning:
		cmd += " 2>/dev/null"
	if verbose:
		print execmd
	try:
		output = subprocess.check_output( execmd, shell=True )
	except subprocess.CalledProcessError as e:
		output = "Return code: " + str(e.returncode) + ", output: " + e.output.strip()
	# print output
	return output
	
def get_host_name( host ):
	execmd = """ssh -o "StrictHostKeyChecking no" -i %s "%s@%s" "hostname" """ % ("deploy/sshkey/id_rsa", "core", host )
	try:
		output = subprocess.check_output( execmd, shell=True )
	except subprocess.CalledProcessError as e:
		return "Exception, with output: " + e.output.strip()
	return output.strip()
	
def get_mac_address( identity_file, host, show=True ):
	output = SSH_exec_cmd_with_output( identity_file, "core", host, "ifconfig" )
	etherMatch = re.compile("ether [0-9a-f][0-9a-f]:[0-9a-f][0-9a-f]:[0-9a-f][0-9a-f]:[0-9a-f][0-9a-f]:[0-9a-f][0-9a-f]:[0-9a-f][0-9a-f]")
	iterator = etherMatch.finditer(output)
	if show:
		print "Node "+host + " Mac address..."
		for match in iterator:
			print match.group()
	macs = []
	for match in iterator:
		macs.append(match.group()[6:])
	return macs

# Execute a remote SSH cmd with identity file (private SSH key), user, host, 
# Copy all directory of srcdir into a temporary folder, execute the command, 
# and then remove the temporary folder. 
# Command should assume that it starts srcdir, and execute a shell script in there. 
# If dstdir is given, the remote command will be executed at dstdir, and its content won't be removed
def SSH_exec_cmd_with_directory( identity_file, user, host, srcdir, cmd, supressWarning = False, preRemove = True, removeAfterExecution = True, dstdir = None ):
	if dstdir is None: 
		tmpdir = os.path.join("/tmp", str(uuid.uuid4()))
		preRemove = False
	else:
		tmpdir = dstdir
		removeAfterExecution = False

	if preRemove:
		SSH_exec_cmd( identity_file, user, host, "sudo rm -rf " + tmpdir )

	scp( identity_file, srcdir, tmpdir, user, host)
	dstcmd = "cd "+tmpdir + "; "
	if supressWarning:
		dstcmd += cmd + " 2>/dev/null; "
	else:
		dstcmd += cmd + "; "
	dstcmd += "cd /tmp; "
	if removeAfterExecution:
		dstcmd += "rm -r " + tmpdir + "; "
	SSH_exec_cmd( identity_file, user, host, dstcmd )


# Execute a remote SSH cmd with identity file (private SSH key), user, host, 
# Copy a bash script a temporary folder, execute the script, 
# and then remove the temporary file. 
def SSH_exec_script( identity_file, user, host, script, supressWarning = False, removeAfterExecution = True):
	tmpfile = os.path.join("/tmp", str(uuid.uuid4())+".sh")
	scp( identity_file, script, tmpfile, user, host)
	cmd = "bash --verbose "+tmpfile
	dstcmd = ""
	if supressWarning:
		dstcmd += cmd + " 2>/dev/null; "
	else:
		dstcmd += cmd + "; "
	if removeAfterExecution:
		dstcmd += "rm -r " + tmpfile + "; "
	SSH_exec_cmd( identity_file, user, host, dstcmd,False )


def get_ETCD_discovery_URL(size):
		try:
			output = urllib.urlopen("https://discovery.etcd.io/new?size=%d" % size ).read()
			if not "https://discovery.etcd.io" in output:
				raise Exception("ERROR: we cannot get etcd discovery url from 'https://discovery.etcd.io/new?size=%d', got message %s" % (size,output)) 
		except Exception as e:
			raise Exception("ERROR: we cannot get etcd discovery url from 'https://discovery.etcd.io/new?size=%d'" % size) 
		return output


def get_cluster_ID_from_file():
	clusterID = None
	if os.path.exists("./deploy/clusterID.yml"):
		f = open("./deploy/clusterID.yml")
		tmp = yaml.load(f)
		f.close()
		if "clusterId" in tmp:
			clusterID = tmp["clusterId"]
		f.close()
	return clusterID


def gen_SSH_key():
		print "==============================================="
		print "generating ssh key..."
		os.system("mkdir -p ./deploy/sshkey")
		os.system("mkdir -p ./deploy/cloud-config")
		os.system("mkdir -p ./deploy/kubelet")
		os.system("rm -r ./deploy/sshkey || true")
		os.system("mkdir -p ./deploy/sshkey")

		os.system("ssh-keygen -t rsa -b 4096 -f ./deploy/sshkey/id_rsa -P ''")

		os.system("rm -r ./deploy/cloud-config")
		os.system("mkdir -p ./deploy/cloud-config")

		os.system("rm -r ./deploy/kubelet")
		os.system("mkdir -p ./deploy/kubelet")


		clusterID = str(uuid.uuid4()) 
		with open("./deploy/clusterID.yml", 'w') as f:
			f.write("clusterId : %s" % clusterID)
		f.close()

def execute_backup_and_encrypt(clusterName, fname, key):
	clusterID = get_cluster_ID_from_file()
	backupdir = "./deploy_backup/backup" 
	os.system("mkdir -p %s/clusterID" % backupdir)
	os.system("cp -r ./*.yaml %s" % backupdir)
	os.system("cp -r ./deploy/sshkey %s/sshkey" % backupdir)
	os.system("cp -r ./deploy/ssl %s/ssl" % backupdir)
	os.system("cp -r ./deploy/clusterID.yml %s/clusterID/" % backupdir)
	os.system("tar -czvf %s.tar.gz %s" % (fname, backupdir))
	if not key is None:
		os.system("openssl enc -aes-256-cbc -k %s -in %s.tar.gz -out %s.tar.gz.enc" % (key, fname, fname) )
		os.system("rm %s.tar.gz" % fname )
	os.system("rm -rf ./deploy_backup/backup")
		
def execute_restore_and_decrypt(fname, key):
	clusterID = get_cluster_ID_from_file()
	backupdir = "./deploy_backup/backup" 
	os.system("mkdir -p %s" % backupdir)
	cleanup_command = ""
	if fname.endswith(".enc"):
		if key is None:
			print ("%s needs decrpytion key" % fname)
			exit(-1)
		fname = fname[:-4]
		os.system("openssl enc -d -aes-256-cbc -k %s -in %s.enc -out %s" % (key, fname, fname) )
		cleanup_command = "rm %s; " % fname
	os.system("tar -xzvf %s %s" % (fname, backupdir))
	os.system("cp %s/*.yaml ." % (backupdir) )
	os.system("cp -r %s/sshkey ./deploy/sshkey" % backupdir)
	os.system("cp -r %s/ssl ./deploy/ssl" % backupdir)
	os.system("cp %s/clusterID/*.yml ./deploy/" % backupdir)
	cleanup_command += "rm -rf ./deploy_backup/backup"
	os.system(cleanup_command)

def backup_keys(clusterName, nargs=[] ):
	if len(nargs)<=0:
		clusterID = get_cluster_ID_from_file()
		fname = "./deploy_backup/config=%s-%s=%s-%s" %(clusterName,clusterID,str(time.time()),str(uuid.uuid4())[:5])
		key = None
	else:
		fname = nargs[0]
		if len(nargs)<=1:
			key = None
		else:
			key = nargs[1]
		
	execute_backup_and_encrypt( clusterName, fname, key )
	
def restore_keys( nargs ):
	if len(nargs)<=0:
		list_of_files = glob.glob("./deploy_backup/config*")
		fname = max(list_of_files, key=os.path.getctime)
		key = None
	else:
		fname = nargs[0]
		if len(nargs)<=1:
			key = None
		else:
			key = nargs[1]
	execute_restore_and_decrypt( fname, key )


def getIP(dnsname):
    try:
        data = socket.gethostbyname(dnsname)
        ip = repr(data).replace("'","")
        return ip
    except Exception:
        return None
