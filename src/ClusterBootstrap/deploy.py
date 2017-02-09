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

import yaml
from jinja2 import Environment, FileSystemLoader, Template
import base64

from shutil import copyfile,copytree
import urllib
import socket;
sys.path.append("storage/glusterFS")
from GlusterFSUtils import GlusterFSJson



capacityMatch = re.compile("\d+[M|G]B")
digitsMatch = re.compile("\d+")
defanswer = ""
ipAddrMetaname = "hostIP"
homeinserver = "http://dlws-clusterportal.westus.cloudapp.azure.com:5000"
discoverserver = "4.2.2.1"
homeininterval = "600"
dockerregistry = "mlcloudreg.westus.cloudapp.azure.com:5000/dlworkspace"

# default search for all partitions of hdb, hdc, hdd, and sdb, sdc, sdd
defPartition = "/dev/[sh]d[^a]"

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def parse_capacity_in_GB( inp ):
	mt = capacityMatch.search(inp)
	if mt is None: 
		return 0.0
	else:
		digits = digitsMatch.search(mt.group(0)).group(0)
		val = int(digits)
		if "GB" in mt.group(0):
			return float(val)
		else:
			return float(val) / 1000.0

def formClusterPortalURL(role, clusterID):
	return config["homeinserver"]+"/GetNodes?role="+role+"&clusterId="+clusterID

def firstChar(s):
	return (s.strip())[0].lower()
	

def raw_input_with_default(prompt):
	if defanswer == "":
		return raw_input(prompt)
	else:
		print prompt + " " + defanswer
		return defanswer

def render(template_file, target_file):
	ENV_local = Environment(loader=FileSystemLoader("/"))
	template = ENV_local.get_template(os.path.abspath(template_file))
	content = template.render(cnf=config)
	with open(target_file, 'w') as f:
		f.write(content)
	f.close()

# Execute a remote SSH cmd with identity file (private SSH key), user, host
def SSH_exec_cmd(identity_file, user,host,cmd,showCmd=True):
	if showCmd:
		print ("""ssh -o "StrictHostKeyChecking no" -i %s "%s@%s" "%s" """ % (identity_file, user, host, cmd) ) 
	os.system("""ssh -o "StrictHostKeyChecking no" -i %s "%s@%s" "%s" """ % (identity_file, user, host, cmd) )

# SSH Connect to a remote host with identity file (private SSH key), user, host
# Program usually exit here. 
def SSH_connect(identity_file, user,host):
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
	print execmd
	try:
		output = subprocess.check_output( execmd, shell=True )
	except subprocess.CalledProcessError as e:
		print "Execution failed: " + e.output
		output = "Execution failed: " + e.output
	# print output
	return output
	
def GetHostName( host ):
	execmd = """ssh -o "StrictHostKeyChecking no" -i %s "%s@%s" "hostname" """ % ("deploy/sshkey/id_rsa", "core", host )
	try:
		output = subprocess.check_output( execmd, shell=True )
	except subprocess.CalledProcessError as e:
		return None
	return output.strip()

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


def Get_ETCD_DiscoveryURL(size):
		try:
			output = urllib.urlopen("https://discovery.etcd.io/new?size=%d" % size ).read()
			if not "https://discovery.etcd.io" in output:
				raise Exception("ERROR: we cannot get etcd discovery url from 'https://discovery.etcd.io/new?size=%d', got message %s" % (size,output)) 
		except Exception as e:
			raise Exception("ERROR: we cannot get etcd discovery url from 'https://discovery.etcd.io/new?size=%d'" % size) 
		return output

def _Check_Config_Items(cnfitem, cnf):
	if not cnfitem in cnf:
		raise Exception("ERROR: we cannot find %s in config file" % cnfitem) 
	else:
		print "Checking configurations '%s' = '%s'" % (cnfitem, cnf[cnfitem])
 
def Check_Config(cnf):
	_Check_Config_Items("discovery_url",cnf)
	_Check_Config_Items("kubernetes_master_node",cnf)
	_Check_Config_Items("kubernetes_master_ssh_user",cnf)
	_Check_Config_Items("api_serviers",cnf)
	_Check_Config_Items("etcd_user",cnf)
	_Check_Config_Items("etcd_node",cnf)
	_Check_Config_Items("etcd_endpoints",cnf)
	_Check_Config_Items("ssh_cert",cnf)
	_Check_Config_Items("pod_ip_range",cnf)
	_Check_Config_Items("basic_auth",cnf)
	_Check_Config_Items("kubernetes_docker_image",cnf)
	_Check_Config_Items("service_cluster_ip_range",cnf)
	if not os.path.isfile(config["ssh_cert"]):
		raise Exception("ERROR: we cannot find ssh key file at %s. \n please run 'python build-pxe-coreos.py docker_image_name' to generate ssh key file and pxe server image." % config["ssh_cert"]) 


def GetCLusterIdFromFile():
	clusterID = None
	if os.path.exists("./deploy/clusterID.yml"):
		f = open("./deploy/clusterID.yml")
		tmp = yaml.load(f)
		f.close()
		if "clusterId" in tmp:
			clusterID = tmp["clusterId"]
		f.close()
	return clusterID


def Gen_SSHKey():
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

def Backup_Keys():
	clusterID = GetCLusterIdFromFile()
	backupdir = "./deploy_backup/%s-%s/%s-%s" % (config["cluster_name"],clusterID,str(time.time()),str(uuid.uuid4())[:5])
	os.system("mkdir -p %s" % backupdir)
	os.system("cp -r ./deploy/sshkey %s" % backupdir)
	os.system("cp -r ./ssl %s" % backupdir)
	os.system("cp -r ./deploy/clusterID.yml %s" % backupdir)

def CopyToISO():
	if not os.path.exists("./deploy/iso-creator"):
		os.system("mkdir -p ./deploy/iso-creator")
	os.system("cp --verbose ./template/pxe/tftp/splash.png ./deploy/iso-creator/splash.png")
	os.system("cp --verbose ./template/pxe/tftp/usr/share/oem/* ./deploy/iso-creator")
	os.system("cp --verbose ./template/iso-creator/* ./deploy/iso-creator")

def InitConfig():
	config = {}
	config["discoverserver"] = discoverserver
	config["homeinserver"] = homeinserver
	config["homeininterval"] = homeininterval
	config["dockerregistry"] = dockerregistry
	return config
	
# Render scripts for kubenete nodes
def addKubeletConfig():
	renderfiles = []

# Render all deployment script used. 
	kubemaster_cfg_files = [f for f in os.listdir("./template/kubelet") if os.path.isfile(os.path.join("./template/kubelet", f))]
	for file in kubemaster_cfg_files:
		renderfiles.append((os.path.join("./template/kubelet", file),os.path.join("./deploy/kubelet", file)))

	for (template_file,target_file) in renderfiles:
		render(template_file,target_file)

	kubemaster_cfg_files = [f for f in os.listdir("./deploy/kubelet") if os.path.isfile(os.path.join("./deploy/kubelet", f))]
	for file in kubemaster_cfg_files:
		with open(os.path.join("./deploy/kubelet", file), 'r') as f:
			content = f.read()
		config[file] = base64.b64encode(content)

	
def Init_Deployment():
	if (os.path.isfile("./deploy/clusterID.yml")):
		
		clusterID = GetCLusterIdFromFile()
		response = raw_input_with_default("There is a cluster (ID:%s) deployment in './deploy', do you want to keep the existing ssh key and CA certificates (y/n)?" % clusterID)
		if firstChar(response) == "n":
			Backup_Keys()
			Gen_SSHKey()
			Gen_CA_Certificates()
			Gen_Worker_Certificates()
			Backup_Keys()
	else:
		Gen_SSHKey()
		Gen_CA_Certificates()
		Gen_Worker_Certificates()
		Backup_Keys()

	clusterID = GetCLusterIdFromFile()

	f = open("./deploy/sshkey/id_rsa.pub")
	sshkey_public = f.read()
	f.close()



	print "Cluster Id is : %s" % clusterID 

	config["clusterId"] = clusterID
	config["sshkey"] = sshkey_public

	addKubeletConfig()

	template_file = "./template/cloud-config/cloud-config-master.yml"
	target_file = "./deploy/cloud-config/cloud-config-master.yml"
	config["role"] = "master"
	
	render(template_file, target_file)

	template_file = "./template/cloud-config/cloud-config-etcd.yml"
	target_file = "./deploy/cloud-config/cloud-config-etcd.yml"
	
	config["role"] = "etcd"
	render(template_file, target_file)

	# Prepare to Generate the ISO image. 
	# Using files in PXE as template. 
	CopyToISO()



	template_file = "./deploy/iso-creator/mkimg.sh.template"
	target_file = "./deploy/iso-creator/mkimg.sh"
	render( template_file, target_file )

	with open("./ssl/ca/ca.pem", 'r') as f:
		content = f.read()
	config["ca.pem"] = base64.b64encode(content)

	with open("./ssl/kubelet/apiserver.pem", 'r') as f:
		content = f.read()
	config["apiserver.pem"] = base64.b64encode(content)
	config["worker.pem"] = base64.b64encode(content)

	with open("./ssl/kubelet/apiserver-key.pem", 'r') as f:
		content = f.read()
	config["apiserver-key.pem"] = base64.b64encode(content)
	config["worker-key.pem"] = base64.b64encode(content)

	addKubeletConfig()

	template_file = "./template/cloud-config/cloud-config-worker.yml"
	target_file = "./deploy/cloud-config/cloud-config-worker.yml"
	render( template_file, target_file )

def CheckNodeAvailability(ipAddress):
	# print "Check node availability on: " + str(ipAddress)
	status = os.system('ssh -o "StrictHostKeyChecking no" -i deploy/sshkey/id_rsa -oBatchMode=yes core@%s hostname > /dev/null' % ipAddress)
	#status = sock.connect_ex((ipAddress,22))
	return status == 0


def GetETCDMasterNodes(clusterId):
	output = urllib.urlopen(formClusterPortalURL("etcd", clusterId)).read()
	output = json.loads(json.loads(output))
	Nodes = []
	NodesInfo = [node for node in output["nodes"] if "time" in node]
	if not "ipToHostname" in config:
		config["ipToHostname"] = {}
	for node in NodesInfo:
		if not node[ipAddrMetaname] in Nodes and CheckNodeAvailability(node[ipAddrMetaname]):
			hostname = GetHostName(node[ipAddrMetaname])
			Nodes.append(node[ipAddrMetaname])
			config["ipToHostname"][node[ipAddrMetaname]] = hostname
	if "etcd_node" in config:
		for node in Nodes:
			if not node in config["etcd_node"]:
				config["etcd_node"].append(node)
	else:
		config["etcd_node"] = Nodes
	config["kubernetes_master_node"] = Nodes
	return Nodes
	
def GetWorkerNodes(clusterId):
	output = urllib.urlopen(formClusterPortalURL("worker", clusterId)).read()
	output = json.loads(json.loads(output))
	Nodes = []
	NodesInfo = [node for node in output["nodes"] if "time" in node]
	if not "ipToHostname" in config:
		config["ipToHostname"] = {}
	for node in NodesInfo:
		if not node[ipAddrMetaname] in Nodes and CheckNodeAvailability(node[ipAddrMetaname]):
			hostname = GetHostName(node[ipAddrMetaname])
			Nodes.append(node[ipAddrMetaname])
			config["ipToHostname"][node[ipAddrMetaname]] = hostname
	config["worker_node"] = Nodes
	return Nodes
	
def GetNodes(clusterId):
	output1 = urllib.urlopen(formClusterPortalURL("worker", clusterId)).read()
	nodes = json.loads(json.loads(output1))["nodes"]
	output3 = urllib.urlopen(formClusterPortalURL("etcd", clusterId)).read()
	nodes = nodes + ( json.loads(json.loads(output3))["nodes"] )
	# print nodes
	Nodes = []
	NodesInfo = [node for node in nodes if "time" in node]
	if not "ipToHostname" in config:
		config["ipToHostname"] = {}
	for node in NodesInfo:
		if not node[ipAddrMetaname] in Nodes and CheckNodeAvailability(node[ipAddrMetaname]):
			hostname = GetHostName(node[ipAddrMetaname])
			Nodes.append(node[ipAddrMetaname])
			config["ipToHostname"][node[ipAddrMetaname]] = hostname
	config["nodes"] = Nodes
	return Nodes

def Check_Master_ETCD_Status():
	masterNodes = []
	etcdNodes = []
	print "==============================================="
	print "Checking Available Nodes for Deployment..."
	if "clusterId" in config:
		GetETCDMasterNodes(config["clusterId"])
		GetWorkerNodes(config["clusterId"])
	print "==============================================="
	print "Activate Master Node(s): %s\n %s \n" % (len(config["kubernetes_master_node"]),",".join(config["kubernetes_master_node"]))
	print "Activate ETCD Node(s):%s\n %s \n" % (len(config["etcd_node"]),",".join(config["etcd_node"]))
	print "Activate Worker Node(s):%s\n %s \n" % (len(config["worker_node"]),",".join(config["worker_node"]))

def Clean_Deployment():
	print "==============================================="
	print "Cleaning previous deployment..."	
	if (os.path.isfile("./deploy/clusterID.yml")):
		Backup_Keys()
	os.system("rm -r ./deploy/*")


def Gen_CA_Certificates():
	os.system("cd ./ssl && ./gencerts_ca.sh")

def Gen_Worker_Certificates():
	os.system("cd ./ssl && ./gencerts_kubelet.sh")	

def Gen_Master_Certificates():
	config["apiserver_ssl_dns"] = ""
	config["apiserver_ssl_ip"] = "IP.1 = 10.3.0.1\nIP.2 = 127.0.0.1\n"+ "\n".join(["IP."+str(i+3)+" = "+ip for i,ip in enumerate(config["kubernetes_master_node"])])

	renderfiles = []
	renderfiles.append(("./ssl/openssl-apiserver.cnf.template","./ssl/openssl-apiserver.cnf"))

	
	for (template_file,target_file) in renderfiles:
		render(template_file,target_file)

	os.system("cd ./ssl && ./gencerts_master.sh")


def Gen_ETCD_Certificates():

	config["etcd_ssl_dns"] = ""
	config["etcd_ssl_ip"] = "IP.1 = 127.0.0.1\n" + "\n".join(["IP."+str(i+2)+" = "+ip for i,ip in enumerate(config["etcd_node"])])
	renderfiles = []
	renderfiles.append(("./ssl/openssl-etcd.cnf.template","./ssl/openssl-etcd.cnf"))

	
	for (template_file,target_file) in renderfiles:
		render(template_file,target_file)

	os.system("cd ./ssl && ./gencerts_etcd.sh")	



def Gen_Configs():
	print "==============================================="
	print "generating configuration files..."
	os.system("mkdir -p ./deploy/bin")
	os.system("mkdir -p ./deploy/etcd")
	os.system("mkdir -p ./deploy/kube-addons")
	os.system("mkdir -p ./deploy/master")	
	os.system("rm -r ./deploy/bin")
	os.system("rm -r ./deploy/etcd")
	os.system("rm -r ./deploy/kube-addons")
	os.system("rm -r ./deploy/master")

	deployDirs = ["deploy/etcd","deploy/kubelet","deploy/master","deploy/web-docker/kubelet","deploy/kube-addons","deploy/bin"]
	for deployDir in deployDirs:
		if not os.path.exists(deployDir):
			os.system("mkdir -p %s" % (deployDir))


	etcd_servers = config["etcd_node"]

	#if int(config["etcd_node_num"]) <= 0:
	#	raise Exception("ERROR: we need at least one etcd_server.") 

	kubernetes_masters = config["kubernetes_master_node"]

	#if len(kubernetes_masters) <= 0:
	#	raise Exception("ERROR: we need at least one etcd_server.") 

	config["discovery_url"] = Get_ETCD_DiscoveryURL(int(config["etcd_node_num"]))

	if "ssh_cert" not in config and os.path.isfile("./deploy/sshkey/id_rsa"):
		config["ssh_cert"] = "./deploy/sshkey/id_rsa"
		config["etcd_user"] = "core"
		config["kubernetes_master_ssh_user"] = "core"

	#config["api_serviers"] = ",".join(["https://"+x for x in config["kubernetes_master_node"]])
	config["api_serviers"] = "https://"+config["kubernetes_master_node"][0]
	config["etcd_endpoints"] = ",".join(["https://"+x+":2379" for x in config["etcd_node"]])


	f = open(config["ssh_cert"])
	sshkey_public = f.read()
	f.close()

	config["sshkey"] = sshkey_public
	Check_Config(config)


	renderfiles = []

	kubemaster_cfg_files = [f for f in os.listdir("./template/etcd") if os.path.isfile(os.path.join("./template/etcd", f))]
	for file in kubemaster_cfg_files:
		renderfiles.append((os.path.join("./template/etcd", file),os.path.join("./deploy/etcd", file)))


	kubemaster_cfg_files = [f for f in os.listdir("./template/master") if os.path.isfile(os.path.join("./template/master", f))]
	for file in kubemaster_cfg_files:
		renderfiles.append((os.path.join("./template/master", file),os.path.join("./deploy/master", file)))


	kubemaster_cfg_files = [f for f in os.listdir("./template/web-docker") if os.path.isfile(os.path.join("./template/web-docker", f))]
	for file in kubemaster_cfg_files:
		renderfiles.append((os.path.join("./template/web-docker", file),os.path.join("./deploy/web-docker", file)))


	kubemaster_cfg_files = [f for f in os.listdir("./template/kube-addons") if os.path.isfile(os.path.join("./template/kube-addons", f))]
	for file in kubemaster_cfg_files:
		renderfiles.append((os.path.join("./template/kube-addons", file),os.path.join("./deploy/kube-addons", file)))


	
	for (template_file,target_file) in renderfiles:
		render(template_file,target_file)

def Get_Config():
	if "ssh_cert" not in config and os.path.isfile("./deploy/sshkey/id_rsa"):
		config["ssh_cert"] = "./deploy/sshkey/id_rsa"
		config["etcd_user"] = "core"
		config["kubernetes_master_ssh_user"] = "core"

	
	f = open(config["ssh_cert"])
	sshkey_public = f.read()
	f.close()

	config["sshkey"] = sshkey_public


def Update_Reporting_service():
	kubernetes_masters = config["kubernetes_master_node"]
	kubernetes_master_user = config["kubernetes_master_ssh_user"]

	for kubernetes_master in kubernetes_masters:
		print "==============================================="
		print "Updating report service on master %s... " % kubernetes_master

		SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo systemctl stop reportcluster")
		scp(config["ssh_cert"],"./deploy/master/report.sh","/home/%s/report.sh" % kubernetes_master_user , kubernetes_master_user, kubernetes_master )
		SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo mv /home/%s/report.sh /opt/report.sh" % (kubernetes_master_user))

		SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo systemctl start reportcluster")


	etcd_servers = config["etcd_node"]
	etcd_server_user = config["etcd_user"]


	for etcd_server_address in etcd_servers:
		print "==============================================="
		print "Updating report service on etcd node %s... " % etcd_server_address

		SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo systemctl stop reportcluster")
		scp(config["ssh_cert"],"./deploy/etcd/report.sh","/home/%s/report.sh" % etcd_server_user , etcd_server_user, etcd_server_address )
		SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo mv /home/%s/report.sh /opt/report.sh" % (etcd_server_user))

		SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo systemctl start reportcluster")

def Clean_Master():
	kubernetes_masters = config["kubernetes_master_node"]
	kubernetes_master_user = config["kubernetes_master_ssh_user"]

	for kubernetes_master in kubernetes_masters:
		print "==============================================="
		print "Clean up kubernetes master %s... (It is OK to see 'Errors' in this section)" % kubernetes_master

		SSH_exec_script(config["ssh_cert"],kubernetes_master_user, kubernetes_master, "./deploy/master/cleanup-master.sh")


def Deploy_Master(kubernetes_master):
		print "==============================================="
		kubernetes_master_user = config["kubernetes_master_ssh_user"]
		print "starting kubernetes master on %s..." % kubernetes_master

		config["master_ip"] = kubernetes_master
		render("./template/master/kube-apiserver.yaml","./deploy/master/kube-apiserver.yaml")
		render("./template/master/kubelet.service","./deploy/master/kubelet.service")
		render("./template/master/pre-master-deploy.sh","./deploy/master/pre-master-deploy.sh")
		render("./template/master/post-master-deploy.sh","./deploy/master/post-master-deploy.sh")


		SSH_exec_script(config["ssh_cert"],kubernetes_master_user, kubernetes_master, "./deploy/master/pre-master-deploy.sh")


		with open("./deploy/master/deploy.list","r") as f:
			deploy_files = [s.split(",") for s in f.readlines() if len(s.split(",")) == 2]
		for (source, target) in deploy_files:
			if (os.path.isfile(source.strip()) or os.path.exists(source.strip())):
				sudo_scp(config["ssh_cert"],source.strip(),target.strip(),kubernetes_master_user,kubernetes_master)


		SSH_exec_script(config["ssh_cert"],kubernetes_master_user, kubernetes_master, "./deploy/master/post-master-deploy.sh")

def Deploy_Masters():

	print "==============================================="
	print "Prepare to deploy kubernetes master"
	print "waiting for ETCD service is ready..."
	Check_etcd_service()
	print "==============================================="
	print "Generating master configuration files..."

	kubernetes_masters = config["kubernetes_master_node"]
	kubernetes_master_user = config["kubernetes_master_ssh_user"]

	renderfiles = []
	kubemaster_cfg_files = [f for f in os.listdir("./template/master") if os.path.isfile(os.path.join("./template/master", f))]
	for file in kubemaster_cfg_files:
		render(os.path.join("./template/master", file),os.path.join("./deploy/master", file))
	kubemaster_cfg_files = [f for f in os.listdir("./template/kube-addons") if os.path.isfile(os.path.join("./template/kube-addons", f))]
	for file in kubemaster_cfg_files:
		render(os.path.join("./template/kube-addons", file),os.path.join("./deploy/kube-addons", file))


	urllib.urlretrieve ("http://ccsdatarepo.westus.cloudapp.azure.com/data/kube/kubelet/kubelet", "./deploy/bin/kubelet")
	urllib.urlretrieve ("http://ccsdatarepo.westus.cloudapp.azure.com/data/kube/kubelet/kubectl", "./deploy/bin/kubectl")
	
	Clean_Master()

	for i,kubernetes_master in enumerate(kubernetes_masters):
		Deploy_Master(kubernetes_master)


	SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_masters[0], "until curl -q http://127.0.0.1:8080/version/ ; do sleep 5; echo 'waiting for master...'; done;  sudo /opt/bin/kubectl create -f /opt/addons/kube-addons/", False)



def Uncordon_Master():
	kubernetes_masters = config["kubernetes_master_node"]
	kubernetes_master_user = config["kubernetes_master_ssh_user"]
	for i,kubernetes_master in enumerate(kubernetes_masters):
		SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo /opt/bin/kubectl uncordon \$HOSTNAME")



def Clean_ETCD():
	etcd_servers = config["etcd_node"]
	etcd_server_user = config["etcd_user"]

	for etcd_server_address in etcd_servers:
		print "==============================================="
		print "Clean up etcd servers %s... (It is OK to see 'Errors' in this section)" % etcd_server_address		
		#SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "timeout 10 docker rm -f \$(timeout 3 docker ps -q -a)")
		SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo rm -r /var/etcd/data")
		SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo rm -r /etc/etcd/ssl")

def Check_etcd_service():
	print "waiting for ETCD service is ready..."
	etcd_servers = config["etcd_node"]
	cmd = "curl --cacert %s --cert %s --key %s 'https://%s:2379/v2/keys'" % ("./ssl/etcd/ca.pem","./ssl/etcd/etcd.pem","./ssl/etcd/etcd-key.pem", etcd_servers[0])
	while os.system(cmd) != 0:
		time.sleep(5)
	print "ETCD service is ready to use..."

def Deploy_ETCD_Docker():
	etcd_servers = config["etcd_node"]
	etcd_server_user = config["etcd_user"]
	
	renderfiles = []

	kubemaster_cfg_files = [f for f in os.listdir("./template/etcd") if os.path.isfile(os.path.join("./template/etcd", f))]
	for file in kubemaster_cfg_files:
		renderfiles.append((os.path.join("./template/etcd", file),os.path.join("./deploy/etcd", file)))
		render(os.path.join("./template/etcd", file),os.path.join("./deploy/etcd", file))


	Clean_ETCD()

	for etcd_server_address in etcd_servers:
		#print "==============================================="
		#print "deploy configuration files to web server..."
		#scp(config["ssh_cert"],"./deploy","/var/www/html", config["webserver_user"], config["webserver"] )

		print "==============================================="
		print "deploy certificates to etcd server %s" % etcd_server_address
		
		SSH_exec_cmd (config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo mkdir -p /etc/kubernetes/ssl") 
		SSH_exec_cmd (config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo chown %s /etc/kubernetes/ssl " % (etcd_server_user)) 
		scp(config["ssh_cert"],"./ssl/etcd","/etc/kubernetes/ssl", etcd_server_user, etcd_server_address )

		print "==============================================="
		print "starting etcd service on %s ..." % etcd_server_address


		config["etcd_node_ip"] = etcd_server_address
		render("./template/etcd/docker_etcd.sh","./deploy/etcd/docker_etcd.sh")
		render("./template/etcd/docker_etcd_ssl.sh","./deploy/etcd/docker_etcd_ssl.sh")

		scp(config["ssh_cert"],"./deploy/etcd/docker_etcd.sh","/home/%s/docker_etcd.sh" % etcd_server_user, etcd_server_user, etcd_server_address )
		SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "chmod +x /home/%s/docker_etcd.sh" % etcd_server_user)

		scp(config["ssh_cert"],"./deploy/etcd/docker_etcd_ssl.sh","/home/%s/docker_etcd_ssl.sh" % etcd_server_user, etcd_server_user, etcd_server_address )
		SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "chmod +x /home/%s/docker_etcd_ssl.sh" % etcd_server_user)


		scp(config["ssh_cert"],"./deploy/etcd/init_network.sh","/home/%s/init_network.sh" % etcd_server_user, etcd_server_user, etcd_server_address )
		SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "chmod +x /home/%s/init_network.sh" % etcd_server_user)

		SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "/home/%s/docker_etcd_ssl.sh" % etcd_server_user)

	print "==============================================="
	print "init etcd service on %s ..."  % etcd_servers[0]


	Check_etcd_service()


	scp(config["ssh_cert"],"./deploy/etcd/init_network.sh","/home/%s/init_network.sh" % etcd_server_user, etcd_server_user, etcd_server_address )
	SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_servers[0], "chmod +x /home/%s/init_network.sh" % etcd_server_user)
	SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_servers[0], "/home/%s/init_network.sh" % etcd_server_user)


def Deploy_ETCD():
	etcd_servers = config["etcd_node"]
	etcd_server_user = config["etcd_user"]
	
	Clean_ETCD()

	for i,etcd_server_address in enumerate(etcd_servers):
		#print "==============================================="
		#print "deploy configuration files to web server..."
		#scp(config["ssh_cert"],"./deploy","/var/www/html", config["webserver_user"], config["webserver"] )

		SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo systemctl stop etcd3")

		print "==============================================="
		print "deploy certificates to etcd server %s" % etcd_server_address
		
		SSH_exec_cmd (config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo mkdir -p /etc/etcd/ssl") 
		SSH_exec_cmd (config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo chown %s /etc/etcd/ssl " % (etcd_server_user)) 
		scp(config["ssh_cert"],"./ssl/etcd/ca.pem","/etc/etcd/ssl", etcd_server_user, etcd_server_address )
		scp(config["ssh_cert"],"./ssl/etcd/etcd.pem","/etc/etcd/ssl", etcd_server_user, etcd_server_address )
		scp(config["ssh_cert"],"./ssl/etcd/etcd-key.pem","/etc/etcd/ssl", etcd_server_user, etcd_server_address )

		print "==============================================="
		print "starting etcd service on %s ..." % etcd_server_address


		config["etcd_node_ip"] = etcd_server_address
		render("./template/etcd/etcd3.service","./deploy/etcd/etcd3.service")
		render("./template/etcd/etcd_ssl.sh","./deploy/etcd/etcd_ssl.sh")

		sudo_scp(config["ssh_cert"],"./deploy/etcd/etcd3.service","/etc/systemd/system/etcd3.service", etcd_server_user, etcd_server_address )

		sudo_scp(config["ssh_cert"],"./deploy/etcd/etcd_ssl.sh","/opt/etcd_ssl.sh", etcd_server_user, etcd_server_address )
		SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "chmod +x /opt/etcd_ssl.sh")
		SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo /opt/etcd_ssl.sh")



	print "==============================================="
	print "init etcd service on %s ..."  % etcd_servers[0]


	print "waiting for ETCD service is ready..."
	cmd = "curl --cacert %s --cert %s --key %s 'https://%s:2379/v2/keys'" % ("./ssl/etcd/ca.pem","./ssl/etcd/etcd.pem","./ssl/etcd/etcd-key.pem", etcd_servers[0])
	while os.system(cmd) != 0:
		print "ETCD service is NOT ready, waiting for 5 seconds..."
		time.sleep(5)
	print "ETCD service is ready to use..."



	render("./template/etcd/init_network.sh","./deploy/etcd/init_network.sh")
	scp(config["ssh_cert"],"./deploy/etcd/init_network.sh","/home/%s/init_network.sh" % etcd_server_user, etcd_server_user, etcd_server_address )
	SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_servers[0], "chmod +x /home/%s/init_network.sh" % etcd_server_user)
	SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_servers[0], "/home/%s/init_network.sh" % etcd_server_user)


def Create_ISO():
	imagename = "./deploy/iso/dlworkspace-cluster-deploy-"+config["cluster_name"]+".iso"
	os.system("mkdir -p ./deploy/iso")
	os.system("cd deploy/iso-creator && bash ./mkimg.sh -v 1185.5.0 -a")
	os.system("mv deploy/iso-creator/coreos-1185.5.0.iso "+imagename )
	os.system("rm -rf ./iso-creator/syslinux-6.03*")
	os.system("rm -rf ./iso-creator/coreos-*")
	print "Please find the bootable USB image at: "+imagename
	print 


def Create_PXE():
	os.system("rm -r ./deploy/pxe")
	os.system("mkdir -p ./deploy/docker")
	os.system("cp -r ./template/pxe ./deploy/pxe")
	os.system("cp -r ./deploy/cloud-config/* ./deploy/pxe/tftp/usr/share/oem")
	dockername = "dlworkspace-pxe:%s" % config["cluster_name"] 
	os.system("docker build -t %s deploy/pxe" % dockername)
	tarname = "deploy/docker/dlworkspace-pxe-%s.tar" % config["cluster_name"]
	
	os.system("docker save " + dockername + " > " + tarname )
	print ("A DL workspace docker is built at: "+ dockername)
	print ("It is also saved as a tar file to: "+ tarname)
	
	#os.system("docker rmi dlworkspace-pxe:%s" % config["cluster_name"])

def CleanWorkerNodes():
	workerNodes = GetWorkerNodes(config["clusterId"])
	for nodeIP in workerNodes:
		print "==============================================="
		print "cleaning worker node: %s ..."  % nodeIP		
		SSH_exec_cmd(config["ssh_cert"], "core", nodeIP, "sudo systemctl stop kubelet")
		SSH_exec_cmd(config["ssh_cert"], "core", nodeIP, "docker rm -f \$(docker ps -a -q)")
		SSH_exec_cmd(config["ssh_cert"], "core", nodeIP, "sudo systemctl stop docker")
		SSH_exec_cmd(config["ssh_cert"], "core", nodeIP, "sudo systemctl stop flanneld")
		SSH_exec_cmd(config["ssh_cert"], "core", nodeIP, "sudo systemctl stop bootstrap")
		SSH_exec_cmd(config["ssh_cert"], "core", nodeIP, "sudo systemctl stop reportcluster")
		SSH_exec_cmd(config["ssh_cert"], "core", nodeIP, "sudo reboot")



def UpdateWorkerNode(nodeIP):
	print "==============================================="
	print "updating worker node: %s ..."  % nodeIP
	SSH_exec_cmd_with_directory(config["ssh_cert"], "core", nodeIP, "scripts", "bash --verbose stop-worker.sh")

	sudo_scp(config["ssh_cert"],"./deploy/kubelet/options.env","/etc/flannel/options.env", "core", nodeIP )

	sudo_scp(config["ssh_cert"],"./deploy/kubelet/kubelet.service","/etc/systemd/system/kubelet.service", "core", nodeIP )

	sudo_scp(config["ssh_cert"],"./deploy/kubelet/worker-kubeconfig.yaml","/etc/kubernetes/worker-kubeconfig.yaml", "core", nodeIP )
	
	sudo_scp(config["ssh_cert"],"./deploy/kubelet/kubelet.sh","/opt/kubelet.sh", "core", nodeIP )

	sudo_scp(config["ssh_cert"],"./deploy/bin/kubelet","/opt/kubelet", "core", nodeIP )
	SSH_exec_cmd(config["ssh_cert"], "core", nodeIP, "sudo chmod +x /opt/kubelet")


	with open("./ssl/ca/ca.pem", 'r') as f:
		content = f.read()
	config["ca.pem"] = base64.b64encode(content)

	with open("./ssl/kubelet/apiserver.pem", 'r') as f:
		content = f.read()
	config["apiserver.pem"] = base64.b64encode(content)
	config["worker.pem"] = base64.b64encode(content)

	with open("./ssl/kubelet/apiserver-key.pem", 'r') as f:
		content = f.read()
	config["apiserver-key.pem"] = base64.b64encode(content)
	config["worker-key.pem"] = base64.b64encode(content)


	sudo_scp(config["ssh_cert"],"./ssl/ca/ca.pem","/etc/kubernetes/ssl/ca.pem", "core", nodeIP )
	sudo_scp(config["ssh_cert"],"./ssl/ca/ca.pem","/etc/ssl/etcd/ca.pem", "core", nodeIP )

	sudo_scp(config["ssh_cert"],"./ssl/kubelet/apiserver.pem","/etc/kubernetes/ssl/worker.pem", "core", nodeIP )
	sudo_scp(config["ssh_cert"],"./ssl/kubelet/apiserver.pem","/etc/ssl/etcd/apiserver.pem", "core", nodeIP )

	sudo_scp(config["ssh_cert"],"./ssl/kubelet/apiserver-key.pem","/etc/kubernetes/ssl/worker-key.pem", "core", nodeIP )
	sudo_scp(config["ssh_cert"],"./ssl/kubelet/apiserver-key.pem","/etc/ssl/etcd/apiserver-key.pem", "core", nodeIP )

	sudo_scp(config["ssh_cert"],"./deploy/kubelet/report.sh","/opt/report.sh", "core", nodeIP )
	sudo_scp(config["ssh_cert"],"./deploy/kubelet/reportcluster.service","/etc/systemd/system/reportcluster.service", "core", nodeIP )

	SSH_exec_cmd_with_directory(config["ssh_cert"], "core", nodeIP, "scripts", "bash --verbose start-worker.sh")

	print "done!"


def UpdateWorkerNodes():
	os.system('sed "s/##etcd_endpoints##/%s/" "./deploy/kubelet/options.env.template" > "./deploy/kubelet/options.env"' % config["etcd_endpoints"].replace("/","\\/"))
	os.system('sed "s/##api_serviers##/%s/" ./deploy/kubelet/kubelet.service.template > ./deploy/kubelet/kubelet.service' % config["api_serviers"].replace("/","\\/"))
	os.system('sed "s/##api_serviers##/%s/" ./deploy/kubelet/worker-kubeconfig.yaml.template > ./deploy/kubelet/worker-kubeconfig.yaml' % config["api_serviers"].replace("/","\\/"))
	
	urllib.urlretrieve ("http://ccsdatarepo.westus.cloudapp.azure.com/data/kube/kubelet/kubelet", "./deploy/bin/kubelet")

	workerNodes = GetWorkerNodes(config["clusterId"])
	for node in workerNodes:
		UpdateWorkerNode(node)

	os.system("rm ./deploy/kubelet/options.env")
	os.system("rm ./deploy/kubelet/kubelet.service")
	os.system("rm ./deploy/kubelet/worker-kubeconfig.yaml")

	#if len(config["kubernetes_master_node"]) > 0:
		#SSH_exec_cmd(config["ssh_cert"], "core", config["kubernetes_master_node"][0], "sudo /opt/bin/kubelet get nodes")

def CreateMYSQLForWebUI():
	#todo: create a mysql database, and set "mysql-hostname", "mysql-username", "mysql-password", "mysql-database"
	pass

def BuildRestfulAPIDocker():
	dockername = "%s/%s-restfulapi" %  (config["dockerregistry"],config["cluster_name"])
	tarname = "deploy/docker/restfulapi-%s.tar" % config["cluster_name"]

	os.system("docker rmi %s" % dockername)
	os.system("docker build -t %s ../docker-images/RestfulAPI" % dockername)

	if not os.path.exists("deploy/docker"):
		os.system("mkdir -p %s" % "deploy/docker")

	os.system("rm %s" % tarname )
	os.system("docker save " + dockername + " > " + tarname )

def DeployRestfulAPIonNode(ipAddress):

	masterIP = ipAddress
	dockername = "%s/dlws-restfulapi" %  (config["dockerregistry"])

	# if user didn't give storage server information, use CCS public storage in default. 
	if "nfs-server" not in config:
		config["nfs-server"] = "10.196.44.241:/mnt/data"

	if not os.path.exists("./deploy/RestfulAPI"):
		os.system("mkdir -p ./deploy/RestfulAPI")
	render("../utils/config.yaml.template","./deploy/RestfulAPI/config.yaml")
	sudo_scp(config["ssh_cert"],"./deploy/RestfulAPI/config.yaml","/etc/RestfulAPI/config.yaml", "core", masterIP )


	SSH_exec_cmd(config["ssh_cert"], "core", masterIP, "sudo mkdir -p /dlws-data && sudo mount %s /dlws-data" % config["nfs-server"])


	SSH_exec_cmd(config["ssh_cert"], "core", masterIP, "docker rm -f restfulapi")
	SSH_exec_cmd(config["ssh_cert"], "core", masterIP, "docker rm -f jobScheduler")

	SSH_exec_cmd(config["ssh_cert"], "core", masterIP, "docker pull %s" % dockername)
	SSH_exec_cmd(config["ssh_cert"], "core", masterIP, "docker run -d -p 5000:5000 --restart always -v /etc/RestfulAPI:/RestfulAPI --name restfulapi %s" % dockername)
	SSH_exec_cmd(config["ssh_cert"], "core", masterIP, "docker run -d -v /dlws-data:/dlws-data -v /etc/RestfulAPI:/RestfulAPI --restart always --name jobScheduler %s /runScheduler.sh" % dockername)


	print "==============================================="
	print "restful api is running at: http://%s:5000" % masterIP
	config["restapi"] = "http://%s:5000" %  masterIP

def BuildWebUIDocker():
	os.system("docker rmi %s" % dockername)
	os.system("docker build -t %s ../docker-images/WebUI" % dockername)

def DeployWebUIOnNode(ipAddress):

	sshUser = "core"
	webUIIP = ipAddress
	dockername = "%s/dlws-webui" %  (config["dockerregistry"])



	if "restapi" not in config:
		print "!!!! Cannot deploy Web UI - RestfulAPI is not deployed"
		return

	if not os.path.exists("./deploy/WebUI"):
		os.system("mkdir -p ./deploy/WebUI")
	render("./template/WebUI/appsettings.json.template","./deploy/WebUI/appsettings.json")
	sudo_scp(config["ssh_cert"],"./deploy/WebUI/appsettings.json","/etc/WebUI/appsettings.json", "core", webUIIP )

	SSH_exec_cmd(config["ssh_cert"], sshUser, webUIIP, "docker pull %s" % dockername)
	SSH_exec_cmd(config["ssh_cert"], sshUser, webUIIP, "docker run -d -p 80:80 -v /etc/WebUI:/WebUI --restart always --name webui %s" % dockername)


	print "==============================================="
	print "Web UI is running at: http://%s" % webUIIP


def DeployWebUI():
	masterIP = config["kubernetes_master_node"][0]
	DeployRestfulAPIonNode(masterIP)
	DeployWebUIOnNode(masterIP)


def getPartitionNode(node, prog):
	output = SSH_exec_cmd_with_output(config["ssh_cert"], "core", node, "sudo parted -l -s", True)
	# print output
	drives = prog.search( output )
	# print(drives.group())
	drivesInfo = prog.split( output )
	# print len(drivesInfo)
	ndrives = len(drivesInfo)/2
	partinfo = {}
	blockdevice = 1
	for i in range(ndrives):
		deviceinfo = {}
		drivename = drivesInfo[i*2+1]
		driveString = drivesInfo[i*2+2]
		#print drivename
		#print driveString
		if not (prog.match(drivename) is None):
			# print driveString
			capacity = parse_capacity_in_GB( driveString )
			lines = driveString.splitlines()
			
			# Skip to "parted" print out where each partition information is shown 
			n = 0
			while n < len(lines):
				segs = lines[n].split()
				if len(segs) > 1 and segs[0]=="Number":
					break;
				n = n + 1
			
			n = n + 1
			parted = {}
			# parse partition information
			while n < len(lines):
				segs = lines[n].split()
				if len(segs) >= 4 and segs[0].isdigit():
					partnum = int(segs[0])
					partcap = parse_capacity_in_GB(segs[3])
					parted[partnum] = partcap
				else:
					break;
				n += 1
			
			# print drivename + " Capacity: " + str(capacity) + " GB, " + str(parted)
			deviceinfo["name"] = drivename
			deviceinfo["capacity"] = capacity
			deviceinfo["parted"] = parted
			partinfo[blockdevice] = deviceinfo
			blockdevice += 1
	return partinfo 
	
# Get Partition of all nodes in a cluster
def getPartitions(nodes, regexp):
	prog = re.compile("("+regexp+")")
	nodesinfo = {}
	for node in nodes:
		partinfo = getPartitionNode( node, prog )
		if not(partinfo is None):
			nodesinfo[node] = partinfo
	return nodesinfo

# Print out the Partition information of all nodes in a cluster	
def showPartitions(nodes, regexp):
	nodesinfo = getPartitions(nodes, regexp)
	for node in nodesinfo:
		print "Node: " + node 
		alldeviceinfo = nodesinfo[node]
		for bdevice in alldeviceinfo:
			deviceinfo = alldeviceinfo[bdevice] 
			print deviceinfo["name"] + ", Capacity: " + str(deviceinfo["capacity"]) + "GB" + ", Partition: " + str(deviceinfo["parted"])
	return nodesinfo
	
# Calculate out a partition configuration in GB as follows. 
# partitionConfig is of s1,s2,..,sn:
#    If s_i < 0, the partition is in absolute size (GB)
#    If s_i > 0, the partition is in proportion.
def calculatePartitions( capacity, partitionConfig):
	npart = len(partitionConfig)
	partitionSize = [0.0]*npart
	sumProportion = 0.0
	#print "Beginning Capacity " + str(capacity)
	#print partitionSize
	for i in range(npart):
		if partitionConfig[i] < 0.0:
			if capacity > 0.0:
				partitionSize[i] = min( capacity, -partitionConfig[i])
				capacity -= partitionSize[i]
			else:
				partitionSize[i] = 0.0
		else:
			sumProportion += partitionConfig[i]
	#print "Ending Capacity " + str(capacity) 
	#print partitionSize
	for i in range(npart):
		if partitionConfig[i] >= 0.0:
			if sumProportion == 0.0:
				partitionSize[i] = 0.0
			else:
				partitionSize[i] = capacity * partitionConfig[i] / sumProportion
	return partitionSize
	
# Repartition of all nodes in a cluster
def repartitionNodes(nodes, nodesinfo, partitionConfig):
	for node in nodes:
		cmd = ""
		alldeviceinfo = nodesinfo[node]
		for bdevice in alldeviceinfo:
			deviceinfo = alldeviceinfo[bdevice] 
			existingPartitions = deviceinfo["parted"]
			if len( existingPartitions ) > 0:
				# remove existing partitions
				removedPartitions = []
				for part in existingPartitions:
					removedPartitions.append(part)
				# print removedPartitions
				removedPartitions.sort(reverse=True)
				for part in removedPartitions:
					cmd += "sudo parted -s " + deviceinfo["name"] + " rm " + str(part) + "; "
			partitionSize = calculatePartitions( deviceinfo["capacity"], partitionConfig)
			# print partitionSize
			totalPartitionSize = sum( partitionSize )
			start = 0
			npart = len(partitionSize)
			for i in range(npart):
				partSize = partitionSize[i]
				end = int( math.floor( start + (partSize/totalPartitionSize)*100.0 + 0.5 ))
				if i == npart-1:
					end = 100
				if end > 100:
					end = 100
				cmd += "sudo parted -s --align optimal " + deviceinfo["name"] + " mkpart logical " + str(start) +"% " + str(end)+"% ; "
				start = end
		SSH_exec_cmd(config["ssh_cert"], "core", node, cmd)
	()
	
def glusterFSCopy():
	srcdir = "storage/glusterFS/kube-templates"
	dstdir = os.path.join( "deploy", srcdir)
	# print "Copytree from: " + srcdir + " to: " + dstdir
	distutils.dir_util.copy_tree( srcdir, dstdir )
	srcfile = "storage/glusterFS/gk-deploy"
	dstfile = os.path.join( "deploy", srcfile)
	copyfile( srcfile, dstfile )
	srcfile = "storage/glusterFS/RemoveLVM.py"
	dstfile = os.path.join( "deploy", srcfile)
	copyfile( srcfile, dstfile )
	
# Deploy glusterFS on a cluster
def startGlusterFS( masternodes, ipToHostname, nodesinfo, glusterFSargs, flag = "-g"):
	glusterFSJson = GlusterFSJson(ipToHostname, nodesinfo, glusterFSargs)
	glusterFSJsonFilename = "deploy/storage/glusterFS/topology.json"
	print "Write GlusterFS configuration file to: " + glusterFSJsonFilename
	glusterFSJson.dump(glusterFSJsonFilename)
	glusterFSCopy()
	rundir = "/tmp/startGlusterFS"
	# use the same heketidocker as in heketi deployment
	heketidocker = "heketi/heketi:latest"
	remotecmd = "docker pull "+heketidocker+"; "
	remotecmd += "docker run -v "+rundir+":"+rundir+" --rm --entrypoint=cp "+heketidocker+" /usr/bin/heketi-cli "+rundir+"; "
	remotecmd += "sudo bash ./gk-deploy "
	remotecmd += flag
	SSH_exec_cmd_with_directory( config["ssh_cert"], "core", masternodes[0], "deploy/storage/glusterFS", remotecmd, dstdir = rundir )
	
# Deploy glusterFS on a cluster
def removeGlusterFSvolumes( masternodes, ipToHostname, nodesinfo, glusterFSargs, nodes ):
	startGlusterFS( masternodes, ipToHostname, nodesinfo, glusterFSargs, flag = "-g --yes --abort")
	for node in nodes:
		glusterFSCopy()
		rundir = "/tmp/glusterFSAdmin"
		remotecmd = "sudo python RemoveLVM.py "
		SSH_exec_cmd_with_directory( config["ssh_cert"], "core", node, "deploy/storage/glusterFS", remotecmd, dstdir = rundir )

def execOnAll(nodes, args, supressWarning = False):
	cmd = ""
	for arg in args:
		if cmd == "":
			cmd += arg
		else:
			cmd += " " + arg
	for node in nodes:
		SSH_exec_cmd(config["ssh_cert"], "core", node, cmd)
		print "Node: " + node + " exec: " + cmd

def execOnAll_with_output(nodes, args, supressWarning = False):
	cmd = ""
	for arg in args:
		if cmd == "":
			cmd += arg
		else:
			cmd += " " + arg
	for node in nodes:
		output = SSH_exec_cmd_with_output(config["ssh_cert"], "core", node, cmd, supressWarning)
		print "Node: " + node
		print output

# run a shell script on one remote node
def runScript(node, args, sudo = False, supressWarning = False):
	if ".py" in args[0]:
		if sudo:
			fullcmd = "sudo /opt/bin/python"
		else:
			fullcmd = "/opt/bin/python"
	else:
		if sudo:
			fullcmd = "sudo bash"
		else:
			fullcmd = "bash"
	nargs = len(args)
	for i in range(nargs):
		if i==0:
			fullcmd += " " + os.path.basename(args[i])
		else:
			fullcmd += " " + args[i]
	srcdir = os.path.dirname(args[0])
	SSH_exec_cmd_with_directory(config["ssh_cert"], "core", node, srcdir, fullcmd, supressWarning)
		

# run a shell script on all remote nodes
def runScriptOnAll(nodes, args, sudo = False, supressWarning = False):
	for node in nodes:
		runScript( node, args, sudo = sudo, supressWarning = supressWarning)

if __name__ == '__main__':
	# the program always run at the current directory. 
	dirpath = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
	# print "Directory: " + dirpath
	os.chdir(dirpath)
	parser = argparse.ArgumentParser( prog='deploy.py',
		formatter_class=argparse.RawDescriptionHelpFormatter,
		description=textwrap.dedent('''\
Build, deploy and administer a DL workspace cluster.

Prerequest:
* Create config.yaml according to instruction in docs/deployment/Configuration.md.
* Metadata of deployed cluster is stored at deploy.

Command:
  build     Build USB iso/pxe-server used by deployment.
  deploy    Deploy DL workspace cluster.
  clean     Clean away a failed deployment.
  connect   [master|etcd|worker] num: Connect to either master, etcd or worker node (with an index number).
  partition [args] Manage data partitions. 
            ls: show all existing partitions. 
            create n: create n partitions of equal size.
            create s1 s2 ... sn: create n partitions;
              if s_i < 0, the partition is s_i GB, 
              if s_i > 0, the partition is in portitional to s_i. 
              We use parted mkpart percentage% to create partitions. As such, the minimum partition is 1% of a disk. 
  glusterFS [args] manage glusterFS on the cluster. 
            start: deploy a glusterFS and start gluster daemon set on the cluster.
            update: update a glusterFS on the cluster.
            stop: stop glusterFS service, data volume not removed. 
            clear: stop glusterFS service, and remove all data volumes. 
  execonall [cmd ... ] Execute the command on all nodes and print the output. 
  doonall [cmd ... ] Execute the command on all nodes. 
  runscriptonall [script] Execute the shell/python script on all nodes. 
  ''') )
	parser.add_argument("-y", "--yes", 
		help="Answer yes automatically for all prompt", 
		action="store_true" )
	parser.add_argument("-p", "--public", 
		help="Use public IP address to deploy/connect [e.g., Azure, AWS]", 
		action="store_true")
	parser.add_argument("--partition", 
		help = "Regular expression to operate on partitions, default = " + defPartition, 
		action="store",
		default = defPartition )
	parser.add_argument("-s", "--sudo", 
		help = "Execute scripts in sudo", 
		action="store_true" )
	parser.add_argument("--discoverserver", 
		help = "Specify an alternative discover server, default = " + discoverserver, 
		action="store", 
		default=discoverserver)
	parser.add_argument("--homeinserver", 
		help = "Specify an alternative home in server, default = " + homeinserver, 
		action="store", 
		default=homeinserver)
		
	parser.add_argument("command", 
		help = "See above for the list of valid command" )
	parser.add_argument('nargs', nargs=argparse.REMAINDER, 
		help="Additional command argument", 
		)
	args = parser.parse_args()
	# If necessary, show parsed arguments. 
	# print args
	discoverserver = args.discoverserver
	homeinserver = args.homeinserver
	config_file = os.path.join(dirpath,"config.yaml")
	# print "Config file: " + config_file
	if not os.path.exists(config_file):
		parser.print_help()
		print "ERROR: config.yaml does not exist!"
		exit()

	f = open(config_file)
	config = InitConfig()
	config.update(yaml.load(f))
	f.close()
	print config
	if os.path.exists("./deploy/clusterID.yml"):
		f = open("./deploy/clusterID.yml")
		tmp = yaml.load(f)
		f.close()
		if "clusterId" in tmp:
			config["clusterId"] = tmp["clusterId"]
	
	
	if args.yes:
		print "Use yes for default answer"
		defanswer = "yes"
		
	if args.public:
		ipAddrMetaname = "clientIP"
		
	command = args.command
	nargs = args.nargs

	if command =="clean":
		Clean_Deployment()
		exit()

	elif command == "connect":
			Check_Master_ETCD_Status()
			if len(nargs) < 1 or nargs[0] == "master":
				nodes = config["kubernetes_master_node"]
			elif nargs[0] == "etcd":
				nodes = config["etcd_node"]
			elif nargs[0] == "worker":
				nodes = config["worker_node"]
			else:
				parser.print_help()
				print "ERROR: must connect to either master, etcd or worker nodes"
				exit()
			if len(nodes) == 0:
				parser.print_help()
				print "ERROR: cannot find any node of the type to connect to"
				exit()
			num = 0
			if len(nargs) >= 2:
				num = int(nargs[1])
				if num < 0 or num >= len(nodes):
					num = 0
			nodename = nodes[num]
			SSH_connect( "./deploy/sshkey/id_rsa", "core", nodename)
			exit()

	elif command == "deploy" and "clusterId" in config:
		print "Detected previous cluster deployment, cluster ID: %s. \n To clean up the previous deployment, run 'python deploy.py clean' \n" % config["clusterId"]
		print "The current deployment has:\n"
		
		Check_Master_ETCD_Status()

		if "etcd_node" in config and len(config["etcd_node"]) >= int(config["etcd_node_num"]) and "kubernetes_master_node" in config and len(config["kubernetes_master_node"]) >= 1:
			print "Ready to deploy kubernetes master on %s, etcd cluster on %s.  " % (",".join(config["kubernetes_master_node"]), ",".join(config["etcd_node"]))
			Gen_Configs()
			response = raw_input_with_default("Deploy ETCD Nodes (y/n)?")
			if firstChar(response) == "y":
				Gen_ETCD_Certificates()
				Deploy_ETCD()			
			response = raw_input_with_default("Deploy Master Nodes (y/n)?")
			if firstChar(response) == "y":
				Gen_Master_Certificates()
				Deploy_Masters()

			response = raw_input_with_default("Allow Workers to register (y/n)?")
			if firstChar(response) == "y":

				urllib.urlretrieve (config["homeinserver"]+"/SetClusterInfo?clusterId=%s&key=etcd_endpoints&value=%s" %  (config["clusterId"],config["etcd_endpoints"]))
				urllib.urlretrieve (
				config["homeinserver"]+"/SetClusterInfo?clusterId=%s&key=api_server&value=%s" % (config["clusterId"],config["api_serviers"]))
			
#			response = raw_input_with_default("Create ISO file for deployment (y/n)?")
#			if firstChar(response) == "y":
#				Create_ISO()

#			response = raw_input_with_default("Create PXE docker image for deployment (y/n)?")
#			if firstChar(response) == "y":
#				Create_PXE()

		else:
			print "Cannot deploy cluster since there are insufficient number of etcd server or master server. \n To continue deploy the cluster we need at least %d etcd server(s) and 1 master server" % (int(config["etcd_node_num"]))

	elif command == "build":
		Init_Deployment()
		response = raw_input_with_default("Create ISO file for deployment (y/n)?")
		if firstChar(response) == "y":
			Create_ISO()
		response = raw_input_with_default("Create PXE docker image for deployment (y/n)?")
		if firstChar(response) == "y":
			Create_PXE()
	elif command == "updateworker":
		response = raw_input_with_default("Deploy Worker Nodes (y/n)?")
		if firstChar(response) == "y":
			Check_Master_ETCD_Status()
			Gen_Configs()
			UpdateWorkerNodes()

	elif command == "cleanworker":
		response = raw_input("Clean and Stop Worker Nodes (y/n)?")
		if firstChar( response ) == "y":
			Check_Master_ETCD_Status()
			Gen_Configs()			
			CleanWorkerNodes()

	elif command == "partition" and len(nargs) >= 1:
		Get_Config()
		nodes = GetNodes(config["clusterId"])
		if nargs[0] == "ls":
		# Display parititons.  
			nodesinfo = showPartitions(nodes, args.partition )
			
		elif nargs[0] == "create" and len(nargs) >= 2:
			partsInfo = map(float, nargs[1:])
			if len(partsInfo)==1 and partsInfo[0] < 30:
				partsInfo = [100.0]*int(partsInfo[0])
			nodesinfo = showPartitions(nodes, args.partition )
			print ("This operation will DELETE all existing partitions and repartition all data drives on the %d nodes to %d partitions of %s" % (len(nodes), len(partsInfo), str(partsInfo)) )
			response = raw_input ("Please type (REPARTITION) in ALL CAPITALS to confirm the operation ---> ")
			if response == "REPARTITION":
				repartitionNodes( nodes, nodesinfo, partsInfo)
			else:
				print "Repartition operation aborted...."
		else:
			parser.print_help()
			exit()
	
	elif command == "glusterFS" and len(nargs) >= 1:
		Get_Config()
		# nodes = GetNodes(config["clusterId"])
		# ToDo: change pending, schedule glusterFS on master & ETCD nodes, 
		if nargs[0] == "start" or nargs[0] == "update" or nargs[0] == "stop" or nargs[0] == "clear":
			nodes = GetWorkerNodes(config["clusterId"])
			nodesinfo = getPartitions(nodes, args.partition )
			if len(nargs) == 1:
				glusterFSargs = 1
			else:
				glusterFSargs = nargs[1]
			masternodes = GetETCDMasterNodes(config["clusterId"])
			gsFlag = ""
			if nargs[0] == "start":
				execOnAll(nodes, ["sudo modprobe dm_thin_pool"])
				gsFlag = "-g"
			elif nargs[0] == "stop":
				gsFlag = "--yes -g --abort"
			if nargs[0] == "clear":
				removeGlusterFSvolumes( masternodes, config["ipToHostname"], nodesinfo, glusterFSargs, nodes )
			else:
				startGlusterFS( masternodes, config["ipToHostname"], nodesinfo, glusterFSargs, flag = gsFlag )
			
				
		else:
			parser.print_help()
			exit()
			
	elif command == "doonall" and len(nargs)>=1:
		Get_Config()
		nodes = GetNodes(config["clusterId"])
		execOnAll(nodes, nargs)
		
	elif command == "execonall" and len(nargs)>=1:
		Get_Config()
		nodes = GetNodes(config["clusterId"])
		execOnAll_with_output(nodes, nargs)

	elif command == "runscriptonall" and len(nargs)>=1:
		Get_Config()
		nodes = GetNodes(config["clusterId"])
		runScriptOnAll(nodes, nargs, sudo = args.sudo )

		
	elif command == "cleanmasteretcd":
		response = raw_input("Clean and Stop Master/ETCD Nodes (y/n)?")
		if firstChar( response ) == "y":
			Check_Master_ETCD_Status()
			Gen_Configs()			
			Clean_Master()
			Clean_ETCD()

	elif command == "updatereport":
		response = raw_input_with_default("Deploy IP Reporting Service on Master and ETCD nodes (y/n)?")
		if firstChar(response) == "y":
			Check_Master_ETCD_Status()
			Gen_Configs()
			Update_Reporting_service()

	elif command == "display":
		Check_Master_ETCD_Status()

	elif command == "webui":
		Check_Master_ETCD_Status()
		Gen_Configs()		
		DeployWebUI()


	else:
		parser.print_help()
