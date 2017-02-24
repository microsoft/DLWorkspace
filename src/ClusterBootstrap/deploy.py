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
# Discover server is used to find IP address of the host, it need to be a well-known IP address 
# that is pingable. 

# CoreOS version and channels, further configurable. 
coreosversion = "1235.9.0"
coreoschannel = "stable"
coreosbaseurl = ""
discoverserver = "4.2.2.1" 
homeininterval = "600"
dockerregistry = "mlcloudreg.westus.cloudapp.azure.com:5000/dlworkspace"
verbose = False; 

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

def form_cluster_portal_URL(role, clusterID):
	returl = config["homeinserver"]+"/GetNodes?role="+role+"&clusterId="+clusterID
	if verbose:
		print "Retrieval portal " + returl
	return returl

def first_char(s):
	return (s.strip())[0].lower()
	

def raw_input_with_default(prompt):
	if defanswer == "":
		return raw_input(prompt)
	else:
		print prompt + " " + defanswer
		return defanswer
		



def copy_to_ISO():
	if not os.path.exists("./deploy/iso-creator"):
		os.system("mkdir -p ./deploy/iso-creator")
	os.system("cp --verbose ./template/pxe/tftp/splash.png ./deploy/iso-creator/splash.png")
	render_template_directory( "./template/pxe/tftp/usr/share/oem", "./deploy/iso-creator")
	render_template_directory( "./template/iso-creator", "./deploy/iso-creator")

# Certain configuration that is default in system 
def init_config():
	config = {}
	config["discoverserver"] = discoverserver
	config["homeinserver"] = homeinserver
	config["homeininterval"] = homeininterval
	config["dockerregistry"] = dockerregistry
	return config



# Test if a certain Config entry exist
def fetch_dictionary(dic, entry):
	if isinstance(entry, list):
		# print "Fetch " + str(dic) + "@" + str(entry) + "==" + str( dic[entry[0]] ) 
		if entry[0] in dic:
			if len(entry)<=1:
				return dic[entry[0]]
			else:
				return fetch_dictionary(dic[entry[0]], entry[1:])
		else:
			return None
	else:
		print "fetch_config expects to take a list, but gets " + str(entry)
	
# Test if a certain Config entry exist
def fetch_config(entry):
	return fetch_dictionary( config, entry )
	
# set a configuration, if an entry in configuration exists and is a certain type, then 
# use that entry, otherwise, use default value
# name: usually a string, the name of the configuration
# entry: a string list, used to mark the entry in the yaml file
# type: expect type of the configuration
# defval: default value
def update_one_config(name, entry, type, defval):
	val = fetch_config(entry)
	if val is None:
		config[name] = defval
	elif isinstance( val, type ):
		config[name] = val
		if verbose:
			print "config["+name+"]="+str(val)
	else:
		print "Error: Configuration " + name + " needs a " + str(type) +", but is given:" + str(val)

def update_config():
	update_one_config("coreosversion",["coreos","version"], basestring, coreosversion)
	update_one_config("coreoschannel",["coreos","channel"], basestring, coreoschannel)
	update_one_config("coreosbaseurl",["coreos","baseurl"], basestring, coreosbaseurl)
	if config["coreosbaseurl"] == "": 
		config["coreosusebaseurl"] = ""
	else:
		config["coreosusebaseurl"] = "-b "+config["coreosbaseurl"]
	
	
def add_ssh_key():
	keys = fetch_config(["sshKeys"])
	if isinstance( keys, list ):
		if not (config["sshkey"] in config["sshKeys"]):
			config["sshKeys"].append(config["sshkey"])
	else:
		config["sshKeys"] = []
		config["sshKeys"].append(config["sshkey"])
		
	
# Render scripts for kubenete nodes
def add_kubelet_config():
	renderfiles = []

# Render all deployment script used. 
	render_template_directory("./template/kubelet", "./deploy/kubelet")

	kubemaster_cfg_files = [f for f in os.listdir("./deploy/kubelet") if os.path.isfile(os.path.join("./deploy/kubelet", f))]
	for file in kubemaster_cfg_files:
		with open(os.path.join("./deploy/kubelet", file), 'r') as f:
			content = f.read()
		config[file] = base64.b64encode(content)

def add_dns_entries():
	addCoreOSNetwork = ""
	dnsEntries = fetch_config(["network", "externalDnsServers"])
	if dnsEntries is None:
		print "No additional DNS servers"
	elif isinstance( dnsEntries, list ):
		addCoreOSNetwork += "    - name: 20-dhcp.network\n"
		addCoreOSNetwork += "      runtime: true\n"
		addCoreOSNetwork += "      content: |\n"
		addCoreOSNetwork += "        [Match]\n"
		addCoreOSNetwork += "        Name=eth*\n"
		addCoreOSNetwork += "\n"
		addCoreOSNetwork += "        [Network]\n"
		addCoreOSNetwork += "        DHCP=yes\n"
		for dnsEntry in dnsEntries:
			addCoreOSNetwork += "        DNS="+dnsEntry+"\n"
		addCoreOSNetwork+="\n"
		print "Add additional Cloud Config entries: "
		print addCoreOSNetwork
	else:
		print "In Configuration file, network/externalDnsServers DNS entries is not a list, please double check ---> " + str(dnsEntries)
		exit()
	
	config["coreosnetwork"]=addCoreOSNetwork
	
def add_leading_spaces(content, nspaces):
	lines = content.splitlines()
	retstr = ""
	for line in lines:
		retstr += (" "*nspaces) + line + "\n"
	return retstr

# fill in additional entry of cloud config
def add_additional_cloud_config():
	coreOSWriteFilesEntries = fetch_config(["coreos", "write_files"])
	if not coreOSWriteFilesEntries is None:
		if isinstance( coreOSWriteFilesEntries, basestring ):
			coreOSWriteFilesEntriesAdj = add_leading_spaces( coreOSWriteFilesEntries, 2)
			config["coreoswritefiles"] = coreOSWriteFilesEntriesAdj
		else:
			print "In Configuration file, coreos/write_files should be a string" + str( coreOSWriteFilesEntries )
			exit()
	coreOSunitsEntries = fetch_config(["coreos", "units"])
	if not coreOSunitsEntries is None:
		if isinstance( coreOSunitsEntries, basestring ):
			coreOSunitsEntriesAdj = add_leading_spaces( coreOSunitsEntries, 4)
			config["coreosunits"] = coreOSunitsEntriesAdj
		else:
			print "In Configuration file, coreos/units should be a string" + str( coreOSunitsEntries )
			exit()
	
def init_deployment():
	if (os.path.isfile("./deploy/clusterID.yml")):
		
		clusterID = get_cluster_ID_from_file()
		response = raw_input_with_default("There is a cluster (ID:%s) deployment in './deploy', do you want to keep the existing ssh key and CA certificates (y/n)?" % clusterID)
		if first_char(response) == "n":
			backup_keys()
			gen_SSH_key()
			gen_CA_certificates()
			gen_worker_certificates()
			backup_keys()
	else:
		gen_SSH_key()
		gen_CA_certificates()
		gen_worker_certificates()
		backup_keys()

	clusterID = get_cluster_ID_from_file()

	f = open("./deploy/sshkey/id_rsa.pub")
	sshkey_public = f.read()
	f.close()



	print "Cluster Id is : %s" % clusterID 

	config["clusterId"] = clusterID
	config["sshkey"] = sshkey_public
	add_ssh_key()

	add_kubelet_config()
	add_additional_cloud_config()

	template_file = "./template/cloud-config/cloud-config-master.yml"
	target_file = "./deploy/cloud-config/cloud-config-master.yml"
	config["role"] = "master"
	
	render_template(template_file, target_file)

	template_file = "./template/cloud-config/cloud-config-etcd.yml"
	target_file = "./deploy/cloud-config/cloud-config-etcd.yml"
	
	config["role"] = "etcd"
	render_template(template_file, target_file)

	# Prepare to Generate the ISO image. 
	# Using files in PXE as template. 
	copy_to_ISO()



	template_file = "./deploy/iso-creator/mkimg.sh.template"
	target_file = "./deploy/iso-creator/mkimg.sh"
	render_template( template_file, target_file )

	with open("./deploy/ssl/ca/ca.pem", 'r') as f:
		content = f.read()
	config["ca.pem"] = base64.b64encode(content)

	with open("./deploy/ssl/kubelet/apiserver.pem", 'r') as f:
		content = f.read()
	config["apiserver.pem"] = base64.b64encode(content)
	config["worker.pem"] = base64.b64encode(content)

	with open("./deploy/ssl/kubelet/apiserver-key.pem", 'r') as f:
		content = f.read()
	config["apiserver-key.pem"] = base64.b64encode(content)
	config["worker-key.pem"] = base64.b64encode(content)

	add_kubelet_config()
	add_additional_cloud_config()

	template_file = "./template/cloud-config/cloud-config-worker.yml"
	target_file = "./deploy/cloud-config/cloud-config-worker.yml"
	render_template( template_file, target_file )

def check_node_availability(ipAddress):
	# print "Check node availability on: " + str(ipAddress)
	status = os.system('ssh -o "StrictHostKeyChecking no" -i deploy/sshkey/id_rsa -oBatchMode=yes core@%s hostname > /dev/null' % ipAddress)
	#status = sock.connect_ex((ipAddress,22))
	return status == 0


def get_ETCD_master_nodes(clusterId):
	output = urllib.urlopen(form_cluster_portal_URL("etcd", clusterId)).read()
	output = json.loads(json.loads(output))
	Nodes = []
	NodesInfo = [node for node in output["nodes"] if "time" in node]
	if not "ipToHostname" in config:
		config["ipToHostname"] = {}
	for node in NodesInfo:
		if not node[ipAddrMetaname] in Nodes and check_node_availability(node[ipAddrMetaname]):
			hostname = get_host_name(node[ipAddrMetaname])
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
	
def get_worker_nodes(clusterId):
	output = urllib.urlopen(form_cluster_portal_URL("worker", clusterId)).read()
	output = json.loads(json.loads(output))
	Nodes = []
	NodesInfo = [node for node in output["nodes"] if "time" in node]
	if not "ipToHostname" in config:
		config["ipToHostname"] = {}
	for node in NodesInfo:
		if not node[ipAddrMetaname] in Nodes and check_node_availability(node[ipAddrMetaname]):
			hostname = get_host_name(node[ipAddrMetaname])
			Nodes.append(node[ipAddrMetaname])
			config["ipToHostname"][node[ipAddrMetaname]] = hostname
	config["worker_node"] = Nodes
	return Nodes
	
def get_nodes(clusterId):
	output1 = urllib.urlopen(form_cluster_portal_URL("worker", clusterId)).read()
	nodes = json.loads(json.loads(output1))["nodes"]
	output3 = urllib.urlopen(form_cluster_portal_URL("etcd", clusterId)).read()
	nodes = nodes + ( json.loads(json.loads(output3))["nodes"] )
	# print nodes
	Nodes = []
	NodesInfo = [node for node in nodes if "time" in node]
	if not "ipToHostname" in config:
		config["ipToHostname"] = {}
	for node in NodesInfo:
		if not node[ipAddrMetaname] in Nodes and check_node_availability(node[ipAddrMetaname]):
			hostname = get_host_name(node[ipAddrMetaname])
			Nodes.append(node[ipAddrMetaname])
			config["ipToHostname"][node[ipAddrMetaname]] = hostname
	config["nodes"] = Nodes
	return Nodes

def check_master_ETCD_status():
	masterNodes = []
	etcdNodes = []
	print "==============================================="
	print "Checking Available Nodes for Deployment..."
	if "clusterId" in config:
		get_ETCD_master_nodes(config["clusterId"])
		get_worker_nodes(config["clusterId"])
	print "==============================================="
	print "Activate Master Node(s): %s\n %s \n" % (len(config["kubernetes_master_node"]),",".join(config["kubernetes_master_node"]))
	print "Activate ETCD Node(s):%s\n %s \n" % (len(config["etcd_node"]),",".join(config["etcd_node"]))
	print "Activate Worker Node(s):%s\n %s \n" % (len(config["worker_node"]),",".join(config["worker_node"]))

def clean_deployment():
	print "==============================================="
	print "Cleaning previous deployment..."	
	if (os.path.isfile("./deploy/clusterID.yml")):
		backup_keys()
	os.system("rm -r ./deploy/*")


def gen_CA_certificates():
	utils.render_template_directory("./template/ssl", "./deploy/ssl",config)
	os.system("cd ./deploy/ssl && bash ./gencerts_ca.sh")

def gen_worker_certificates():
	utils.render_template_directory("./template/ssl", "./deploy/ssl",config)
	os.system("cd ./deploy/ssl && bash ./gencerts_kubelet.sh")	

def gen_master_certificates():
	config["apiserver_ssl_dns"] = ""
	config["apiserver_ssl_ip"] = "IP.1 = 10.3.0.1\nIP.2 = 127.0.0.1\n"+ "\n".join(["IP."+str(i+3)+" = "+ip for i,ip in enumerate(config["kubernetes_master_node"])])

	utils.render_template_directory("./template/ssl", "./deploy/ssl",config)

	os.system("cd ./deploy/ssl && bash ./gencerts_master.sh")


def gen_ETCD_certificates():

	config["etcd_ssl_dns"] = ""
	config["etcd_ssl_ip"] = "IP.1 = 127.0.0.1\n" + "\n".join(["IP."+str(i+2)+" = "+ip for i,ip in enumerate(config["etcd_node"])])
	utils.render_template_directory("./template/ssl", "./deploy/ssl",config)


	os.system("cd ./deploy/ssl && ./gencerts_etcd.sh")	



def gen_configs():
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

	config["discovery_url"] = get_ETCD_discovery_URL(int(config["etcd_node_num"]))

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
	add_ssh_key()
	check_config(config)

	render_template_directory("./template/etcd", "./deploy/etcd")
	render_template_directory("./template/master", "./deploy/master")
	render_template_directory("./template/web-docker", "./deploy/web-docker")
	render_template_directory("./template/kube-addons", "./deploy/kube-addons")

def get_config():
	if "ssh_cert" not in config and os.path.isfile("./deploy/sshkey/id_rsa"):
		config["ssh_cert"] = "./deploy/sshkey/id_rsa"
		config["etcd_user"] = "core"
		config["kubernetes_master_ssh_user"] = "core"

	
	f = open(config["ssh_cert"])
	sshkey_public = f.read()
	f.close()

	config["sshkey"] = sshkey_public
	add_ssh_key()


def update_reporting_service():
	kubernetes_masters = config["kubernetes_master_node"]
	kubernetes_master_user = config["kubernetes_master_ssh_user"]

	for kubernetes_master in kubernetes_masters:
		print "==============================================="
		print "Updating report service on master %s... " % kubernetes_master

		SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo systemctl stop reportcluster")
		scp(config["ssh_cert"],"./deploy/kebelet/report.sh","/home/%s/report.sh" % kubernetes_master_user , kubernetes_master_user, kubernetes_master )
		SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo mv /home/%s/report.sh /opt/report.sh" % (kubernetes_master_user))

		SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo systemctl start reportcluster")


	etcd_servers = config["etcd_node"]
	etcd_server_user = config["etcd_user"]


	for etcd_server_address in etcd_servers:
		print "==============================================="
		print "Updating report service on etcd node %s... " % etcd_server_address

		SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo systemctl stop reportcluster")
		scp(config["ssh_cert"],"./deploy/kubelet/report.sh","/home/%s/report.sh" % etcd_server_user , etcd_server_user, etcd_server_address )
		SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo mv /home/%s/report.sh /opt/report.sh" % (etcd_server_user))

		SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo systemctl start reportcluster")

def clean_master():
	kubernetes_masters = config["kubernetes_master_node"]
	kubernetes_master_user = config["kubernetes_master_ssh_user"]

	for kubernetes_master in kubernetes_masters:
		print "==============================================="
		print "Clean up kubernetes master %s... (It is OK to see 'Errors' in this section)" % kubernetes_master

		SSH_exec_script(config["ssh_cert"],kubernetes_master_user, kubernetes_master, "./deploy/master/cleanup-master.sh")


def deploy_master(kubernetes_master):
		print "==============================================="
		kubernetes_master_user = config["kubernetes_master_ssh_user"]
		print "starting kubernetes master on %s..." % kubernetes_master

		config["master_ip"] = kubernetes_master
		render_template("./template/master/kube-apiserver.yaml","./deploy/master/kube-apiserver.yaml")
		render_template("./template/master/kubelet.service","./deploy/master/kubelet.service")
		render_template("./template/master/pre-master-deploy.sh","./deploy/master/pre-master-deploy.sh")
		render_template("./template/master/post-master-deploy.sh","./deploy/master/post-master-deploy.sh")


		SSH_exec_script(config["ssh_cert"],kubernetes_master_user, kubernetes_master, "./deploy/master/pre-master-deploy.sh")


		with open("./deploy/master/deploy.list","r") as f:
			deploy_files = [s.split(",") for s in f.readlines() if len(s.split(",")) == 2]
		for (source, target) in deploy_files:
			if (os.path.isfile(source.strip()) or os.path.exists(source.strip())):
				sudo_scp(config["ssh_cert"],source.strip(),target.strip(),kubernetes_master_user,kubernetes_master)


		SSH_exec_script(config["ssh_cert"],kubernetes_master_user, kubernetes_master, "./deploy/master/post-master-deploy.sh")

def deploy_masters():

	print "==============================================="
	print "Prepare to deploy kubernetes master"
	print "waiting for ETCD service is ready..."
	check_etcd_service()
	print "==============================================="
	print "Generating master configuration files..."

	kubernetes_masters = config["kubernetes_master_node"]
	kubernetes_master_user = config["kubernetes_master_ssh_user"]

	renderfiles = []
	kubemaster_cfg_files = [f for f in os.listdir("./template/master") if os.path.isfile(os.path.join("./template/master", f))]
	for file in kubemaster_cfg_files:
		render_template(os.path.join("./template/master", file),os.path.join("./deploy/master", file))
	kubemaster_cfg_files = [f for f in os.listdir("./template/kube-addons") if os.path.isfile(os.path.join("./template/kube-addons", f))]
	for file in kubemaster_cfg_files:
		render_template(os.path.join("./template/kube-addons", file),os.path.join("./deploy/kube-addons", file))


	urllib.urlretrieve ("http://ccsdatarepo.westus.cloudapp.azure.com/data/kube/kubelet/kubelet", "./deploy/bin/kubelet")
	urllib.urlretrieve ("http://ccsdatarepo.westus.cloudapp.azure.com/data/kube/kubelet/kubectl", "./deploy/bin/kubectl")
	
	clean_master()

	for i,kubernetes_master in enumerate(kubernetes_masters):
		deploy_master(kubernetes_master)


	SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_masters[0], "until curl -q http://127.0.0.1:8080/version/ ; do sleep 5; echo 'waiting for master...'; done;  sudo /opt/bin/kubectl create -f /opt/addons/kube-addons/", False)



def uncordon_master():
	get_ETCD_master_nodes(config["clusterId"])
	kubernetes_masters = config["kubernetes_master_node"]
	kubernetes_master_user = config["kubernetes_master_ssh_user"]
	for i,kubernetes_master in enumerate(kubernetes_masters):
		SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo /opt/bin/kubectl uncordon \$HOSTNAME")



def clean_etcd():
	etcd_servers = config["etcd_node"]
	etcd_server_user = config["etcd_user"]

	for etcd_server_address in etcd_servers:
		print "==============================================="
		print "Clean up etcd servers %s... (It is OK to see 'Errors' in this section)" % etcd_server_address		
		#SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "timeout 10 docker rm -f \$(timeout 3 docker ps -q -a)")
		cmd = "sudo systemctl stop etcd3; "
		cmd += "sudo rm -r /var/etcd/data ; "
		cmd += "sudo rm -r /etc/etcd/ssl; "
		SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, cmd )

def check_etcd_service():
	print "waiting for ETCD service is ready..."
	etcd_servers = config["etcd_node"]
	cmd = "curl --cacert %s --cert %s --key %s 'https://%s:2379/v2/keys'" % ("./deploy/ssl/etcd/ca.pem","./deploy/ssl/etcd/etcd.pem","./deploy/ssl/etcd/etcd-key.pem", etcd_servers[0])
	while os.system(cmd) != 0:
		time.sleep(5)
	print "ETCD service is ready to use..."

def deploy_ETCD_docker():
	etcd_servers = config["etcd_node"]
	etcd_server_user = config["etcd_user"]
	render_template_directory("./template/etcd", "./deploy/etcd")

	clean_etcd()

	for etcd_server_address in etcd_servers:
		#print "==============================================="
		#print "deploy configuration files to web server..."
		#scp(config["ssh_cert"],"./deploy","/var/www/html", config["webserver_user"], config["webserver"] )

		print "==============================================="
		print "deploy certificates to etcd server %s" % etcd_server_address
		
		SSH_exec_cmd (config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo mkdir -p /etc/kubernetes/ssl") 
		SSH_exec_cmd (config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo chown %s /etc/kubernetes/ssl " % (etcd_server_user)) 
		scp(config["ssh_cert"],"./deploy/ssl/etcd","/etc/kubernetes/ssl", etcd_server_user, etcd_server_address )

		print "==============================================="
		print "starting etcd service on %s ..." % etcd_server_address


		config["etcd_node_ip"] = etcd_server_address
		render_template("./template/etcd/docker_etcd.sh","./deploy/etcd/docker_etcd.sh")
		render_template("./template/etcd/docker_etcd_ssl.sh","./deploy/etcd/docker_etcd_ssl.sh")

		scp(config["ssh_cert"],"./deploy/etcd/docker_etcd.sh","/home/%s/docker_etcd.sh" % etcd_server_user, etcd_server_user, etcd_server_address )
		SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "chmod +x /home/%s/docker_etcd.sh" % etcd_server_user)

		scp(config["ssh_cert"],"./deploy/etcd/docker_etcd_ssl.sh","/home/%s/docker_etcd_ssl.sh" % etcd_server_user, etcd_server_user, etcd_server_address )
		SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "chmod +x /home/%s/docker_etcd_ssl.sh" % etcd_server_user)


		scp(config["ssh_cert"],"./deploy/etcd/init_network.sh","/home/%s/init_network.sh" % etcd_server_user, etcd_server_user, etcd_server_address )
		SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "chmod +x /home/%s/init_network.sh" % etcd_server_user)

		SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "/home/%s/docker_etcd_ssl.sh" % etcd_server_user)

	print "==============================================="
	print "init etcd service on %s ..."  % etcd_servers[0]


	check_etcd_service()


	scp(config["ssh_cert"],"./deploy/etcd/init_network.sh","/home/%s/init_network.sh" % etcd_server_user, etcd_server_user, etcd_server_address )
	SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_servers[0], "chmod +x /home/%s/init_network.sh" % etcd_server_user)
	SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_servers[0], "/home/%s/init_network.sh" % etcd_server_user)


def deploy_ETCD():
	etcd_servers = config["etcd_node"]
	etcd_server_user = config["etcd_user"]
	
	clean_etcd()

	for i,etcd_server_address in enumerate(etcd_servers):
		#print "==============================================="
		#print "deploy configuration files to web server..."
		#scp(config["ssh_cert"],"./deploy","/var/www/html", config["webserver_user"], config["webserver"] )

		SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo systemctl stop etcd3")

		print "==============================================="
		print "deploy certificates to etcd server %s" % etcd_server_address
		
		SSH_exec_cmd (config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo mkdir -p /etc/etcd/ssl") 
		SSH_exec_cmd (config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo chown %s /etc/etcd/ssl " % (etcd_server_user)) 
		scp(config["ssh_cert"],"./deploy/ssl/etcd/ca.pem","/etc/etcd/ssl", etcd_server_user, etcd_server_address )
		scp(config["ssh_cert"],"./deploy/ssl/etcd/etcd.pem","/etc/etcd/ssl", etcd_server_user, etcd_server_address )
		scp(config["ssh_cert"],"./deploy/ssl/etcd/etcd-key.pem","/etc/etcd/ssl", etcd_server_user, etcd_server_address )

		print "==============================================="
		print "starting etcd service on %s ..." % etcd_server_address


		config["etcd_node_ip"] = etcd_server_address
		config["hostname"] = config["cluster_name"]+"-etcd"+str(i+1)
		render_template("./template/etcd/etcd3.service","./deploy/etcd/etcd3.service")
		render_template("./template/etcd/etcd_ssl.sh","./deploy/etcd/etcd_ssl.sh")

		sudo_scp(config["ssh_cert"],"./deploy/etcd/etcd3.service","/etc/systemd/system/etcd3.service", etcd_server_user, etcd_server_address )

		sudo_scp(config["ssh_cert"],"./deploy/etcd/etcd_ssl.sh","/opt/etcd_ssl.sh", etcd_server_user, etcd_server_address )
		SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "chmod +x /opt/etcd_ssl.sh")
		SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo /opt/etcd_ssl.sh")



	print "==============================================="
	print "init etcd service on %s ..."  % etcd_servers[0]


	print "waiting for ETCD service is ready..."
	cmd = "curl --cacert %s --cert %s --key %s 'https://%s:2379/v2/keys'" % ("./deploy/ssl/etcd/ca.pem","./deploy/ssl/etcd/etcd.pem","./deploy/ssl/etcd/etcd-key.pem", etcd_servers[0])
	while os.system(cmd) != 0:
		print "ETCD service is NOT ready, waiting for 5 seconds..."
		time.sleep(5)
	print "ETCD service is ready to use..."



	render_template("./template/etcd/init_network.sh","./deploy/etcd/init_network.sh")
	SSH_exec_script( config["ssh_cert"], etcd_server_user, etcd_servers[0], "./deploy/etcd/init_network.sh")


def create_ISO():
	imagename = "./deploy/iso/dlworkspace-cluster-deploy-"+config["cluster_name"]+".iso"
	os.system("mkdir -p ./deploy/iso")
	os.system("cd deploy/iso-creator && bash ./mkimg.sh -v "+config["coreosversion"] + " -l "+ config["coreoschannel"]+" -a")
	os.system("mv deploy/iso-creator/coreos-"+config["coreosversion"]+".iso "+imagename )
	os.system("rm -rf ./iso-creator/syslinux-6.03*")
	os.system("rm -rf ./iso-creator/coreos-*")
	print "Please find the bootable USB image at: "+imagename
	print 


def create_PXE():
	os.system("rm -r ./deploy/pxe")
	os.system("mkdir -p ./deploy/docker")
	render_template_directory("./template/pxe", "./deploy/pxe")
	# cloud-config should be rendered already
	os.system("cp -r ./deploy/cloud-config/* ./deploy/pxe/tftp/usr/share/oem")
	dockername = "dlworkspace-pxe:%s" % config["cluster_name"] 
	os.system("docker build -t %s deploy/pxe" % dockername)
	tarname = "deploy/docker/dlworkspace-pxe-%s.tar" % config["cluster_name"]
	
	os.system("docker save " + dockername + " > " + tarname )
	print ("A DL workspace docker is built at: "+ dockername)
	print ("It is also saved as a tar file to: "+ tarname)
	
	#os.system("docker rmi dlworkspace-pxe:%s" % config["cluster_name"])

def clean_worker_nodes():
	workerNodes = get_worker_nodes(config["clusterId"])
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



def update_worker_node(nodeIP):
	print "==============================================="
	print "updating worker node: %s ..."  % nodeIP
	SSH_exec_cmd_with_directory(config["ssh_cert"], "core", nodeIP, "scripts", "bash --verbose stop-worker.sh")

	sudo_scp(config["ssh_cert"],"./deploy/kubelet/options.env","/etc/flannel/options.env", "core", nodeIP )

	sudo_scp(config["ssh_cert"],"./deploy/kubelet/kubelet.service","/etc/systemd/system/kubelet.service", "core", nodeIP )

	sudo_scp(config["ssh_cert"],"./deploy/kubelet/worker-kubeconfig.yaml","/etc/kubernetes/worker-kubeconfig.yaml", "core", nodeIP )
	
	sudo_scp(config["ssh_cert"],"./deploy/kubelet/kubelet.sh","/opt/kubelet.sh", "core", nodeIP )

	sudo_scp(config["ssh_cert"],"./deploy/bin/kubelet","/opt/bin/kubelet", "core", nodeIP )
	SSH_exec_cmd(config["ssh_cert"], "core", nodeIP, "sudo chmod +x /opt/bin/kubelet")


	with open("./deploy/ssl/ca/ca.pem", 'r') as f:
		content = f.read()
	config["ca.pem"] = base64.b64encode(content)

	with open("./deploy/ssl/kubelet/apiserver.pem", 'r') as f:
		content = f.read()
	config["apiserver.pem"] = base64.b64encode(content)
	config["worker.pem"] = base64.b64encode(content)

	with open("./deploy/ssl/kubelet/apiserver-key.pem", 'r') as f:
		content = f.read()
	config["apiserver-key.pem"] = base64.b64encode(content)
	config["worker-key.pem"] = base64.b64encode(content)


	sudo_scp(config["ssh_cert"],"./deploy/ssl/ca/ca.pem","/etc/kubernetes/ssl/ca.pem", "core", nodeIP )
	sudo_scp(config["ssh_cert"],"./deploy/ssl/ca/ca.pem","/etc/ssl/etcd/ca.pem", "core", nodeIP )

	sudo_scp(config["ssh_cert"],"./deploy/ssl/kubelet/apiserver.pem","/etc/kubernetes/ssl/worker.pem", "core", nodeIP )
	sudo_scp(config["ssh_cert"],"./deploy/ssl/kubelet/apiserver.pem","/etc/ssl/etcd/apiserver.pem", "core", nodeIP )

	sudo_scp(config["ssh_cert"],"./deploy/ssl/kubelet/apiserver-key.pem","/etc/kubernetes/ssl/worker-key.pem", "core", nodeIP )
	sudo_scp(config["ssh_cert"],"./deploy/ssl/kubelet/apiserver-key.pem","/etc/ssl/etcd/apiserver-key.pem", "core", nodeIP )

	sudo_scp(config["ssh_cert"],"./deploy/kubelet/report.sh","/opt/report.sh", "core", nodeIP )
	sudo_scp(config["ssh_cert"],"./deploy/kubelet/reportcluster.service","/etc/systemd/system/reportcluster.service", "core", nodeIP )

	SSH_exec_cmd_with_directory(config["ssh_cert"], "core", nodeIP, "scripts", "bash --verbose start-worker.sh")

	print "done!"


def update_worker_nodes():
	os.system('sed "s/##etcd_endpoints##/%s/" "./deploy/kubelet/options.env.template" > "./deploy/kubelet/options.env"' % config["etcd_endpoints"].replace("/","\\/"))
	os.system('sed "s/##api_serviers##/%s/" ./deploy/kubelet/kubelet.service.template > ./deploy/kubelet/kubelet.service' % config["api_serviers"].replace("/","\\/"))
	os.system('sed "s/##api_serviers##/%s/" ./deploy/kubelet/worker-kubeconfig.yaml.template > ./deploy/kubelet/worker-kubeconfig.yaml' % config["api_serviers"].replace("/","\\/"))
	
	urllib.urlretrieve ("http://ccsdatarepo.westus.cloudapp.azure.com/data/kube/kubelet/kubelet", "./deploy/bin/kubelet")

	workerNodes = get_worker_nodes(config["clusterId"])
	for node in workerNodes:
		update_worker_node(node)

	os.system("rm ./deploy/kubelet/options.env")
	os.system("rm ./deploy/kubelet/kubelet.service")
	os.system("rm ./deploy/kubelet/worker-kubeconfig.yaml")

	#if len(config["kubernetes_master_node"]) > 0:
		#SSH_exec_cmd(config["ssh_cert"], "core", config["kubernetes_master_node"][0], "sudo /opt/bin/kubelet get nodes")

def create_MYSQL_for_WebUI():
	#todo: create a mysql database, and set "mysql-hostname", "mysql-username", "mysql-password", "mysql-database"
	pass

def build_restful_API_docker():
	dockername = "%s/%s-restfulapi" %  (config["dockerregistry"],config["cluster_name"])
	tarname = "deploy/docker/restfulapi-%s.tar" % config["cluster_name"]

	os.system("docker rmi %s" % dockername)
	os.system("docker build -t %s ../docker-images/RestfulAPI" % dockername)

	if not os.path.exists("deploy/docker"):
		os.system("mkdir -p %s" % "deploy/docker")

	os.system("rm %s" % tarname )
	os.system("docker save " + dockername + " > " + tarname )

def deploy_restful_API_on_node(ipAddress):

	masterIP = ipAddress
	dockername = "%s/dlws-restfulapi" %  (config["dockerregistry"])

	# if user didn't give storage server information, use CCS public storage in default. 
	if "nfs-server" not in config:
		config["nfs-server"] = "10.196.44.241:/mnt/data"

	if not os.path.exists("./deploy/RestfulAPI"):
		os.system("mkdir -p ./deploy/RestfulAPI")
	render_template("../utils/config.yaml.template","./deploy/RestfulAPI/config.yaml")
	sudo_scp(config["ssh_cert"],"./deploy/RestfulAPI/config.yaml","/etc/RestfulAPI/config.yaml", "core", masterIP )


	SSH_exec_cmd(config["ssh_cert"], "core", masterIP, "sudo mkdir -p /dlws-data && sudo mount %s /dlws-data" % config["nfs-server"])


	SSH_exec_cmd(config["ssh_cert"], "core", masterIP, "docker rm -f restfulapi; docker rm -f jobScheduler ; docker pull %s ; docker run -d -p 5000:5000 --restart always -v /etc/RestfulAPI:/RestfulAPI --name restfulapi %s ; docker run -d -v /dlws-data:/dlws-data -v /etc/RestfulAPI:/RestfulAPI --restart always --name jobScheduler %s /runScheduler.sh ;" % (dockername,dockername,dockername))


	print "==============================================="
	print "restful api is running at: http://%s:5000" % masterIP
	config["restapi"] = "http://%s:5000" %  masterIP

def build_webUI_docker():
	os.system("docker rmi %s" % dockername)
	os.system("docker build -t %s ../docker-images/WebUI" % dockername)

def deploy_webUI_on_node(ipAddress):

	sshUser = "core"
	webUIIP = ipAddress
	dockername = "%s/dlws-webui" %  (config["dockerregistry"])

	if "restapi" not in config:
		print "!!!! Cannot deploy Web UI - RestfulAPI is not deployed"
		return

	if not os.path.exists("./deploy/WebUI"):
		os.system("mkdir -p ./deploy/WebUI")
	render_template("./template/WebUI/appsettings.json.template","./deploy/WebUI/appsettings.json")
	sudo_scp(config["ssh_cert"],"./deploy/WebUI/appsettings.json","/etc/WebUI/appsettings.json", "core", webUIIP )

	SSH_exec_cmd(config["ssh_cert"], sshUser, webUIIP, "docker pull %s ; docker rm -f webui ; docker run -d -p 80:80 -v /etc/WebUI:/WebUI --restart always --name webui %s ;" % (dockername,dockername))


	print "==============================================="
	print "Web UI is running at: http://%s" % webUIIP


def deploy_webUI():
	masterIP = config["kubernetes_master_node"][0]
	deploy_restful_API_on_node(masterIP)
	deploy_webUI_on_node(masterIP)

# Get disk partition information of a node
def get_partions_of_node(node, prog):
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
def get_partitions(nodes, regexp):
	prog = re.compile("("+regexp+")")
	nodesinfo = {}
	for node in nodes:
		partinfo = get_partions_of_node( node, prog )
		if not(partinfo is None):
			nodesinfo[node] = partinfo
	return nodesinfo

# Print out the Partition information of all nodes in a cluster	
def show_partitions(nodes, regexp):
	nodesinfo = get_partitions(nodes, regexp)
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
def calculate_partitions( capacity, partitionConfig):
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
def repartition_nodes(nodes, nodesinfo, partitionConfig):
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
			partitionSize = calculate_partitions( deviceinfo["capacity"], partitionConfig)
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
	print "Please note, it is OK to ignore message of Warning: Not all of the space available to /dev/___ appears to be used. The current default partition method optimizes for speed, rather to use all disk capacity..."
	()
	
def glusterFS_copy():
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
def start_glusterFS( masternodes, ipToHostname, nodesinfo, glusterFSargs, flag = "-g"):
	glusterFSJson = GlusterFSJson(ipToHostname, nodesinfo, glusterFSargs)
	glusterFSJsonFilename = "deploy/storage/glusterFS/topology.json"
	print "Write GlusterFS configuration file to: " + glusterFSJsonFilename
	glusterFSJson.dump(glusterFSJsonFilename)
	glusterFS_copy()
	rundir = "/tmp/start_glusterFS"
	# use the same heketidocker as in heketi deployment
	heketidocker = "heketi/heketi:latest"
	remotecmd = "docker pull "+heketidocker+"; "
	remotecmd += "docker run -v "+rundir+":"+rundir+" --rm --entrypoint=cp "+heketidocker+" /usr/bin/heketi-cli "+rundir+"; "
	remotecmd += "sudo bash ./gk-deploy "
	remotecmd += flag
	SSH_exec_cmd_with_directory( config["ssh_cert"], "core", masternodes[0], "deploy/storage/glusterFS", remotecmd, dstdir = rundir )
	
# Deploy glusterFS on a cluster
def remove_glusterFS_volumes( masternodes, ipToHostname, nodesinfo, glusterFSargs, nodes ):
	start_glusterFS( masternodes, ipToHostname, nodesinfo, glusterFSargs, flag = "-g --yes --abort")
	for node in nodes:
		glusterFS_copy()
		rundir = "/tmp/glusterFSAdmin"
		remotecmd = "sudo python RemoveLVM.py "
		SSH_exec_cmd_with_directory( config["ssh_cert"], "core", node, "deploy/storage/glusterFS", remotecmd, dstdir = rundir )

def exec_on_all(nodes, args, supressWarning = False):
	cmd = ""
	for arg in args:
		if cmd == "":
			cmd += arg
		else:
			cmd += " " + arg
	for node in nodes:
		SSH_exec_cmd(config["ssh_cert"], "core", node, cmd)
		print "Node: " + node + " exec: " + cmd

def exec_on_all_with_output(nodes, args, supressWarning = False):
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
def run_script(node, args, sudo = False, supressWarning = False):
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
def run_script_on_all(nodes, args, sudo = False, supressWarning = False):
	for node in nodes:
		run_script( node, args, sudo = sudo, supressWarning = supressWarning)
		
def add_mac_dictionary( dic, name, mac):
	mac = mac.lower() 
	if mac in dic:
		if dic[mac] != name:
			print "Error, two mac entries " + mac + "for machine " + dic[mac] + ", " + name
			exit()
	else:
		dic[mac] = name
		
def create_mac_dictionary( machineEntry ):
	dic = {}
	for name in machineEntry:
		machineInfo = machineEntry[name]
		if "mac" in machineInfo:
			macs = machineInfo["mac"]
			if isinstance(macs, basestring):
				add_mac_dictionary(dic, name, macs)
			elif isinstance(macs, list):
				for mac in macs:
					add_mac_dictionary(dic, name, mac)
			else:
				print "Error, machine " + name + ", mac entry is of unknown type: " + str(macs)
	#print dic
	return dic
	
def set_host_names_by_lookup():
	domainEntry = fetch_config( ["network", "domain"] )
	machineEntry = fetch_config( ["machines"] )
	if machineEntry is None:
		print "Unable to set host name as there are no machines information in the configuration file. "
	else:
		dic_macs_to_hostname = create_mac_dictionary(machineEntry)
		nodes = get_nodes(config["clusterId"])
		for node in nodes:
			macs = get_mac_address(node, show=False )
			namelist = []
			for mac in macs:
				usemac = mac.lower()
				if usemac in dic_macs_to_hostname:
					namelist.append(dic_macs_to_hostname[usemac])
			if len(namelist) > 1:
				print "Error, machine with mac "+str(macs)+" has more than 1 name entries " +str(namelist)
			elif len(namelist) == 0:
				print "Warning, cannot find an entry for machine with mac "+str(macs)
			else:
				if isinstance( domainEntry, basestring):
					usename = namelist[0] + "." + domainEntry
				else:
					usename = namelist[0]
				cmd = "sudo hostnamectl set-hostname " + usename
				print "Set hostname of node " + node + " ... " + usename
				SSH_exec_cmd( config["ssh_cert"], "core", node, cmd )

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
  hostname  [args] manage hostname on the cluster
            set: set hostname
  uncordon  allow etcd/master nodes to be scheduled jobs 
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
  listmac   display mac address of the cluster notes
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
	parser.add_argument("-v", "--verbose", 
		help = "verbose print", 
		action="store_true")
		
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
	if args.verbose: 
		verbose = True
	
	config = init_config()
	# Cluster Config
	config_cluster = os.path.join(dirpath,"cluster.yaml")
	if os.path.exists(config_cluster):
		config.update(yaml.load(open(config_cluster)))

	config_file = os.path.join(dirpath,"config.yaml")
	# print "Config file: " + config_file
	if not os.path.exists(config_file):
		parser.print_help()
		print "ERROR: config.yaml does not exist!"
		exit()
	
	
	f = open(config_file)
	config.update(yaml.load(f))
	f.close()
	# print config
	if os.path.exists("./deploy/clusterID.yml"):
		f = open("./deploy/clusterID.yml")
		tmp = yaml.load(f)
		f.close()
		if "clusterId" in tmp:
			config["clusterId"] = tmp["clusterId"]
	update_config()
	
	
	if args.yes:
		print "Use yes for default answer"
		defanswer = "yes"
		
	if args.public:
		ipAddrMetaname = "clientIP"
		
	command = args.command
	nargs = args.nargs

	if command =="clean":
		clean_deployment()
		exit()

	elif command == "connect":
			check_master_ETCD_status()
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
		
		check_master_ETCD_status()

		if "etcd_node" in config and len(config["etcd_node"]) >= int(config["etcd_node_num"]) and "kubernetes_master_node" in config and len(config["kubernetes_master_node"]) >= 1:
			print "Ready to deploy kubernetes master on %s, etcd cluster on %s.  " % (",".join(config["kubernetes_master_node"]), ",".join(config["etcd_node"]))
			gen_configs()
			response = raw_input_with_default("Deploy ETCD Nodes (y/n)?")
			if first_char(response) == "y":
				gen_ETCD_certificates()
				deploy_ETCD()			
			response = raw_input_with_default("Deploy Master Nodes (y/n)?")
			if first_char(response) == "y":
				gen_master_certificates()
				deploy_masters()

			response = raw_input_with_default("Allow Workers to register (y/n)?")
			if first_char(response) == "y":

				urllib.urlretrieve (config["homeinserver"]+"/SetClusterInfo?clusterId=%s&key=etcd_endpoints&value=%s" %  (config["clusterId"],config["etcd_endpoints"]))
				urllib.urlretrieve (
				config["homeinserver"]+"/SetClusterInfo?clusterId=%s&key=api_server&value=%s" % (config["clusterId"],config["api_serviers"]))
			
#			response = raw_input_with_default("Create ISO file for deployment (y/n)?")
#			if first_char(response) == "y":
#				create_ISO()

#			response = raw_input_with_default("Create PXE docker image for deployment (y/n)?")
#			if first_char(response) == "y":
#				create_PXE()

		else:
			print "Cannot deploy cluster since there are insufficient number of etcd server or master server. \n To continue deploy the cluster we need at least %d etcd server(s)" % (int(config["etcd_node_num"]))

	elif command == "build":
		init_deployment()
		response = raw_input_with_default("Create ISO file for deployment (y/n)?")
		if first_char(response) == "y":
			create_ISO()
		response = raw_input_with_default("Create PXE docker image for deployment (y/n)?")
		if first_char(response) == "y":
			create_PXE()
	elif command == "updateworker":
		response = raw_input_with_default("Deploy Worker Nodes (y/n)?")
		if first_char(response) == "y":
			check_master_ETCD_status()
			gen_configs()
			update_worker_nodes()
			
	elif command == "listmac":
		get_config()
		nodes = get_nodes(config["clusterId"])
		for node in nodes:
			get_mac_address(node)
			
	elif command == "uncordon":
		get_config()
		uncordon_master()
	
	elif command == "hostname" and len(nargs) >= 1:
		get_config()
		if nargs[0] == "set":
			set_host_names_by_lookup()
		else:
			parser.print_help()
			print "Error: hostname with unknown subcommand"
			exit()

	elif command == "cleanworker":
		response = raw_input("Clean and Stop Worker Nodes (y/n)?")
		if first_char( response ) == "y":
			check_master_ETCD_status()
			gen_configs()			
			clean_worker_nodes()

	elif command == "partition" and len(nargs) >= 1:
		get_config()
		nodes = get_nodes(config["clusterId"])
		if nargs[0] == "ls":
		# Display parititons.  
			nodesinfo = show_partitions(nodes, args.partition )
			
		elif nargs[0] == "create" and len(nargs) >= 2:
			partsInfo = map(float, nargs[1:])
			if len(partsInfo)==1 and partsInfo[0] < 30:
				partsInfo = [100.0]*int(partsInfo[0])
			nodesinfo = show_partitions(nodes, args.partition )
			print ("This operation will DELETE all existing partitions and repartition all data drives on the %d nodes to %d partitions of %s" % (len(nodes), len(partsInfo), str(partsInfo)) )
			response = raw_input ("Please type (REPARTITION) in ALL CAPITALS to confirm the operation ---> ")
			if response == "REPARTITION":
				repartition_nodes( nodes, nodesinfo, partsInfo)
			else:
				print "Repartition operation aborted...."
		else:
			parser.print_help()
			exit()
	
	elif command == "glusterFS" and len(nargs) >= 1:
		get_config()
		# nodes = get_nodes(config["clusterId"])
		# ToDo: change pending, schedule glusterFS on master & ETCD nodes, 
		if nargs[0] == "start" or nargs[0] == "update" or nargs[0] == "stop" or nargs[0] == "clear":
			nodes = get_worker_nodes(config["clusterId"])
			nodesinfo = get_partitions(nodes, args.partition )
			if len(nargs) == 1:
				glusterFSargs = 1
			else:
				glusterFSargs = nargs[1]
			masternodes = get_ETCD_master_nodes(config["clusterId"])
			gsFlag = ""
			if nargs[0] == "start":
				exec_on_all(nodes, ["sudo modprobe dm_thin_pool"])
				gsFlag = "-g"
			elif nargs[0] == "stop":
				gsFlag = "--yes -g --abort"
			if nargs[0] == "clear":
				remove_glusterFS_volumes( masternodes, config["ipToHostname"], nodesinfo, glusterFSargs, nodes )
			else:
				start_glusterFS( masternodes, config["ipToHostname"], nodesinfo, glusterFSargs, flag = gsFlag )
			
				
		else:
			parser.print_help()
			exit()
			
	elif command == "doonall" and len(nargs)>=1:
		get_config()
		nodes = get_nodes(config["clusterId"])
		exec_on_all(nodes, nargs)
		
	elif command == "execonall" and len(nargs)>=1:
		get_config()
		nodes = get_nodes(config["clusterId"])
		exec_on_all_with_output(nodes, nargs)

	elif command == "runscriptonall" and len(nargs)>=1:
		get_config()
		nodes = get_nodes(config["clusterId"])
		run_script_on_all(nodes, nargs, sudo = args.sudo )

		
	elif command == "cleanmasteretcd":
		response = raw_input("Clean and Stop Master/ETCD Nodes (y/n)?")
		if first_char( response ) == "y":
			check_master_ETCD_status()
			gen_configs()			
			clean_master()
			clean_etcd()

	elif command == "updatereport":
		response = raw_input_with_default("Deploy IP Reporting Service on Master and ETCD nodes (y/n)?")
		if first_char(response) == "y":
			check_master_ETCD_status()
			gen_configs()
			update_reporting_service()

	elif command == "display":
		check_master_ETCD_status()

	elif command == "webui":
		check_master_ETCD_status()
		gen_configs()		
		deploy_webUI()


	else:
		parser.print_help()
