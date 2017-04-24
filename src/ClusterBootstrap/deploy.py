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
import random

from os.path import expanduser

import yaml
from jinja2 import Environment, FileSystemLoader, Template
import base64

from shutil import copyfile,copytree
import urllib
import socket;
sys.path.append("storage/glusterFS")
from GlusterFSUtils import GlusterFSJson
sys.path.append("../utils")

import utils
from DockerUtils import build_dockers, push_dockers, run_docker, find_dockers, build_docker_fullname

sys.path.append("../docker-images/glusterfs")
import launch_glusterfs

capacityMatch = re.compile("\d+[M|G]B")
digitsMatch = re.compile("\d+")
defanswer = ""
ipAddrMetaname = "hostIP"


# CoreOS version and channels, further configurable. 
coreosversion = "1235.9.0"
coreoschannel = "stable"
coreosbaseurl = ""
verbose = False
nocache = False

# These are the default configuration parameter
default_config_parameters = { 
	"homeinserver" : "http://dlws-clusterportal.westus.cloudapp.azure.com:5000", 
	# Discover server is used to find IP address of the host, it need to be a well-known IP address 
	# that is pingable. 
	"discoverserver" : "4.2.2.1", 
	"homeininterval" : "600", 
	"dockerregistry" : "mlcloudreg.westus.cloudapp.azure.com:5000/",
	# There are two docker registries, one for infrastructure (used for pre-deployment)
	# and one for worker docker (pontentially in cluser)
	# A set of infrastructure-dockers 
	"infrastructure-dockers" : {}, 
	"dockerprefix" : "",
	"dockertag" : "latest",
	"etcd3port1" : "2379", # Etcd3port1 will be used by App to call Etcd 
	"etcd3port2" : "4001", # Etcd3port2 is established for legacy purpose. 
	"etcd3portserver" : "2380", # Server port for etcd
	"k8sAPIport" : "443", # Server port for etcd
	"nvidiadriverdocker" : "mlcloudreg.westus.cloudapp.azure.com:5000/nvidia_driver:375.20",
	"nvidiadriverversion" : "375.20",
	#master deployment scripts
	"premasterdeploymentscript" : "pre-master-deploy.sh",
	"postmasterdeploymentscript" : "post-master-deploy.sh",
	"mastercleanupscript" : "cleanup-master.sh",
	"masterdeploymentlist" : "deploy.list",
	#worker deployment scripts
	"preworkerdeploymentscript" : "pre-worker-deploy.sh",
	"postworkerdeploymentscript" : "post-worker-deploy.sh",
	"workercleanupscript" : "cleanup-worker.sh",
	"workerdeploymentlist" : "deploy.list",
	"webuiport" : "80",
	"restfulapiport" : "5000",
	"ssh_cert" : "./deploy/sshkey/id_rsa",
	"storage-mount-path" : "/dlwsdata",
	"storage-mount-path-name" : "dlwsdata",
	"nvidia-driver-path" : "/opt/nvidia-driver/current", 
	"data-disk": "/dev/[sh]d[^a]", 
	"partition-configuration": [ "1" ], 
	"heketi-docker": "heketi/heketi:dev",
	# The following file will be copied (not rendered for configuration)
	"render-exclude" : {"GlusterFSUtils.pyc": True, "launch_glusterfs.pyc": True, },
	"render-by-copy-ext" : { ".png": True, },
	"render-by-copy": { "gk-deploy":True, },
	# glusterFS parameter
	"glusterFS" : { "dataalignment": "1280K", 
					"physicalextentsize": "128K", 
					"volumegroup": "gfs_vg", 
					"metasize": "16776960K", 
					# Volume needs to leave room for metadata and thinpool provisioning, 98%FREE is doable for a 1TB drive.
					"volumesize": "98%FREE",
					"metapoolname": "gfs_pool_meta", 
					"datapoolname": "gfs_pool", 
					"volumename": "gfs_lv",
					"chunksize": "1280K",
					"mkfs.xfs.options": "-f -i size=512 -n size=8192 -d su=128k,sw=10",
					"mountpoint": "/mnt/glusterfs/localvolume", 
					# GlusterFS volume to be constructed. 
					"glustefs_nodes_yaml" : "./deploy/docker-images/glusterfs/glusterfs_config.yaml", 
					"glusterfs_docker" : "glusterfs", 
					# File system should always be accessed from the symbolic link, not from the actual mountpoint
					"glusterfs_mountpoint": "/mnt/glusterfs/private",
					"glusterfs_symlink": "/mnt/glusterfs",
					# Spell out a number of glusterFS volumes to be created on the cluster. 
					# Please refer to https://access.redhat.com/documentation/en-US/Red_Hat_Storage/2.1/html/Administration_Guide/sect-User_Guide-Setting_Volumes-Distributed_Replicated.html
					# for proper volumes in glusterFS. 
					# By default, all worker nodes with glusterFS installed will be placed in the default group. 
					# The behavior can be modified by spell out the group that the node is expected to be in. 
					# E.g., 
					# node01:
					#   gluterfs: 1
					# will place node01 into a glusterfs group 1. The nodes in each glusterfs group will form separate volumes
					# 
					"gluster_volumes" : {
							"default" : {
								"netvolume" : { 
									"property": "replica 3", 
									"transport": "tcp,rdma", 
									# of nodes that can fail before the volume will become unaccessible. 
									"tolerance": 2,
									# number of bricks need to be a multiple of this
									"multiple": 3, 
								}, 
							}, 
						}, 
					# These parameters are required for every glusterfs volumes
					"gluster_volumes_required_param": ["property", "transport", "tolerance", "multiple" ], 
					}, 
	# Options to run in glusterfs
	"launch-glusterfs-opt": "run", 
}




# default search for all partitions of hdb, hdc, hdd, and sdb, sdc, sdd

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def expand_path(path):
	return expanduser(path)

# Return a path name, expand on ~, for a particular config, 
# e.g., ssh_key
def expand_path_in_config(key_in_config):
	if key_in_config in config:
		return expand_path(config[key_in_config])
	else:
		raise Exception("Error: no %s in config " % key_in_config)

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
	utils.render_template_directory( "./template/pxe/tftp/usr/share/oem", "./deploy/iso-creator",config)
	utils.render_template_directory( "./template/iso-creator", "./deploy/iso-creator",config)

# Certain configuration that is default in system 
def init_config():
	config = {}
	for k,v in default_config_parameters.iteritems():
		config[ k ] = v
	return config

def apply_config_mapping():
	for k,tuple in default_config_mapping.iteritems():
		if not ( k in config ) or len(config[k])<=1:
			dstname = tuple[0]
			value = fetch_config(dstname)
			config[k] = tuple[1](value)
			if verbose:
				print "Config[%s] = %s" %(k, config[k])

def _check_config_items(cnfitem, cnf):
	if not cnfitem in cnf:
		raise Exception("ERROR: we cannot find %s in config file" % cnfitem) 
	else:
		print "Checking configurations '%s' = '%s'" % (cnfitem, cnf[cnfitem])
 
def check_config(cnf):
	_check_config_items("discovery_url",cnf)
	_check_config_items("kubernetes_master_node",cnf)
	_check_config_items("kubernetes_master_ssh_user",cnf)
	_check_config_items("api_servers",cnf)
	_check_config_items("etcd_user",cnf)
	_check_config_items("etcd_node",cnf)
	_check_config_items("etcd_endpoints",cnf)
	_check_config_items("ssh_cert",cnf)
	_check_config_items("pod_ip_range",cnf)
	_check_config_items("basic_auth",cnf)
	_check_config_items("kubernetes_docker_image",cnf)
	_check_config_items("service_cluster_ip_range",cnf)
	if not os.path.isfile(config["ssh_cert"]):
		raise Exception("ERROR: we cannot find ssh key file at %s. \n please run 'python build-pxe-coreos.py docker_image_name' to generate ssh key file and pxe server image." % config["ssh_cert"]) 


# Test if a certain Config entry exist
def fetch_dictionary(dic, entry):
	if isinstance(entry, list):
		# print "Fetch " + str(dic) + "@" + str(entry) + "==" + str( dic[entry[0]] ) 
		if isinstance( dic, list ):
			for subdic in dic:
				if entry[0] in subdic:
					if len(entry)<=1:
						return subdic[entry[0]]
					else:
						return fetch_dictionary(subdic[entry[0]], entry[1:])
			return None
		elif entry[0] in dic:
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
	
# Test if a certain Config entry exist
def fetch_config_and_check(entry):
	ret = fetch_config( entry )
	if ret is None:
		print "Error: config entry %s doesn't exist" % entry
		exit()
	return ret;
	
# These parameter will be mapped if non-exist
# Each mapping is the form of: dstname: ( srcname, lambda )
# dstname: config name to be used.
# srcname: config name to be searched for (expressed as a list, see fetch_config)
# lambda: lambda function to translate srcname to target name
default_config_mapping = { 
	"dockerprefix": (["cluster_name"], lambda x:x+"/"), 
	"infrastructure-dockerregistry": (["dockerregistry"], lambda x:x), 
	"worker-dockerregistry": (["dockerregistry"], lambda x:x),
	"glusterfs-device": (["glusterFS"], lambda x: "/dev/%s/%s" % (fetch_dictionary(x, ["volumegroup"]), fetch_dictionary(x, ["volumename"]) ) ),
	"glusterfs-localvolume": (["glusterFS"], lambda x: fetch_dictionary(x, ["mountpoint"]) ),
	
};
	
# Merge entries in config2 to that of config1, if entries are dictionary. 
# If entry is list or other variable, it will just be replaced. 
# say config1 = { "A" : { "B": 1 } }, config2 = { "A" : { "C": 2 } }
# C python operation: config1.update(config2) give you { "A" : { "C": 2 } }
# merge_config will give you: { "A" : { "B": 1, "C":2 } }
def merge_config( config1, config2 ):
	for entry in config2:
		if entry in config1:
			if isinstance( config1[entry], dict): 
				merge_config( config1[entry], config2[entry] )
			else:
				config1[entry] = config2[entry]
		else:
			config1[entry] = config2[entry]

	
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
	apply_config_mapping()
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
		if "sshkey" in config and "sshKeys" in config and not (config["sshkey"] in config["sshKeys"]):
			config["sshKeys"].append(config["sshkey"])
	elif "sshkey" in config:
		config["sshKeys"] = []
		config["sshKeys"].append(config["sshkey"])
		
	
# Render scripts for kubenete nodes
def add_kubelet_config():
	renderfiles = []

# Render all deployment script used. 
	utils.render_template_directory("./template/kubelet", "./deploy/kubelet",config)

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
	
# translate a config entry to another, check type and do format conversion along the way
def translate_config_entry( entry, name, type, leading_space = 0 ):
	content = fetch_config( entry )
	if not content is None:
		if isinstance( content, type ):
			if leading_space > 0 : 
				adj_content = add_leading_spaces( content, leading_space )
			else:
				adj_content = content
			config[name] = adj_content
			if verbose: 
				print "Configuration entry: " + name
				print adj_content
		else:
			print "In configuration file, " + str( entry ) + " should be type of " +str(type) + ", rather than: "+ str(content )
			exit()

# fill in additional entry of cloud config
def add_additional_cloud_config():
	# additional entry to be added to write_files 
	translate_config_entry( ["coreos", "write_files"], "coreoswritefiles", basestring, 2 )
	# additional entry to be added to units 
	translate_config_entry( ["coreos", "units"], "coreosunits", basestring, 4 )
	# additional startup script to be added to report.sh
	translate_config_entry( ["coreos", "startupScripts"], "startupscripts", basestring )
	
def init_deployment():
	if (os.path.isfile("./deploy/clusterID.yml")):
		
		clusterID = utils.get_cluster_ID_from_file()
		response = raw_input_with_default("There is a cluster (ID:%s) deployment in './deploy', do you want to keep the existing ssh key and CA certificates (y/n)?" % clusterID)
		if first_char(response) == "n":
			utils.backup_keys(config["cluster_name"])
			utils.gen_SSH_key()
			gen_CA_certificates()
			gen_worker_certificates()
			utils.backup_keys(config["cluster_name"])
	else:
		utils.gen_SSH_key()
		gen_CA_certificates()
		gen_worker_certificates()
		utils.backup_keys(config["cluster_name"])

	clusterID = utils.get_cluster_ID_from_file()

	f = open(config["ssh_cert"]+".pub")
	sshkey_public = f.read()
	print sshkey_public
	f.close()



	print "Cluster Id is : %s" % clusterID 

	config["clusterId"] = clusterID
	config["sshkey"] = sshkey_public
	add_ssh_key()

	add_additional_cloud_config()
	add_kubelet_config()

	template_file = "./template/cloud-config/cloud-config-master.yml"
	target_file = "./deploy/cloud-config/cloud-config-master.yml"
	config["role"] = "master"
	
	utils.render_template(template_file, target_file,config)

	template_file = "./template/cloud-config/cloud-config-etcd.yml"
	target_file = "./deploy/cloud-config/cloud-config-etcd.yml"
	
	config["role"] = "etcd"
	utils.render_template(template_file, target_file,config)

	# Prepare to Generate the ISO image. 
	# Using files in PXE as template. 
	copy_to_ISO()



	template_file = "./template/iso-creator/mkimg.sh.template"
	target_file = "./deploy/iso-creator/mkimg.sh"
	utils.render_template( template_file, target_file ,config)

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

	add_additional_cloud_config()
	add_kubelet_config()

	template_file = "./template/cloud-config/cloud-config-worker.yml"
	target_file = "./deploy/cloud-config/cloud-config-worker.yml"
	utils.render_template( template_file, target_file ,config)

def check_node_availability(ipAddress):
	# print "Check node availability on: " + str(ipAddress)
	status = os.system('ssh -o "StrictHostKeyChecking no" -i %s -oBatchMode=yes core@%s hostname > /dev/null' % (config["ssh_cert"], ipAddress))
	#status = sock.connect_ex((ipAddress,22))
	return status == 0
	
# Get domain of the node
def get_domain():
	if "network" in config and "domain" in config["network"]:
		domain = "."+config["network"]["domain"]
	else:
		domain = ""
	return domain

# Get a list of nodes from cluster.yaml 
def get_nodes_from_config(machinerole):
	if "machines" not in config:
		return []
	else:
		domain = get_domain()
		Nodes = []
		for nodename in config["machines"]:
			nodeInfo = config["machines"][nodename]
			if "role" in nodeInfo and nodeInfo["role"]==machinerole:
				Nodes.append(nodename+domain)
		return sorted(Nodes)

def get_ETCD_master_nodes_from_cluster_portal(clusterId):
	output = urllib.urlopen(form_cluster_portal_URL("etcd", clusterId)).read()	
	output = json.loads(json.loads(output))
	Nodes = []
	NodesInfo = [node for node in output["nodes"] if "time" in node]
	if not "ipToHostname" in config:
		config["ipToHostname"] = {}
	for node in NodesInfo:
		if not node[ipAddrMetaname] in Nodes and check_node_availability(node[ipAddrMetaname]):
			hostname = utils.get_host_name(node[ipAddrMetaname])
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
	
def get_ETCD_master_nodes_from_config(clusterId):
	Nodes = get_nodes_from_config("infrastructure")
	config["etcd_node"] = Nodes
	config["kubernetes_master_node"] = Nodes
	return Nodes

def get_ETCD_master_nodes(clusterId):
	if "etcd_node" in config:
		return config["etcd_node"]
	if "useclusterfile" not in config or not config["useclusterfile"]:
		return get_ETCD_master_nodes_from_cluster_portal(clusterId)
	else:
		return get_ETCD_master_nodes_from_config(clusterId)
	
def get_worker_nodes_from_cluster_report(clusterId):
	output = urllib.urlopen(form_cluster_portal_URL("worker", clusterId)).read()
	output = json.loads(json.loads(output))
	Nodes = []
	NodesInfo = [node for node in output["nodes"] if "time" in node]
	if not "ipToHostname" in config:
		config["ipToHostname"] = {}
	for node in NodesInfo:
		if not node[ipAddrMetaname] in Nodes and check_node_availability(node[ipAddrMetaname]):
			hostname = utils.get_host_name(node[ipAddrMetaname])
			Nodes.append(node[ipAddrMetaname])
			config["ipToHostname"][node[ipAddrMetaname]] = hostname
	config["worker_node"] = Nodes
	return Nodes

def get_worker_nodes_from_config(clusterId):
	Nodes = get_nodes_from_config("worker")
	config["worker_node"] = Nodes
	return Nodes

def get_worker_nodes(clusterId):
	if "worker_node" in config:
		return config["worker_node"]
	if "useclusterfile" not in config or not config["useclusterfile"]:
		return get_worker_nodes_from_cluster_report(clusterId)
	else:
		return get_worker_nodes_from_config(clusterId)

def get_nodes(clusterId):
	nodes = get_ETCD_master_nodes(clusterId) + get_worker_nodes(clusterId)
	return nodes

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
		utils.backup_keys(config["cluster_name"])
	os.system("rm -r ./deploy/*")


def gen_CA_certificates():
	utils.render_template_directory("./template/ssl", "./deploy/ssl",config)
	os.system("cd ./deploy/ssl && bash ./gencerts_ca.sh")

def GetCertificateProperty():
	masterips = []
	masterdns = []
	etcdips = []
	etcddns = []
	ippattern = re.compile("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")

	for i,value in enumerate(config["kubernetes_master_node"]):
		if ippattern.match(value):
			masterips.append(value)
		else:
			masterdns.append(value)

	config["apiserver_ssl_dns"] = "\n".join(["DNS."+str(i+5)+" = "+dns for i,dns in enumerate(masterdns)])
	config["apiserver_ssl_ip"] = "IP.1 = 10.3.0.1\nIP.2 = 127.0.0.1\n"+ "\n".join(["IP."+str(i+3)+" = "+ip for i,ip in enumerate(masterips)])

	for i,value in enumerate(config["etcd_node"]):
		if ippattern.match(value):
			etcdips.append(value)
		else:
			etcddns.append(value)

	config["etcd_ssl_dns"] = "\n".join(["DNS."+str(i+5)+" = "+dns for i,dns in enumerate(etcddns)])
	config["etcd_ssl_ip"] = "IP.1 = 127.0.0.1\n" + "\n".join(["IP."+str(i+2)+" = "+ip for i,ip in enumerate(etcdips)])

def gen_worker_certificates():

	GetCertificateProperty()
	utils.render_template_directory("./template/ssl", "./deploy/ssl",config)
	os.system("cd ./deploy/ssl && bash ./gencerts_kubelet.sh")	

def gen_master_certificates():

	GetCertificateProperty()

	utils.render_template_directory("./template/ssl", "./deploy/ssl",config)
	os.system("cd ./deploy/ssl && bash ./gencerts_master.sh")


def gen_ETCD_certificates():

	GetCertificateProperty()
	utils.render_template_directory("./template/ssl", "./deploy/ssl",config)
	os.system("cd ./deploy/ssl && bash ./gencerts_etcd.sh")	



def gen_configs():
	print "==============================================="
	print "generating configuration files..."
	os.system("mkdir -p ./deploy/etcd")
	os.system("mkdir -p ./deploy/kube-addons")
	os.system("mkdir -p ./deploy/master")	
	os.system("rm -r ./deploy/etcd")
	os.system("rm -r ./deploy/kube-addons")
	os.system("rm -r ./deploy/master")

	deployDirs = ["deploy/etcd","deploy/kubelet","deploy/master","deploy/web-docker/kubelet","deploy/kube-addons","deploy/bin"]
	for deployDir in deployDirs:
		if not os.path.exists(deployDir):
			os.system("mkdir -p %s" % (deployDir))

	if "etcd_node" in config:
		etcd_servers = config["etcd_node"]
	else:
		etcd_servers = []

	#if int(config["etcd_node_num"]) <= 0:
	#	raise Exception("ERROR: we need at least one etcd_server.") 
	if "kubernetes_master_node" in config:
		kubernetes_masters = config["kubernetes_master_node"]
	else:
		kubernetes_masters = []

	#if len(kubernetes_masters) <= 0:
	#	raise Exception("ERROR: we need at least one etcd_server.") 

	config["discovery_url"] = utils.get_ETCD_discovery_URL(int(config["etcd_node_num"]))

	if "ssh_cert" not in config and os.path.isfile("./deploy/sshkey/id_rsa"):
		config["ssh_cert"] = expand_path("./deploy/sshkey/id_rsa")
		
	config["etcd_user"] = "core"
	config["kubernetes_master_ssh_user"] = "core"

	#config["api_servers"] = ",".join(["https://"+x for x in config["kubernetes_master_node"]])
	config["api_servers"] = "https://"+config["kubernetes_master_node"][0]+":"+str(config["k8sAPIport"])
	config["etcd_endpoints"] = ",".join(["https://"+x+":"+config["etcd3port1"] for x in config["etcd_node"]])

	if os.path.isfile(config["ssh_cert"]+".pub"):
		f = open(config["ssh_cert"]+".pub")
		sshkey_public = f.read()
		f.close()

		config["sshkey"] = sshkey_public
	add_ssh_key()

	check_config(config)

	utils.render_template_directory("./template/etcd", "./deploy/etcd",config)
	utils.render_template_directory("./template/master", "./deploy/master",config)
	utils.render_template_directory("./template/web-docker", "./deploy/web-docker",config)
	utils.render_template_directory("./template/kube-addons", "./deploy/kube-addons",config)
	utils.render_template_directory("./template/RestfulAPI", "./deploy/RestfulAPI",config)

def get_ssh_config():
	if "ssh_cert" not in config and os.path.isfile("./deploy/sshkey/id_rsa"):
		config["ssh_cert"] = "./deploy/sshkey/id_rsa"
	if "ssh_cert" in config:
		config["ssh_cert"] = expand_path(config["ssh_cert"])
	config["etcd_user"] = "core"
	config["kubernetes_master_ssh_user"] = "core"
	add_ssh_key()


def update_reporting_service():
	kubernetes_masters = config["kubernetes_master_node"]
	kubernetes_master_user = config["kubernetes_master_ssh_user"]

	for kubernetes_master in kubernetes_masters:
		print "==============================================="
		print "Updating report service on master %s... " % kubernetes_master

		utils.SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo systemctl stop reportcluster")
		utils.scp(config["ssh_cert"],"./deploy/kebelet/report.sh","/home/%s/report.sh" % kubernetes_master_user , kubernetes_master_user, kubernetes_master )
		utils.SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo mv /home/%s/report.sh /opt/report.sh" % (kubernetes_master_user))

		utils.SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo systemctl start reportcluster")


	etcd_servers = config["etcd_node"]
	etcd_server_user = config["etcd_user"]


	for etcd_server_address in etcd_servers:
		print "==============================================="
		print "Updating report service on etcd node %s... " % etcd_server_address

		utils.SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo systemctl stop reportcluster")
		utils.scp(config["ssh_cert"],"./deploy/kubelet/report.sh","/home/%s/report.sh" % etcd_server_user , etcd_server_user, etcd_server_address )
		utils.SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo mv /home/%s/report.sh /opt/report.sh" % (etcd_server_user))

		utils.SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo systemctl start reportcluster")

def clean_master():
	kubernetes_masters = config["kubernetes_master_node"]
	kubernetes_master_user = config["kubernetes_master_ssh_user"]

	for kubernetes_master in kubernetes_masters:
		print "==============================================="
		print "Clean up kubernetes master %s... (It is OK to see 'Errors' in this section)" % kubernetes_master

		utils.SSH_exec_script(config["ssh_cert"],kubernetes_master_user, kubernetes_master, "./deploy/master/%s" % config["mastercleanupscript"])


def deploy_master(kubernetes_master):
		print "==============================================="
		kubernetes_master_user = config["kubernetes_master_ssh_user"]
		print "starting kubernetes master on %s..." % kubernetes_master

		config["master_ip"] = utils.getIP(kubernetes_master)
		utils.render_template("./template/master/kube-apiserver.yaml","./deploy/master/kube-apiserver.yaml",config)
		utils.render_template("./template/master/kubelet.service","./deploy/master/kubelet.service",config)
		utils.render_template("./template/master/" + config["premasterdeploymentscript"],"./deploy/master/"+config["premasterdeploymentscript"],config)
		utils.render_template("./template/master/" + config["postmasterdeploymentscript"],"./deploy/master/"+config["postmasterdeploymentscript"],config)


		utils.SSH_exec_script(config["ssh_cert"],kubernetes_master_user, kubernetes_master, "./deploy/master/"+config["premasterdeploymentscript"])


		with open("./deploy/master/"+config["masterdeploymentlist"],"r") as f:
			deploy_files = [s.split(",") for s in f.readlines() if len(s.split(",")) == 2]
		for (source, target) in deploy_files:
			if (os.path.isfile(source.strip()) or os.path.exists(source.strip())):
				utils.sudo_scp(config["ssh_cert"],source.strip(),target.strip(),kubernetes_master_user,kubernetes_master)

		utils.SSH_exec_script(config["ssh_cert"],kubernetes_master_user, kubernetes_master, "./deploy/master/" + config["postmasterdeploymentscript"])
		
def get_kubectl_binary():
	os.system("mkdir -p ./deploy/bin")
	urllib.urlretrieve ("http://ccsdatarepo.westus.cloudapp.azure.com/data/kube/kubelet/kubelet", "./deploy/bin/kubelet")
	urllib.urlretrieve ("http://ccsdatarepo.westus.cloudapp.azure.com/data/kube/kubelet/kubectl", "./deploy/bin/kubectl")
	os.system("chmod +x ./deploy/bin/*")

def deploy_masters():

	print "==============================================="
	print "Prepare to deploy kubernetes master"
	print "waiting for ETCD service is ready..."
	check_etcd_service()
	print "==============================================="
	print "Generating master configuration files..."

	kubernetes_masters = config["kubernetes_master_node"]
	kubernetes_master_user = config["kubernetes_master_ssh_user"]


	utils.render_template_directory("./template/master", "./deploy/master",config)
	utils.render_template_directory("./template/kube-addons", "./deploy/kube-addons",config)
	#temporary hard-coding, will be fixed after refactoring of config/render logic
	config["restapi"] = "http://%s:%s" %  (kubernetes_masters[0],config["restfulapiport"])
	utils.render_template_directory("./template/WebUI", "./deploy/WebUI",config)
	utils.render_template_directory("./template/RestfulAPI", "./deploy/RestfulAPI",config)


	get_kubectl_binary()
	
	clean_master()

	for i,kubernetes_master in enumerate(kubernetes_masters):
		deploy_master(kubernetes_master)


	utils.SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_masters[0], "until curl -q http://127.0.0.1:8080/version/ ; do sleep 5; echo 'waiting for master...'; done;  sudo /opt/bin/kubectl create -f /opt/addons/kube-addons/dashboard.yaml;  sudo /opt/bin/kubectl create -f /opt/addons/kube-addons/dns-addon.yaml;  sudo /opt/bin/kubectl create -f /opt/addons/kube-addons/kube-proxy.json;  sudo /opt/bin/kubectl create -f /opt/addons/kube-addons/heapster-deployment.json;  sudo /opt/bin/kubectl create -f /opt/addons/kube-addons/heapster-svc.json", False)


def clean_etcd():
	etcd_servers = config["etcd_node"]
	etcd_server_user = config["etcd_user"]

	for etcd_server_address in etcd_servers:
		print "==============================================="
		print "Clean up etcd servers %s... (It is OK to see 'Errors' in this section)" % etcd_server_address		
		#utils.SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "timeout 10 docker rm -f \$(timeout 3 docker ps -q -a)")
		cmd = "sudo systemctl stop etcd3; "
		cmd += "sudo rm -r /var/etcd/data ; "
		cmd += "sudo rm -r /etc/etcd/ssl; "
		utils.SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, cmd )

def check_etcd_service():
	print "waiting for ETCD service is ready..."
	etcd_servers = config["etcd_node"]
	cmd = "curl --cacert %s --cert %s --key %s 'https://%s:%s/v2/keys'" % ("./deploy/ssl/etcd/ca.pem","./deploy/ssl/etcd/etcd.pem","./deploy/ssl/etcd/etcd-key.pem", etcd_servers[0], config["etcd3port1"])
	if verbose:
		print cmd
	while os.system(cmd) != 0:
		time.sleep(5)
	print "ETCD service is ready to use..."


def deploy_ETCD_docker():
	
	etcd_servers = config["etcd_node"]
	etcd_server_user = config["etcd_user"]
	utils.render_template_directory("./template/etcd", "./deploy/etcd",config)

	for etcd_server_address in etcd_servers:
		#print "==============================================="
		#print "deploy configuration files to web server..."
		#scp(config["ssh_cert"],"./deploy","/var/www/html", config["webserver_user"], config["webserver"] )

		print "==============================================="
		print "deploy certificates to etcd server %s" % etcd_server_address
		utils.SSH_exec_cmd (config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo mkdir -p /etc/etcd/ssl ; sudo chown %s /etc/etcd/ssl " % (etcd_server_user)) 
		utils.scp(config["ssh_cert"],"./deploy/ssl/etcd/ca.pem","/etc/etcd/ssl", etcd_server_user, etcd_server_address )
		utils.scp(config["ssh_cert"],"./deploy/ssl/etcd/etcd.pem","/etc/etcd/ssl", etcd_server_user, etcd_server_address )
		utils.scp(config["ssh_cert"],"./deploy/ssl/etcd/etcd-key.pem","/etc/etcd/ssl", etcd_server_user, etcd_server_address )

		print "==============================================="
		print "starting etcd service on %s ..." % etcd_server_address


		config["etcd_node_ip"] = etcd_server_address
		utils.render_template("./template/etcd/docker_etcd_ssl.sh","./deploy/etcd/docker_etcd_ssl.sh",config)

		utils.scp(config["ssh_cert"],"./deploy/etcd/docker_etcd_ssl.sh","/home/%s/docker_etcd_ssl.sh" % etcd_server_user, etcd_server_user, etcd_server_address )
		utils.SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "chmod +x /home/%s/docker_etcd_ssl.sh ; /home/%s/docker_etcd_ssl.sh" % (etcd_server_user,etcd_server_user))


	print "==============================================="
	print "init etcd service on %s ..."  % etcd_servers[0]


	check_etcd_service()

	utils.scp(config["ssh_cert"],"./deploy/etcd/init_network.sh","/home/%s/init_network.sh" % etcd_server_user, etcd_server_user, etcd_servers[0] )
	utils.SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_servers[0], "chmod +x /home/%s/init_network.sh" % etcd_server_user)
	utils.SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_servers[0], "/home/%s/init_network.sh" % etcd_server_user)


def deploy_ETCD():

	if "deploydockerETCD" in config and config["deploydockerETCD"]:
		deploy_ETCD_docker()
		return

	etcd_servers = config["etcd_node"]
	etcd_server_user = config["etcd_user"]
	
	clean_etcd()

	for i,etcd_server_address in enumerate(etcd_servers):
		#print "==============================================="
		#print "deploy configuration files to web server..."
		#utils.scp(config["ssh_cert"],"./deploy","/var/www/html", config["webserver_user"], config["webserver"] )

		utils.SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo systemctl stop etcd3")

		print "==============================================="
		print "deploy certificates to etcd server %s" % etcd_server_address
		
		utils.SSH_exec_cmd (config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo mkdir -p /etc/etcd/ssl") 
		utils.SSH_exec_cmd (config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo chown %s /etc/etcd/ssl " % (etcd_server_user)) 
		utils.scp(config["ssh_cert"],"./deploy/ssl/etcd/ca.pem","/etc/etcd/ssl", etcd_server_user, etcd_server_address )
		utils.scp(config["ssh_cert"],"./deploy/ssl/etcd/etcd.pem","/etc/etcd/ssl", etcd_server_user, etcd_server_address )
		utils.scp(config["ssh_cert"],"./deploy/ssl/etcd/etcd-key.pem","/etc/etcd/ssl", etcd_server_user, etcd_server_address )

		print "==============================================="
		print "starting etcd service on %s ..." % etcd_server_address


		config["etcd_node_ip"] = etcd_server_address
		config["hostname"] = config["cluster_name"]+"-etcd"+str(i+1)
		utils.render_template("./template/etcd/etcd3.service","./deploy/etcd/etcd3.service",config)
		utils.render_template("./template/etcd/etcd_ssl.sh","./deploy/etcd/etcd_ssl.sh",config)

		utils.sudo_scp(config["ssh_cert"],"./deploy/etcd/etcd3.service","/etc/systemd/system/etcd3.service", etcd_server_user, etcd_server_address )

		utils.sudo_scp(config["ssh_cert"],"./deploy/etcd/etcd_ssl.sh","/opt/etcd_ssl.sh", etcd_server_user, etcd_server_address )
		utils.SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "chmod +x /opt/etcd_ssl.sh")
		utils.SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo /opt/etcd_ssl.sh")



	print "==============================================="
	print "init etcd service on %s ..."  % etcd_servers[0]


	print "waiting for ETCD service is ready..."
	cmd = "curl --cacert %s --cert %s --key %s 'https://%s:%s/v2/keys'" % ("./deploy/ssl/etcd/ca.pem","./deploy/ssl/etcd/etcd.pem","./deploy/ssl/etcd/etcd-key.pem", etcd_servers[0], config["etcd3port1"])
	while os.system(cmd) != 0:
		print "ETCD service is NOT ready, waiting for 5 seconds..."
		time.sleep(5)
	print "ETCD service is ready to use..."



	utils.render_template("./template/etcd/init_network.sh","./deploy/etcd/init_network.sh",config)
	utils.SSH_exec_script( config["ssh_cert"], etcd_server_user, etcd_servers[0], "./deploy/etcd/init_network.sh")


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
	utils.render_template_directory("./template/pxe", "./deploy/pxe",config)
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
		utils.SSH_exec_script(config["ssh_cert"],kubernetes_master_user, kubernetes_master, "./deploy/kubelet/%s" % config["workercleanupscript"])



def reset_worker_node(nodeIP):

	print "==============================================="
	print "updating worker node: %s ..."  % nodeIP

	worker_ssh_user = "core"
	utils.SSH_exec_script(config["ssh_cert"],worker_ssh_user, nodeIP, "./deploy/kubelet/%s" % config["preworkerdeploymentscript"])


	utils.sudo_scp(config["ssh_cert"],"./deploy/cloud-config/cloud-config-worker.yml","/var/lib/coreos-install/user_data", worker_ssh_user, nodeIP )

	utils.SSH_exec_cmd(config["ssh_cert"], worker_ssh_user, nodeIP, "sudo reboot")

def write_nodelist_yaml():
	data = {}
	data["worker_node"] = config["worker_node"]
	data["etcd_node"] = config["etcd_node"]
	with open("./deploy/kubelet/nodelist.yaml",'w') as datafile:
		yaml.dump(data, datafile, default_flow_style=False)

def update_worker_node(nodeIP):
	print "==============================================="
	print "updating worker node: %s ..."  % nodeIP

	worker_ssh_user = "core"
	utils.SSH_exec_script(config["ssh_cert"],worker_ssh_user, nodeIP, "./deploy/kubelet/%s" % config["preworkerdeploymentscript"])

	with open("./deploy/kubelet/"+config["workerdeploymentlist"],"r") as f:
		deploy_files = [s.split(",") for s in f.readlines() if len(s.split(",")) == 2]
	for (source, target) in deploy_files:
		if (os.path.isfile(source.strip()) or os.path.exists(source.strip())):
			utils.sudo_scp(config["ssh_cert"],source.strip(),target.strip(),worker_ssh_user, nodeIP)

	utils.SSH_exec_script(config["ssh_cert"],worker_ssh_user, nodeIP, "./deploy/kubelet/%s" % config["postworkerdeploymentscript"])

	print "done!"
	
def in_list( node, nodelists ):
	if nodelists is None or len(nodelists)<=0:
		return True
	else:
		for name in nodelists:
			if node.find(name)>=0:
				return True;
		return False;


def update_worker_nodes( nargs ):
	utils.render_template_directory("./template/kubelet", "./deploy/kubelet",config)
	write_nodelist_yaml()
	
	os.system('sed "s/##etcd_endpoints##/%s/" "./deploy/kubelet/options.env.template" > "./deploy/kubelet/options.env"' % config["etcd_endpoints"].replace("/","\\/"))
	os.system('sed "s/##api_servers##/%s/" ./deploy/kubelet/kubelet.service.template > ./deploy/kubelet/kubelet.service' % config["api_servers"].replace("/","\\/"))
	os.system('sed "s/##api_servers##/%s/" ./deploy/kubelet/worker-kubeconfig.yaml.template > ./deploy/kubelet/worker-kubeconfig.yaml' % config["api_servers"].replace("/","\\/"))
	
	urllib.urlretrieve ("http://ccsdatarepo.westus.cloudapp.azure.com/data/kube/kubelet/kubelet", "./deploy/bin/kubelet")

	workerNodes = get_worker_nodes(config["clusterId"])
	for node in workerNodes:
		if in_list(node, nargs):
			update_worker_node(node)

	os.system("rm ./deploy/kubelet/options.env")
	os.system("rm ./deploy/kubelet/kubelet.service")
	os.system("rm ./deploy/kubelet/worker-kubeconfig.yaml")

	#if len(config["kubernetes_master_node"]) > 0:
		#utils.SSH_exec_cmd(config["ssh_cert"], "core", config["kubernetes_master_node"][0], "sudo /opt/bin/kubelet get nodes")

def reset_worker_nodes():

	workerNodes = get_worker_nodes(config["clusterId"])
	for node in workerNodes:
		reset_worker_node(node)



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
	utils.render_template("../utils/config.yaml.template","./deploy/RestfulAPI/config.yaml",config)
	utils.render_template("./template/master/restapi-kubeconfig.yaml","./deploy/master/restapi-kubeconfig.yaml",config)

	utils.sudo_scp(config["ssh_cert"],"./deploy/RestfulAPI/config.yaml","/etc/RestfulAPI/config.yaml", "core", masterIP )
	utils.sudo_scp(config["ssh_cert"],"./deploy/master/restapi-kubeconfig.yaml","/etc/kubernetes/restapi-kubeconfig.yaml", "core", masterIP )


	utils.SSH_exec_cmd(config["ssh_cert"], "core", masterIP, "sudo mkdir -p /dlws-data && sudo mount %s /dlws-data ; docker rm -f restfulapi; docker rm -f jobScheduler ; docker pull %s ; docker run -d -p %s:80 --restart always -v /etc/RestfulAPI:/RestfulAPI --name restfulapi %s ; docker run -d -v /dlws-data:/dlws-data -v /etc/RestfulAPI:/RestfulAPI -v /etc/kubernetes/restapi-kubeconfig.yaml:/root/.kube/config -v /etc/kubernetes/ssl:/etc/kubernetes/ssl --restart always --name jobScheduler %s /runScheduler.sh ;" % (config["nfs-server"], dockername,config["restfulapiport"],dockername,dockername))


	print "==============================================="
	print "restful api is running at: http://%s:%s" % (masterIP,config["restfulapiport"])
	config["restapi"] = "http://%s:%s" %  (masterIP,config["restfulapiport"])

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
	utils.render_template("./template/WebUI/appsettings.json.template","./deploy/WebUI/appsettings.json",config)
	utils.sudo_scp(config["ssh_cert"],"./deploy/WebUI/appsettings.json","/etc/WebUI/appsettings.json", "core", webUIIP )


	utils.SSH_exec_cmd(config["ssh_cert"], sshUser, webUIIP, "docker pull %s ; docker rm -f webui ; docker run -d -p %s:80 -v /etc/WebUI:/WebUI --restart always --name webui %s ;" % (dockername,str(config["webuiport"]),dockername))


	print "==============================================="
	print "Web UI is running at: http://%s:%s" % (webUIIP,str(config["webuiport"]))


def deploy_webUI():
	masterIP = config["kubernetes_master_node"][0]
	deploy_restful_API_on_node(masterIP)
	deploy_webUI_on_node(masterIP)


def label_webUI(nodename):
	kubernetes_label_node("--overwrite", nodename, "webportal=active")
	kubernetes_label_node("--overwrite", nodename, "restfulapi=active")
	kubernetes_label_node("--overwrite", nodename, "jobmanager=active")

# Get disk partition information of a node
def get_partions_of_node(node, prog):
	output = utils.SSH_exec_cmd_with_output(config["ssh_cert"], "core", node, "sudo parted -l -s", True)
	if verbose:
		print node
		print output
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
			if capacity > 0 and len(parted)==0:
				parted[0] = capacity
			
			# print drivename + " Capacity: " + str(capacity) + " GB, " + str(parted)
			deviceinfo["name"] = drivename
			deviceinfo["capacity"] = capacity
			deviceinfo["parted"] = parted
			partinfo[blockdevice] = deviceinfo
			blockdevice += 1
	return partinfo 
	
# Get Partition of all nodes in a cluster
def get_partitions(nodes, regexp):
	print "Retrieving partition information for nodes, can take quite a while for a large cluster ......"
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
		if len(cmd)>0:
			utils.SSH_exec_cmd(config["ssh_cert"], "core", node, cmd)
	print "Please note, it is OK to ignore message of Warning: Not all of the space available to /dev/___ appears to be used. The current default partition method optimizes for speed, rather to use all disk capacity..."
	()
	
def glusterFS_copy_heketi():
	utils.render_template_directory("./storage/glusterFS", "./deploy/storage/glusterFS", config, verbose)
	
# Deploy glusterFS on a cluster
def start_glusterFS_heketi( masternodes, ipToHostname, nodesinfo, glusterFSargs, flag = "-g"):
	glusterFSJson = GlusterFSJson(ipToHostname, nodesinfo, glusterFSargs)
	glusterFSJsonFilename = "deploy/storage/glusterFS/topology.json"
	print "Write GlusterFS configuration file to: " + glusterFSJsonFilename
	glusterFSJson.dump(glusterFSJsonFilename)
	glusterFS_copy()
	rundir = "/tmp/start_glusterFS"
	# use the same heketidocker as in heketi deployment
	remotecmd = "docker pull "+config["heketi-docker"]+"; "
	remotecmd += "docker run -v "+rundir+":"+rundir+" --rm --entrypoint=cp "+config["heketi-docker"]+" /usr/bin/heketi-cli "+rundir+"; "
	remotecmd += "sudo bash ./gk-deploy "
	remotecmd += flag
	utils.SSH_exec_cmd_with_directory( config["ssh_cert"], "core", masternodes[0], "deploy/storage/glusterFS", remotecmd, dstdir = rundir )

# Deploy glusterFS on a cluster
def remove_glusterFS_volumes_heketi( masternodes, ipToHostname, nodesinfo, glusterFSargs, nodes ):
	exit()
	start_glusterFS_heketi( masternodes, ipToHostname, nodesinfo, glusterFSargs, flag = "-g --yes --abort")
	for node in nodes:
		glusterFS_copy()
		rundir = "/tmp/glusterFSAdmin"
		remotecmd = "sudo python RemoveLVM.py "
		utils.SSH_exec_cmd_with_directory( config["ssh_cert"], "core", node, "deploy/storage/glusterFS", remotecmd, dstdir = rundir )
		
def regmatch_glusterFS( glusterFSargs ):
	if isinstance( glusterFSargs, (int,long) ):
		regexp = "/dev/[s|h]d[^a]"+str(glusterFSargs)
	else:
		regexp = glusterFSargs
	#print regexp
	regmatch = re.compile(regexp)
	return regmatch

def find_glusterFS_volume( alldeviceinfo, regmatch ):	
	deviceList = {}
	for bdevice in alldeviceinfo:
		deviceinfo = alldeviceinfo[bdevice] 
		for part in deviceinfo["parted"]:
			bdevicename = deviceinfo["name"] + str(part)
			#print bdevicename
			match = regmatch.search(bdevicename)
			if not ( match is None ):
				deviceList[match.group(0)] = deviceinfo["parted"][part]
	#print deviceList; 
	return deviceList

# Form a configuration file for operation of glusterfs 
def write_glusterFS_configuration( nodesinfo, glusterFSargs ):
	config_file = fetch_config_and_check( ["glusterFS", "glustefs_nodes_yaml" ])
	config_glusterFS = fetch_config_and_check( ["glusterFS"] )
	glusterfs_volumes_config = fetch_dictionary( config_glusterFS, ["gluster_volumes"] )
	required_param = fetch_dictionary( config_glusterFS, ["gluster_volumes_required_param"] )
	config_glusterFS["groups"] = {}
	glusterfs_groups = config_glusterFS["groups"]
	for node in nodesinfo:
		node_basename = kubernetes_get_node_name( node )
		node_config = fetch_config( ["machine", node_basename ] )
		glusterfs_group = "default" if node_config is None or not "glusterfs" in node_config else node_config["glusterfs"]
		if not glusterfs_group in glusterfs_groups:
			glusterfs_groups[glusterfs_group] = {}
			glusterfs_groups[glusterfs_group]["gluster_volumes"] = glusterfs_volumes_config["default"] if not glusterfs_group in glusterfs_volumes_config else glusterfs_volumes_config[glusterfs_group]
			# make sure required parameter are there for each volume
			for volume, volume_config in glusterfs_groups[glusterfs_group]["gluster_volumes"].iteritems():
				for param in required_param:
					if not param in volume_config:
						print "Error: please check configuration file ..." 
						print "Gluster group %s volume %s doesn't have a required parameter %s" % (glusterfs_group, volume, param) 
						exit()
			glusterfs_groups[glusterfs_group]["nodes"] = []
		glusterfs_groups[glusterfs_group]["nodes"].append( node )
	with open(config_file,'w') as datafile:
		yaml.dump(config_glusterFS, datafile, default_flow_style=False)
	return config_glusterFS
	
# Form YAML file for glusterfs endpoints, launch glusterfs endpoints. 
def launch_glusterFS_endpoint( nodesinfo, glusterFSargs ):
	os.system( "mkdir -p ./deploy/services/glusterFS_ep" )
	config_glusterFS = write_glusterFS_configuration( nodesinfo, glusterFSargs )
	glusterfs_groups = config_glusterFS["groups"]
	with open("./services/glusterFS_ep/glusterFS_ep.yaml",'r') as config_template_file:
		config_template = yaml.load( config_template_file )
		config_template_file.close()
	for group, group_config in glusterfs_groups.iteritems():
		config_template["metadata"]["name"] = "glusterfs-%s" % group
		config_template["subsets"] = []
		endpoint_subsets = config_template["subsets"]
		for node in nodes:
			ip = socket.gethostbyname(node)
			endpoint_subsets.append({"addresses": [{"ip":ip}] , "ports": [{"port":1}] })
		fname = "./deploy/services/glusterFS_ep/glusterFS_ep_%s.yaml" % group
		with open( fname, 'w') as config_file:
			yaml.dump(config_template, config_file, default_flow_style=False)
		run_kubectl( ["create", "-f", fname ] )

def stop_glusterFS_endpoint( ):
	glusterfs_groups = config_glusterFS["groups"]
	for group, group_config in glusterfs_groups.iteritems():
		fname = "./deploy/services/glusterFS_ep/glusterFS_ep_%s.yaml" % group
		run_kubectl( ["delete", "-f", fname ] )

# Path to mount name 
# Change path, e.g., /mnt/glusterfs/localvolume to 
# name mnt-glusterfs-localvolume
def path_to_mount_service_name( path ):
	return path.replace('/','-')[1:]

# Create gluster FS volume 
def create_glusterFS_volume( nodesinfo, glusterFSargs ):
	utils.render_template_directory("./storage/glusterFS", "./deploy/storage/glusterFS", config, verbose)
	config_glusterFS = write_glusterFS_configuration( nodesinfo, glusterFSargs )
	regmatch = regmatch_glusterFS(glusterFSargs)
	for node in nodesinfo:
		alldeviceinfo = nodesinfo[node]
		volumes = find_glusterFS_volume( alldeviceinfo, regmatch )
		print "................. Node %s ................." % node
		remotecmd = "";
		remotecmd += "sudo modprobe dm_thin_pool; "
		capacityGB = 0.0
		for volume in volumes:
			remotecmd += "sudo pvcreate -f "  
			dataalignment = fetch_config( ["glusterFS", "dataalignment"] )
			if not dataalignment is None: 
				remotecmd += " --dataalignment " + dataalignment;
			remotecmd += " " + volume + "; "
			capacityGB += volumes[volume]
		if len(volumes)>0: 
			remotecmd += "sudo vgcreate "
			physicalextentsize = fetch_config( ["glusterFS", "physicalextentsize"] )
			if not physicalextentsize is None: 
				remotecmd += " --physicalextentsize " + physicalextentsize;
			volumegroup = fetch_config_and_check( ["glusterFS", "volumegroup" ] )
			remotecmd += " " + volumegroup
			for volume in volumes:
				remotecmd += " " + volume; 
			remotecmd += "; "
		else:
			# The machine doesn't have any data disk, skip glusterFS setup
			break; 
		volumesize = fetch_config_and_check( ["glusterFS", "volumesize" ] )
		metasize = fetch_config_and_check(["glusterFS", "metasize" ] )
		metapoolname = fetch_config_and_check(["glusterFS", "metapoolname" ] )
		# create metapool 
		remotecmd += "sudo lvcreate -L %s --name %s %s ; " % ( metasize, metapoolname, volumegroup )
		# create datapool 
		volumesize = fetch_config_and_check(["glusterFS", "volumesize" ] )
		datapoolname = fetch_config_and_check(["glusterFS", "datapoolname" ] )
		remotecmd += "sudo lvcreate -l %s --name %s %s ; " % ( volumesize, datapoolname, volumegroup )
		chunksize = fetch_config_and_check(["glusterFS", "chunksize" ] )
		remotecmd += "sudo lvconvert -y --chunksize %s --thinpool %s/%s --poolmetadata %s/%s ; " % ( chunksize, volumegroup, datapoolname, volumegroup, metapoolname )
		remotecmd += "sudo lvchange -y --zero n %s/%s; " %( volumegroup, datapoolname )
		volumename = fetch_config_and_check(["glusterFS", "volumename" ] )
		remotecmd += "sudo lvcreate -y -V %dG -T %s/%s -n %s ;" %( int(capacityGB), volumegroup, datapoolname, volumename )
		mkfsoptions = fetch_config_and_check(["glusterFS", "mkfs.xfs.options" ] )
		remotecmd += "sudo mkfs.xfs -f %s /dev/%s/%s ;" %( mkfsoptions, volumegroup, volumename )
		# Create a service for volume mount
		remotepath = config["glusterfs-localvolume"]
		remotename = path_to_mount_service_name( remotepath )
		remotedevice = config["glusterfs-device"]
		remotemount = remotename + ".mount"
		utils.sudo_scp(config["ssh_cert"],"./deploy/storage/glusterFS/mnt-glusterfs-localvolume.mount", "/etc/systemd/system/" + remotemount, "core", node, verbose=verbose )
		remotecmd += "cd /etc/systemd/system; "
		remotecmd += "sudo systemctl enable %s; " % remotemount
		remotecmd += "sudo systemctl daemon-reload; ";
		remotecmd += "sudo systemctl start %s; " % remotemount;
		groupinfo = launch_glusterfs.find_group( config_glusterFS, node )
		group = groupinfo[0]
		group_config = groupinfo[1]
		othernodes = groupinfo[2]
		gluster_volumes = group_config["gluster_volumes"]
		for volume, volume_config in gluster_volumes.iteritems():
			multiple = volume_config["multiple"]
			numnodes = len(othernodes) + 1
			# Find the number of subvolume needed. 
			subvolumes = 1
			while ( numnodes * subvolumes ) % multiple !=0:
				subvolumes +=1; 
			if verbose: 
				print( "Volume %s, multiple is %d, # of nodes = %d, make %d volumes ..." % (volume, multiple, numnodes, subvolumes) )
			for sub in range(1, subvolumes + 1 ):
				remotecmd += "sudo mkdir -p %s; " % ( os.path.join( remotepath, volume ) + str(sub) )
		utils.SSH_exec_cmd( config["ssh_cert"], "core", node, remotecmd )
	
def remove_glusterFS_volume( nodesinfo, glusterFSargs ):
	regmatch = regmatch_glusterFS(glusterFSargs)
	for node in nodesinfo:
		alldeviceinfo = nodesinfo[node]
		volumes = find_glusterFS_volume( alldeviceinfo, regmatch )
		print "................. Node %s ................." % node
		remotecmd = "";
		if len(volumes)>0: 
			volumegroup = fetch_config_and_check( ["glusterFS", "volumegroup" ] )
			datapoolname = fetch_config_and_check( ["glusterFS", "datapoolname" ] )	
			volumename = fetch_config_and_check(["glusterFS", "volumename" ] )
			remotecmd += "sudo lvremove -y %s/%s ; " % ( volumegroup, volumename )
			remotecmd += "sudo lvremove -y %s/%s ; " % ( volumegroup, datapoolname )
			remotecmd += "sudo vgremove -y %s ; " % volumegroup
		else:
			# The machine doesn't have any data disk, skip glusterFS removal
			break; 	
		for volume in volumes:
			remotecmd += "sudo pvremove -y %s; " % volume
		# print remotecmd
		utils.SSH_exec_cmd( config["ssh_cert"], "core", node, remotecmd )		

def display_glusterFS_volume( nodesinfo, glusterFSargs ):
	regmatch = regmatch_glusterFS(glusterFSargs)
	for node in nodes:
		print "................. Node %s ................." % node
		remotecmd = "sudo pvdisplay; sudo vgdisplay; sudo lvdisplay"
		utils.SSH_exec_cmd( config["ssh_cert"], "core", node, remotecmd )

def exec_on_all(nodes, args, supressWarning = False):
	cmd = ""
	for arg in args:
		if cmd == "":
			cmd += arg
		else:
			cmd += " " + arg
	for node in nodes:
		utils.SSH_exec_cmd(config["ssh_cert"], "core", node, cmd)
		print "Node: " + node + " exec: " + cmd

def exec_on_all_with_output(nodes, args, supressWarning = False):
	cmd = ""
	for arg in args:
		if cmd == "":
			cmd += arg
		else:
			cmd += " " + arg
	for node in nodes:
		output = utils.SSH_exec_cmd_with_output(config["ssh_cert"], "core", node, cmd, supressWarning)
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
	utils.SSH_exec_cmd_with_directory(config["ssh_cert"], "core", node, srcdir, fullcmd, supressWarning)
		

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
			macs = utils.get_mac_address(config["ssh_cert"], node, show=False )
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
				#if isinstance( domainEntry, basestring):
				#	usename = namelist[0] + "." + domainEntry
				#else:
				#	usename = namelist[0]
				usename = namelist[0]
				cmd = "sudo hostnamectl set-hostname " + usename
				print "Set hostname of node " + node + " ... " + usename
				utils.SSH_exec_cmd( config["ssh_cert"], "core", node, cmd )

def deploy_ETCD_master():
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
				urllib.urlretrieve (config["homeinserver"]+"/SetClusterInfo?clusterId=%s&key=api_server&value=%s" % (config["clusterId"],config["api_servers"]))
				return True
			return False
			
#			response = raw_input_with_default("Create ISO file for deployment (y/n)?")
#			if first_char(response) == "y":
#				create_ISO()

#			response = raw_input_with_default("Create PXE docker image for deployment (y/n)?")
#			if first_char(response) == "y":
#				create_PXE()

		else:
			print "Cannot deploy cluster since there are insufficient number of etcd server or master server. \n To continue deploy the cluster we need at least %d etcd server(s)" % (int(config["etcd_node_num"]))
			return False
			
def update_config_node( node ):
	role = SSH_exec_cmd_with_output( )
			
def update_config_nodes():
	nodes = get_nodes(config["clusterId"])
	for node in nodes:
		update_config_node( node )

# Running a kubectl commands. 
def run_kube( prog, commands ):
	nodes = get_ETCD_master_nodes(config["clusterId"])
	master_node = random.choice(nodes)
	one_command = " ".join(commands)
	kube_command = ("%s --server=https://%s:%s --certificate-authority=%s --client-key=%s --client-certificate=%s %s" % (prog, master_node, config["k8sAPIport"], "./deploy/ssl/ca/ca.pem", "./deploy/ssl/kubelet/apiserver-key.pem", "./deploy/ssl/kubelet/apiserver.pem", one_command) )
	if verbose:
		print kube_command
	os.system(kube_command)

def run_kubectl( commands ):
	run_kube( "./deploy/bin/kubectl", commands)
	
def kubernetes_get_node_name(node):
	domain = get_domain()
	if len(domain) < 2: 
		return node
	elif domain in node:
		# print "Remove domain %d" % len(domain)
		return node[:-(len(domain))]
	else:
		return node

def render_service_templates():
	# Multiple call of render_template will only render the directory once during execution. 
	utils.render_template_directory( "./services/", "./deploy/services/", config)
	
def get_all_services():
	render_service_templates()
	rootdir = "./deploy/services"
	servicedic = {}
	for service in os.listdir(rootdir):
		dirname = os.path.join(rootdir, service)
		if os.path.isdir(dirname):
			yamlname = os.path.join(dirname, service + ".yaml")
			if os.path.isfile(yamlname):
				servicedic[service] = yamlname
			else:
				yamls = glob.glob("*.yaml")
				servicedic[service] = yamls[0]
	return servicedic
	
def get_service_name(service_config_file):
	f = open(service_config_file)
	service_config = yaml.load(f)
	f.close()
	# print service_config
	name = fetch_dictionary(service_config, ["metadata","name"])
	if not name is None:
		return name
	else:
		name = fetch_dictionary(service_config, ["spec","template","metadata","name"])
		if not name is None:
			return name
		else:
			return None

def get_service_yaml( use_service ):
	servicedic = get_all_services()
	newentries = {}
	for service in servicedic:
		servicename = get_service_name(servicedic[service])
		newentries[servicename] = servicedic[service]
	servicedic.update(newentries)
	fname = servicedic[use_service]
	return fname
			
def kubernetes_label_node(cmdoptions, nodename, label):
	run_kubectl(["label nodes %s %s %s" % (cmdoptions, nodename, label)])


def kubernetes_label_nodes( verb, servicelists, force ):
	servicedic = get_all_services()
	get_nodes(config["clusterId"])
	labels = fetch_config(["kubelabels"])
	for service in servicedic:
		servicename = get_service_name(servicedic[service])
		if (not service in labels) and (not servicename in labels) and "default" in labels:
			labels[servicename] = labels["default"]
	if len(servicelists)==0:
		servicelists = labels
	else:
		for service in servicelists:
			if (not service in labels) and "default" in labels:
				labels[service] = labels["default"]
	# print servicelists
	for label in servicelists:
		nodetype = labels[label]
		if nodetype == "worker_node":
			nodes = config["worker_node"]
		elif nodetype == "etcd_node":
			nodes = config["etcd_node"]
		elif nodetype.find( "etcd_node_" )>=0:
			nodenumber = int(nodetype[nodetype.find( "etcd_node_" )+len("etcd_node_"):])
			nodes = [ config["etcd_node"][nodenumber-1] ]
		elif nodetype == "all":
			nodes = config["worker_node"] + config["etcd_node"]
		else:
			print "Unknown nodes type %s in kubelabels in configuration file." % nodetype
			exit(-1)
		if verbose: 
			print "kubernetes: apply label %s to %s, nodes: %s" %(label, nodetype, nodes)
		if force:
			cmdoptions = "--overwrite"
		else:
			cmdoptions = ""
		for node in nodes:
			nodename = kubernetes_get_node_name(node)
			if verb == "active":
				kubernetes_label_node(cmdoptions, nodename, label+"=active")
			elif verb == "inactive":
				kubernetes_label_node(cmdoptions, nodename, label+"=inactive")
			elif verb == "remove":
				kubernetes_label_node(cmdoptions, nodename, label+"-")



def start_kube_service( servicename ):
	fname = get_service_yaml( servicename )
	# print "start service %s with %s" % (servicename, fname)
	if verbose:
		f = open(fname)
		service_yaml = yaml.load(f)
		f.close()
		print "Start service: "
		print service_yaml
	run_kubectl( ["create", "-f", fname ] )

def stop_kube_service( servicename ):
	fname = get_service_yaml( servicename )
	run_kubectl( ["delete", "-f", fname ] )
	
def replace_kube_service( servicename ):
	fname = get_service_yaml( servicename )
	run_kubectl( ["replace --force", "-f", fname ] )
	
def run_kube_command_node(verb, nodes):
	for node in nodes:
		nodename = kubernetes_get_node_name(node)
		run_kubectl( [verb, nodename ] )
		
def run_kube_command_on_nodes( nargs ):
	verb = nargs[0]
	if len(nargs)>1:
		nodes = nargs[1:]
	else:
		nodes = get_ETCD_master_nodes(config["clusterId"])
	run_kube_command_node( verb, nodes)
	
def render_docker_images():
	if verbose:
		print "Rendering docker-images from template ..."
	utils.render_template_directory("../docker-images/","./deploy/docker-images",config, verbose)

def build_docker_images(nargs):
	render_docker_images()
	if verbose:
		print "Build docker ..."
	build_dockers("./deploy/docker-images/", config["dockerprefix"], config["dockertag"], nargs, verbose, nocache = nocache )
	
def push_docker_images(nargs):
	render_docker_images()
	if verbose:
		print "Build & push docker images to docker register  ..."
	push_dockers("./deploy/docker-images/", config["dockerprefix"], config["dockertag"], nargs, config, verbose, nocache = nocache )
	
def run_docker_image( imagename, native = False ):
	full_dockerimage_name = build_docker_fullname( config, imagename )
	matches = find_dockers( full_dockerimage_name )
	if len( matches ) == 0:
		matches = find_dockers( imagename )
	if len( matches ) == 0:
		print "Error: can't find any docker image built by name %s, you may need to build the relevant docker first..." % imagename
	elif len( matches ) > 1: 
		print "Error: find multiple dockers by name %s as %s, you may need to be more specific on which docker image to run " % ( imagename, str(matches))
	else:
		if native: 
			os.system( "docker run --rm -ti " + matches[0] )
		else:
			run_docker( matches[0], prompt = imagename )
	

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
  production [nodes] Deploy a production cluster, with tasks of:
            set hostname, deploy etcd/master nodes, deploy worker nodes, uncordon master nodes. 
  deploy    Deploy DL workspace cluster.
  updateworker [nodes] Update the worker nodes. If no additional node is specified, all nodes will be updated. 
  clean     Clean away a failed deployment.
  update    [args] Update cluster. 
            config: update cloud-config of each deployed node. 
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
  glusterfs [args] manage glusterFS on the cluster. 
            display: display lvm information on each node of the cluster. 
            create: formatting and create lvm for used by glusterfs. 
            remove: deletel and remove glusterfs volumes. 
            config: generate configuration file, build and push glusterfs docker.
            start: start glusterfs service and endpoints. 
            stop: stop glusterfs service and endpoints. 
  download  [args] Manage download
            kubectl: download kubelet/kubectl.
            kubelet: download kubelet/kubectl.
  backup    [fname] [key] Backup configuration & encrypt, fname is the backup file without surfix. 
            If key exists, the backup file will be encrypted. 
  restore   [fname] [key] Decrypt & restore configuration, fname is the backup file with surfix. 
            If the backup file is encrypted, a key needs to be provided to decrypt the configuration. 
  etcd      [args] manage etcd server.
            check: check ETCD service.
  kubernetes [args] manage kubelet services on the cluster. 
            start: launch a certain kubelet service. 
            stop: stop a certain kubelet service. 
            restart: replace a certain kubelet service. 
            cordon [node]: cordon certain nodes. If no node, cordon all etcd nodes. 
            uncordon [node]: uncordon certain nodes. If no node, uncordon all etcd nodes. 
            labels verb [services]: applying labels to node. 
              -y: overwrite existing value
              verb: active, inactive, remove (default=on)
              services: if none, apply to all services in the service directory
  kubectl   [args] run a native kubectl command. 
  docker    [args] manage docker images. 
            build: build one or more docker images associated with the current deployment. 
            push: build and push one or more docker images to register
  execonall [cmd ... ] Execute the command on all nodes and print the output. 
  doonall [cmd ... ] Execute the command on all nodes. 
  runscriptonall [script] Execute the shell/python script on all nodes. 
  listmac   display mac address of the cluster notes
  checkconfig   display config items
  ''') )
	parser.add_argument("-y", "--yes", 
		help="Answer yes automatically for all prompt", 
		action="store_true" )
	parser.add_argument("--native", 
		help="Run docker in native mode (in how it is built)", 
		action="store_true" )	
	parser.add_argument("-p", "--public", 
		help="Use public IP address to deploy/connect [e.g., Azure, AWS]", 
		action="store_true")
	parser.add_argument("-s", "--sudo", 
		help = "Execute scripts in sudo", 
		action="store_true" )
	parser.add_argument("--discoverserver", 
		help = "Specify an alternative discover server, default = " + default_config_parameters["discoverserver"], 
		action="store", 
		default=default_config_parameters["discoverserver"])
	parser.add_argument("--homeinserver", 
		help = "Specify an alternative home in server, default = " + default_config_parameters["homeinserver"], 
		action="store", 
		default=default_config_parameters["homeinserver"])
	parser.add_argument("-v", "--verbose", 
		help = "verbose print", 
		action="store_true")
	parser.add_argument("--nocache", 
		help = "Build docker without cache", 
		action="store_true")

	parser.add_argument("--glusterfs", 
		help = textwrap.dedent('''"Additional glusterfs launch parameter, \
        detach: detach all glusterfs nodes (to rebuild cluster), 
        start: initiate cluster (all nodes need to be operative during start stage to construct the cluster),
        run: continuous operation, 
		''' ), 
		action="store", 
		default="run" )
		
	parser.add_argument("command", 
		help = "See above for the list of valid command" )
	parser.add_argument('nargs', nargs=argparse.REMAINDER, 
		help="Additional command argument", 
		)
	args = parser.parse_args()
	nocache = args.nocache
	
	# If necessary, show parsed arguments. 
	# print args
	discoverserver = args.discoverserver
	homeinserver = args.homeinserver
	if args.verbose: 
		verbose = True
		utils.verbose = True
	
	config = init_config()
	
	command = args.command
	nargs = args.nargs
	if command == "restore":
		utils.restore_keys(nargs)
		get_kubectl_binary()
		exit()
	
	# Cluster Config
	config_cluster = os.path.join(dirpath,"cluster.yaml")
	if os.path.exists(config_cluster):
		merge_config( config, yaml.load(open(config_cluster)))

	config_file = os.path.join(dirpath,"config.yaml")
	# print "Config file: " + config_file
	if not os.path.exists(config_file):
		parser.print_help()
		print "ERROR: config.yaml does not exist!"
		exit()
		
	
	f = open(config_file)
	merge_config(config, yaml.load(f))
	f.close()
	# print config
	if os.path.exists("./deploy/clusterID.yml"):
		f = open("./deploy/clusterID.yml")
		tmp = yaml.load(f)
		f.close()
		if "clusterId" in tmp:
			config["clusterId"] = tmp["clusterId"]
	update_config()
	
	# additional glusterfs launch parameter.
	config["launch-glusterfs-opt"] = args.glusterfs;

	get_ssh_config()
	
	if args.yes:
		print "Use yes for default answer"
		defanswer = "yes"
		
	if args.public:
		ipAddrMetaname = "clientIP"
		
	
	if verbose: 
		print "deploy " + command + " " + (" ".join(nargs))

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
			utils.SSH_connect( config["ssh_cert"], "core", nodename)
			exit()

	elif command == "deploy" and "clusterId" in config:
		deploy_ETCD_master()

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
			update_worker_nodes( nargs )
			
	elif command == "resetworker":
		response = raw_input_with_default("Deploy Worker Nodes (y/n)?")
		if first_char(response) == "y":
			check_master_ETCD_status()
			gen_configs()
			reset_worker_nodes()

	elif command == "listmac":
		nodes = get_nodes(config["clusterId"])
		for node in nodes:
			utils.get_mac_address(config["ssh_cert"], node)
			
	elif command == "uncordon":
		uncordon_master()
		
	elif command == "checkconfig":
		for k,v in config.iteritems():
			print str(k)+":"+str(v)


	elif command == "hostname" and len(nargs) >= 1:
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
		nodes = get_nodes(config["clusterId"])
		if nargs[0] == "ls":
		# Display parititons.  
			print "Show partition on data disk: " + config["data-disk"]
			nodesinfo = show_partitions(nodes, config["data-disk"] )
			
		elif nargs[0] == "create":
			partsInfo = config["partition-configuration"]
			if len(nargs) >= 2:
				partsInfo = nargs[1:]
			partsInfo = map(float, partsInfo)
			if len(partsInfo)==1 and partsInfo[0] == 0:
				print "0 partitions, use the disk as is, do not partition"
			elif len(partsInfo)==1 and partsInfo[0] < 30:
				partsInfo = [100.0]*int(partsInfo[0])
			nodesinfo = show_partitions(nodes, config["data-disk"] )
			print ("This operation will DELETE all existing partitions and repartition all data drives on the %d nodes to %d partitions of %s" % (len(nodes), len(partsInfo), str(partsInfo)) )
			response = raw_input ("Please type (REPARTITION) in ALL CAPITALS to confirm the operation ---> ")
			if response == "REPARTITION":
				repartition_nodes( nodes, nodesinfo, partsInfo)
			else:
				print "Repartition operation aborted...."
		else:
			parser.print_help()
			exit()
	
	elif command == "glusterFS_heketi" and len(nargs) >= 1:
		# nodes = get_nodes(config["clusterId"])
		# ToDo: change pending, schedule glusterFS on master & ETCD nodes, 
		if nargs[0] == "start" or nargs[0] == "update" or nargs[0] == "stop" or nargs[0] == "clear":
			nodes = get_worker_nodes(config["clusterId"])
			nodesinfo = get_partitions(nodes, config["data-disk"] )
			glusterFSargs = fetch_config( ["glusterFS", "partitions"] )
			if glusterFSargs is None:
				parser.print_help()
				print "Need to configure partitions which glusterFS will deploy..."
				exit()
			masternodes = get_ETCD_master_nodes(config["clusterId"])
			gsFlag = ""
			if nargs[0] == "start":
				exec_on_all(nodes, ["sudo modprobe dm_thin_pool"])
				gsFlag = "-g"
			elif nargs[0] == "stop":
				gsFlag = "--yes -g --abort"
			if nargs[0] == "start":
				remove_glusterFS_volumes_heketi( masternodes, config["ipToHostname"], nodesinfo, glusterFSargs, nodes )
			elif nargs[0] == "stop":
				start_glusterFS_heketi( masternodes, fetch_config(["ipToHostname"]), nodesinfo, glusterFSargs, flag = gsFlag )
			
				
		else:
			parser.print_help()
			exit()
			
	elif command == "glusterfs" and len(nargs) >= 1:
		# nodes = get_nodes(config["clusterId"])
		# ToDo: change pending, schedule glusterFS on master & ETCD nodes, 
		nodes = get_worker_nodes(config["clusterId"])	
		glusterFSargs = fetch_config( ["glusterFS", "partitions"] )
		if nargs[0] == "display":
			display_glusterFS_volume( nodes, glusterFSargs )
			exit()
				
		nodesinfo = get_partitions(nodes, config["data-disk"] )
		if glusterFSargs is None:
			parser.print_help()
			print "Need to configure partitions which glusterFS will deploy..."
			exit()
		if nargs[0] == "create":
			print ("This operation will CREATE new volume over all existing glusterFS partitions, and will erase the data on those partitions "  )
			response = raw_input ("Please type (CREATE) in ALL CAPITALS to confirm the operation ---> ")
			if response == "CREATE":
				create_glusterFS_volume( nodesinfo, glusterFSargs )
		elif nargs[0] == "remove":
			print ("This operation will REMOVE volumes over all existing glusterFS partitions, and will erase the data on those partitions "  )
			response = raw_input ("Please type (REMOVE) in ALL CAPITALS to confirm the operation ---> ")
			if response == "REMOVE":
				remove_glusterFS_volume( nodesinfo, glusterFSargs )
		elif nargs[0] == "config":
			write_glusterFS_configuration( nodesinfo, glusterFSargs ) 
			dockername = fetch_config_and_check(["glusterFS", "glusterfs_docker"])
			push_docker_images( [dockername] )
		elif nargs[0] == "start":
			start_kube_service("glusterFS")
			launch_glusterFS_endpoint( nodesinfo, glusterFSargs )
		elif nargs[0] == "stop":
			stop_glusterFS_endpoint()
			stop_kube_service("glusterFS")
		else:
			parser.print_help()
			print "Unknown subcommand for glusterFS: " + nargs[0]
			exit()
			
	elif command == "doonall" and len(nargs)>=1:
		nodes = get_nodes(config["clusterId"])
		exec_on_all(nodes, nargs)
		
	elif command == "execonall" and len(nargs)>=1:
		nodes = get_nodes(config["clusterId"])
		print "Exec on all: " + str(nodes) 
		exec_on_all_with_output(nodes, nargs)

	elif command == "runscriptonall" and len(nargs)>=1:
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
		
	elif command == "labelwebui":
		label_webUI(nargs[0])
		
	elif command == "production":
		set_host_names_by_lookup()
		success = deploy_ETCD_master()
		if success: 
			update_worker_nodes( [] )
			
	elif command == "update" and len(nargs)>=1:
		if nargs[0] == "config":
			update_config_nodes()
			
	elif command == "kubectl":
		run_kubectl(nargs)
	
	elif command == "kubernetes":
		if len(nargs) >= 1: 
			if len(nargs)>=2:
				servicenames = nargs[1:]
			else:
				allservices = get_all_services()
				servicenames = []
				for service in allservices:
					servicenames.append(service)
				# print servicenames
			if nargs[0] == "start":
				# Start a kubelet service. 
				for servicename in servicenames:
					start_kube_service(servicename)
			elif nargs[0] == "stop":
				# stop a kubelet service.
				for servicename in servicenames:
					stop_kube_service(servicename)
			elif nargs[0] == "restart":
				# restart a kubelet service.
				for servicename in servicenames:
					replace_kube_service(servicename)
			elif nargs[0] == "labels":
				if len(nargs)>=2 and ( nargs[1] == "active" or nargs[1] == "inactive" or nargs[1] == "remove" ):
					kubernetes_label_nodes(nargs[1], nargs[2:], args.yes)
				elif len(nargs)==1:
					kubernetes_label_nodes("active", [], args.yes )
				else:
					parser.print_help()
					print "Error: kubernetes labels expect a verb which is either on, off or remove, but get: " + nargs[1]
			elif nargs[0] == "cordon" or nargs[0] == "uncordon":
				run_kube_command_on_nodes(nargs)
			else:
				parser.print_help()
				print "Error: Unknown kubernetes subcommand " + nargs[0]
		else:
			parser.print_help()
			print "Error: kubernetes need a subcommand."
			exit()
	
	elif command == "download":
		if len(nargs)>=1:
			if nargs[0] == "kubectl" or nargs[0] == "kubelet":
				get_kubectl_binary()
			else:
				parser.print_help()
				print "Error: unrecognized etcd subcommand."
				exit()
		else:
			parser.print_help()
			print "Error: etcd need a subcommand."
			exit()
	
	elif command == "etcd":
		if len(nargs)>=1:
			if nargs[0] == "check":
				get_ETCD_master_nodes(config["clusterId"])
				check_etcd_service()
			else:
				parser.print_help()
				print "Error: unrecognized etcd subcommand."
				exit()
		else:
			parser.print_help()
			print "Error: etcd need a subcommand."
			exit()
			
	elif command == "backup":
		utils.backup_keys(config["cluster_name"], nargs)
		
	elif command == "docker":
		if len(nargs)>=1:
			if nargs[0] == "build":
				build_docker_images(nargs[1:])
			elif nargs[0] == "push":
				push_docker_images(nargs[1:])
			elif nargs[0] == "run":
				if len(nargs)>=2:
					run_docker_image( nargs[1], args.native ) 
				else:
					parser.print_help()
					print "Error: docker run expects an image name "
			else:
				parser.print_help()
				print "Error: unkown subcommand %s for docker." % nargs[0]
				exit()
		else:
			parser.print_help()
			print "Error: docker needs a subcommand"
			exit()
	else:
		parser.print_help()
		print "Error: Unknown command " + command
