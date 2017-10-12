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
import glob
import copy
import numbers

from os.path import expanduser

import yaml
from jinja2 import Environment, FileSystemLoader, Template
import base64
import tempfile

from shutil import copyfile, copytree
import urllib
import socket
sys.path.append("storage/glusterFS")
from GlusterFSUtils import GlusterFSJson
sys.path.append("../utils")

import utils
from DockerUtils import push_one_docker, build_dockers, push_dockers, run_docker, find_dockers, build_docker_fullname, copy_from_docker_image
import k8sUtils
from config import config as k8sconfig

sys.path.append("../docker-images/glusterfs")
import launch_glusterfs
import az_tools
import acs_tools

capacityMatch = re.compile("\d+\.?\d*\s*[K|M|G|T|P]B")
digitsMatch = re.compile("\d+\.?\d*")
defanswer = ""
ipAddrMetaname = "hostIP"

# CoreOS version and channels, further configurable. 
coreosversion = "1235.9.0"
coreoschannel = "stable"
coreosbaseurl = ""
verbose = False
nocache = False
limitnodes = None

# These are the default configuration parameter
default_config_parameters = {
	# Kubernetes setting
	"service_cluster_ip_range" : "10.3.0.0/16", 
	"pod_ip_range" : "10.2.0.0/16", 
	# Home in server, to aide Kubernete setup
	"homeinserver" : "http://dlws-clusterportal.westus.cloudapp.azure.com:5000", 	

	# Discover server is used to find IP address of the host, it need to be a well-known IP address 
	# that is pingable. 
	"discoverserver" : "4.2.2.1", 
	"homeininterval" : "600", 
	"dockerregistry" : "mlcloudreg.westus.cloudapp.azure.com:5000/",
	"kubernetes_docker_image" : "mlcloudreg.westus.cloudapp.azure.com:5000/dlworkspace/hyperkube:v1.7.5", 
	"freeflow_route_docker_image" : "mlcloudreg.westus.cloudapp.azure.com:5000/dlworkspace/freeflow:0.16", 
	# There are two docker registries, one for infrastructure (used for pre-deployment)
	# and one for worker docker (pontentially in cluser)
	# A set of infrastructure-dockers 
	"infrastructure-dockers" : {"pxe": True, "pxe-ubuntu": True, }, 
	"dockerprefix" : "",
	"dockertag" : "latest",
	"etcd3port1" : "2379", # Etcd3port1 will be used by App to call Etcd 
	"etcd3port2" : "4001", # Etcd3port2 is established for legacy purpose. 
	"etcd3portserver" : "2380", # Server port for etcd
	"k8sAPIport" : "443", # Server port for etcd
	"nvidiadriverdocker" : "mlcloudreg.westus.cloudapp.azure.com:5000/nvidia_driver:375.20",
	"nvidiadriverversion" : "375.20",
	# Default port for WebUI, Restful API, 
	"webuiport" : "80",
	"restfulapiport" : "5000",
	"restfulapi" : "restfulapi",
	"ssh_cert" : "./deploy/sshkey/id_rsa",
    "admin_username" : "core", 
	# the path of where dfs/nfs is source linked and consumed on each node, default /dlwsdata
	"storage-mount-path" : "/dlwsdata",
	# the path of where filesystem is actually mounted /dlwsdata
	"physical-mount-path" : "/mntdlws",
	# the path of where local device is mounted. 
	"local-mount-path" : "/mnt",

	# required storage folder under storage-mount-path
	"default-storage-folders" : ["jobfiles", "storage", "work", "namenodeshare" ],
	"per_user_gpu_limit": "-1",

	# the path of where nvidia driver is installed on each node, default /opt/nvidia-driver/current
	"nvidia-driver-path" : "/opt/nvidia-driver/current", 
	"systemdisk": "/dev/sda",
	"data-disk": "/dev/[sh]d[^a]", 
	"partition-configuration": [ "1" ], 
	"heketi-docker": "heketi/heketi:dev",
	# The following file will be copied (not rendered for configuration)
	"render-exclude" : { 
		"GlusterFSUtils.pyc": True, 
		"launch_glusterfs.pyc": True, 
		"bootstrap_hdfs.pyc": True,
		},
	"render-by-copy-ext" : { 
		".png": True, 
		# All in-docker file will be copied and rendered in docker.
		".in-docker": True, },
	"render-by-copy": { 
		"gk-deploy":True, 
		"pxelinux.0": True, 
		# This template will be rendered inside container, but not at build stage
		# "hdfs-site.xml.template": True, 		
		},

	"docker-run" : {
		"hdfs" : {
			"workdir" : "/opt/hadoop", 
			"volumes" : {
				"configDir" : {
					"from" : "./deploy/etc/hdfs", 
					"to" : "/etc/hdfs", 
				},
			},
		},
		"pxe-ubuntu" : {
			"workdir" : "/", 
			"su" : True, 
			"options" : "--net=host", 
		},

	}, 

	"build-docker-via-config" : {
		"hdfs": True, 
		"spark": True, 
		"glusterfs": True, 
	},
	#"render-by-line": { "preseed.cfg": True, },
	# glusterFS parameter
	"glusterFS" : { "dataalignment": "1280K", 
					"physicalextentsize": "128K", 
					"volumegroup": "gfs_vg", 
					# metasize is total_capacity / physicalextentsize * 64
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
					# To use glusterFS, you will configure the partitions parameter
					# partitions: /dev/sd[^a]
					# which is a regular expression calls out all partition that will be deployed with glusterfs
					}, 
	# Options to run in glusterfs
	"launch-glusterfs-opt": "run", 

	# Govern how Kubernete nodes are labeled to deploy various kind of service deployment. :
	#   - label : etcd_node <tag to be applied to etcd node only >
	#   - label : worker_node <tag to be applied to worker node only >
	#   - label : all <tag to be applied to all nodes
	"kubelabels" : {
  		"infrastructure": "etcd_node", 
  		"worker": "worker_node", 
  		"all": "all", 
  		"default": "all",
		"glusterfs": "worker_node", 
		# HDFS node selector
		"hdfs": "worker_node",
		"zookeeper": "etcd_node", 
		"journalnode": "etcd_node",
		"namenode1": "etcd_node_1", 
		"namenode2": "etcd_node_2",
		"datanode": "all",
  		"webportal": "etcd_node_1", 
  		"restfulapi": "etcd_node_1", 
  		"jobmanager": "etcd_node_1", 
  		"FragmentGPUJob": "all", 
  	},

	"kubemarks" : [ "rack", "sku" ],

    "network": {
	   "trusted-domains" : {
		   "*.redmond.corp.microsoft.com" : True, 
		   "*.corp.microsoft.com": True,
	   }, 
	   "container-network-iprange" : "192.168.0.1/24",
	}, 


	"localdisk": {
		# The following pair of options control how local disk is formated and mounted
		"mkfscmd" : "mkfs -F -q -t ext4",
		"mountoptions": "ext4 defaults 0 1",
	},

	# optional hdfs_cluster_name: if not inherit cluster_name from cluster
	# "hdfs_cluster_name": cluster_name for HDFS

	"hdfsconfig" : {
		# Launch options for formatting, etc..
		"formatoptions" : "", 
		# Comma separated list of paths on the local filesystem of a DataNode where it should store its blocks.
		"dfs" : {
			# Data node configuration, 
			# Comma separated list of paths on the local filesystem of a DataNode where it should store its blocks
			# to be filled. 
			"data": "", 
		},
		"namenode" : {
			"localdata" : "/var/lib/namenode",
			"data": "/mnt/namenodeshare",
		},
		"zks" : {
			# The IP address should be within service_cluster_ip_range
			"ip" : "10.3.1.100",
			"port": "2181", 
			"data": "/var/lib/zookeeper",
		},
		"journalnode" : {
			"port": "8485",
			"data": "/var/lib/hdfsjournal",
		}, 
		# location of configuration file
		"configfile": "/etc/hdfs/config.yaml", 
		# logging directory
		"loggingDirBase": "/usr/local/hadoop/logs"
	}, 
	"ubuntuconfig" : {
		"version" : "16.04.1", 
		"16.04.2" : {
			"ubuntuImageUrl" : "http://releases.ubuntu.com/16.04/ubuntu-16.04.2-server-amd64.iso", 
			"ubuntuImageName" : "ubuntu-16.04.2-server-amd64.iso",
		},
		"16.04.1" : {
			"ubuntuImageUrl" : "http://old-releases.ubuntu.com/releases/16.04.1/ubuntu-16.04.1-server-amd64.iso",
			"ubuntuImageName" : "ubuntu-16.04.1-server-amd64.iso",
		},
	}, 

	"acskubeconfig" : "acs_kubeclusterconfig",
	"isacs" : False,
	"acsagentsize" : "Standard_NC12",

	"mountconfig": {
		"azurefileshare" : {
			"options" : "vers=3.0,username=%s,password=%s,dir_mode=0777,file_mode=0777,serverino",
		},
		"glusterfs" : {
			"options" : "defaults,_netdev",
		},
		"nfs" : {
			"options" : "rsize=8192,timeo=14,intr,tcp",
		},
		"hdfs" : {
			"fstaboptions" : "allow_other,usetrash,rw 2 0",
			"options": "rw -ousetrash -obig_writes -oinitchecks",
		},
		
	},

	"mountdescription" : {
		"azurefileshare" : "Azure file storage", 
		"glusterfs" : "GlusterFS (replicated distributed storage)", 
		"nfs" : "NFS (remote file share)",
		"hdfs" : "Hadoop file system (replicated distribute storage).", 
		"local" : "Local SSD. ", 
		"localHDD" : "Local HDD. ", 
		"emptyDir" : "Kubernetes emptyDir (folder will be erased after job termination).", 
	}, 

	"mounthomefolder" : "yes", 
	# Mount point to be deployed to container. 
	"deploymounts" : [ ], 

	
	# folder where automatic share script will be located
	"folder_auto_share" : "/opt/auto_share", 

	# Option to change pre-/post- deployment script
	# Available options are (case sensitive):
	# "default": CoreOS individual cluster
	# "philly": philly cluster
	# "ubuntu": ubuntu cluster
	"platform-scripts" : "default", 


	# Default usergroup for the WebUI portal
	# Default setting will allow all Microsoft employees to access the cluster, 
	# You should override this setting if you have concern. 
	"UserGroups": {
        # Group name
        "CCSAdmins": {
            # The match is in C# Regex Language, please refer to :
            # https://msdn.microsoft.com/en-us/library/az24scfc(v=vs.110).aspx
            "Allowed": [ "jinl@microsoft.com", "hongzl@microsoft.com" ],
            "uid": "900000000-999999999",
            "gid": "508953967"
        },
        "MicrosoftUsers": {
            # The match is in C# Regex Language, please refer to :
            # https://msdn.microsoft.com/en-us/library/az24scfc(v=vs.110).aspx
            "Allowed": [ "@microsoft.com" ],
            "uid": "900000000-999999999",
            "gid": "508953967"
        }, 
		"Live": {
            # The match is in C# Regex Language, please refer to :
            # https://msdn.microsoft.com/en-us/library/az24scfc(v=vs.110).aspx
            "Allowed": [ "@live.com", "@hotmail.com", "@outlook.com" ],
            "uid": "7000000000-7999999999",
            "gid": "508953967"
        }, 
		"Gmail": {
            # The match is in C# Regex Language, please refer to :
            # https://msdn.microsoft.com/en-us/library/az24scfc(v=vs.110).aspx
            "Allowed": [ "@gmail.com" ],
            "uid": "8000000000-8999999999",
            "gid": "508953967"
        }, 
    },

	"WebUIregisterGroups": [ "MicrosoftUsers", "Live", "Gmail" ], 
	"WebUIauthorizedGroups": [], # [ "MicrosoftUsers", "Live", "Gmail" ], 
	"WebUIadminGroups" : [ "CCSAdmins" ], 

	# Selectively deploy (turn on) one or more authenticatin methods. 
	# Parameter of the authentication method is in config.json file in WebUI. 
	# Please note for each authentication method deployed, the DL Workspace endpoint needs to registered with 
	# each corresponding App according to openID authentication. 
	"DeployAuthentications" : ["Corp","Live","Gmail"],
	# You should remove WinBindServers if you will use
	# UserGroups for authentication.  
	"WinbindServers": [ "http://onenet40.redmond.corp.microsoft.com/domaininfo/GetUserId?userName={0}" ],
	"workFolderAccessPoint" : "", 
	"dataFolderAccessPoint" : "", 

	"kube_configchanges" : ["/opt/addons/kube-addons/weave.yaml"],
	"kube_addons" : ["/opt/addons/kube-addons/dashboard.yaml", 
					 "/opt/addons/kube-addons/dns-addon.yaml",
					 "/opt/addons/kube-addons/kube-proxy.json",
					 "/opt/addons/kube-addons/collectd.yaml",
					 "/opt/addons/kube-addons/grafana.yaml",
					 "/opt/addons/kube-addons/heapster.yaml",
					 "/opt/addons/kube-addons/influxdb.yaml",
					 ],

    "Authentications": {
        "Live-login-windows": {
            "DisplayName": "Microsoft Account (live.com)",
            "Tenant": "microsoft.onmicrosoft.com",
            "ClientId": "55489cd6-b5b8-438d-ab42-4aba116ef8a3",
            "UseIdToken": "true",
            "Scope": "openid email profile",
            # "ClientSecret": "g1nNX9u6Q2tAiqWXdec5amRPadSJQnvsy03P+arDkCk=",
            "AuthorityFormat": "https://login.windows.net/common",
            "Domains": [ "live.com", "hotmail.com", "outlook.com" ]
        },
        "Live-login-microsoftonline": {
            "DisplayName": "Microsoft Account (live.com)",
            "Tenant": "microsoft.onmicrosoft.com",
            "ClientId": "55489cd6-b5b8-438d-ab42-4aba116ef8a3",
            "UseIdToken": "true",
            "Scope": "openid email profile",
            # "ClientSecret": "g1nNX9u6Q2tAiqWXdec5amRPadSJQnvsy03P+arDkCk=",
            "AuthorityFormat": "https://login.microsoftonline.com/common/v2.0",
            "Domains": [ "live.com", "hotmail.com", "outlook.com" ]
        }, 
        "Live": {
            "DisplayName": "Microsoft Account (live.com)",
            "Tenant": "jinlmsfthotmail.onmicrosoft.com",
            "ClientId": "734cc6a7-e80c-4b89-a663-0b9512925b45",
            "ClientSecret": "g1nNX9u6Q2tAiqWXdec5amRPadSJQnvsy03P+arDkCk=",
            "AuthorityFormat": "https://login.microsoftonline.com/{0}",
            "Domains": [ "live.com", "hotmail.com", "outlook.com" ]
        }, 
        "Aad": {
            "DisplayName": "Azure Graph",
            "UseAadGraph": "true",
            "UseToken": "true",
            "Tenant": "jinlmsfthotmail.onmicrosoft.com",
            "ClientId": "734cc6a7-e80c-4b89-a663-0b9512925b45",
            "ClientSecret": "g1nNX9u6Q2tAiqWXdec5amRPadSJQnvsy03P+arDkCk=",
            "AuthorityFormat": "https://login.microsoftonline.com/{0}",
            "RedirectUri": "",
            "GraphBaseEndpoint": "https://graph.windows.net",
            "GraphApiVersion": "1.6", # API version,
            "Scope": "User.Read",
            "Domains": [ "live.com", "hotmail.com", "outlook.com" ]
        },
        "Live-jinl-windows": {
            "DisplayName": "Live.com",
            "Tenant": "jinlmsfthotmail.onmicrosoft.com",
            "ClientId": "734cc6a7-e80c-4b89-a663-0b9512925b45",
            "ClientSecret": "g1nNX9u6Q2tAiqWXdec5amRPadSJQnvsy03P+arDkCk=",
            "AuthorityFormat": "https://login.windows.net/common",
            "RedirectUri": "",
            "GraphBaseEndpoint": "https://graph.windows.net",
            "GraphApiVersion": "1.6", # API version,
            # "Scope": "User.Read",
            "Domains": [ "live.com", "hotmail.com", "outlook.com" ]
        },
        "CorpAad": {
            "DisplayName": "@microsoft.com corpnet sign in",
            "UseAadGraph": "true",
            "UseToken": "true",
            "Tenant": "microsoft.onmicrosoft.com",
            "ClientId": "511c7514-3090-400e-873a-2fb05f2d5c19",
            "ClientSecret": "E3RT39WiTvfBrJLpfs8FYJcrvFDTqEjxrlu9G36CZZM=",
            "AuthorityFormat": "https://login.microsoftonline.com/{0}",
            "RedirectUri": "",
            "Scope": "User.Read",
            "GraphBaseEndpoint": "https://graph.windows.net",
            "GraphApiVersion": "1.6", # API version,
            "Domains": [ "microsoft.com" ]
        },       
        "Live-Microsoft": {
            "DisplayName": "Microsoft Account (live.com)",
            "Tenant": "jinlmsfthotmail.onmicrosoft.com",
            "ClientId": "734cc6a7-e80c-4b89-a663-0b9512925b45",
            "ClientSecret": "g1nNX9u6Q2tAiqWXdec5amRPadSJQnvsy03P+arDkCk=",
            "AuthorityFormat": "https://login.microsoftonline.com/{0}",
            "Domains": [ "live.com", "hotmail.com", "outlook.com" ]
        }, 

        "Corp": {
            "DisplayName": "@microsoft.com corpnet sign in",
            "UseAadGraph": "false",
            "Tenant": "microsoft.onmicrosoft.com",
            "ClientId": "511c7514-3090-400e-873a-2fb05f2d5c19",
            "ClientSecret": "E3RT39WiTvfBrJLpfs8FYJcrvFDTqEjxrlu9G36CZZM=",
            "AuthorityFormat": "https://login.microsoftonline.com/{0}",
            "RedirectUri": "",
            "GraphBaseEndpoint": "https://graph.windows.net",
            "GraphApiVersion": "1.6", # API version,
            "Domains": [ "microsoft.com" ]
        },
        "Gmail": {
            "DisplayName": "Gmail",
            "Tenant": "dlws-auth",
            "ClientId": "79875480060-jrs8a1rqe6a4kv82jh4d2nqgq8t6ap6k.apps.googleusercontent.com",
            "ClientSecret": "L6XfKLzIbiy7jT7s416CBamz",
            "AuthorityFormat": "https://accounts.google.com",
            "Scope": "openid email",
            "Domains": [ "gmail.com" ]
        },

    }

}

# These are super scripts
scriptblocks = {
	"azure": [
		"runscriptonall ./scripts/prepare_ubuntu.sh", 
		"-y deploy",
		"-y updateworker",
		"-y kubernetes labels",
		"webui",
		"docker push restfulapi",
		"docker push webui",
		"mount", 
  		"kubernetes start jobmanager",
  		"kubernetes start restfulapi",
  		"kubernetes start webportal",
	],
	"ubuntu_uncordon": [
		"runscriptonall ./scripts/prepare_ubuntu.sh",
		"-y deploy",
		"sleep 60",
		"-y updateworker",
		"sleep 30",
		"-y kubernetes labels",
		"kubernetes uncordon",
		"sleep 10",
		"mount",
		"webui",
		"docker push restfulapi",
		"docker push webui",
		"kubernetes start freeflow",
		"kubernetes start jobmanager",
		"kubernetes start restfulapi",
		"kubernetes start webportal",
	],
	"add_worker": [
		"sshkey install",
		"runscriptonall ./scripts/prepare_ubuntu.sh",
		"-y updateworker",
		"-y kubernetes labels",
		"mount",
	],	
	"bldwebui": [
		"webui",
		"docker push restfulapi",
		"docker push webui",
	],
	"restartwebui": [
		"kubernetes stop webportal",
		"kubernetes stop restfulapi",
		"kubernetes stop jobmanager",
		"webui",
		"sleep 30", 
		"kubernetes start jobmanager",
		"kubernetes start restfulapi",
		"kubernetes start webportal",
	],
	"ubuntu": [
		"runscriptonall ./scripts/prepare_ubuntu.sh",
		"-y deploy",
		"-y updateworker",
		"-y kubernetes labels",
		"mount",
		"webui",
		"docker push restfulapi",
		"docker push webui",
		"kubernetes start freeflow",
		"kubernetes start jobmanager",
		"kubernetes start restfulapi",
		"kubernetes start webportal",
	],
	"acs": [
		"acs deploy",
		"acs postdeploy",
		"acs storagemount",
		"acs gpudrivers",
		"acs freeflow",
		"acs bldwebui",
		"acs restartwebui",
	],
}

# default search for all partitions of hdb, hdc, hdd, and sdb, sdc, sdd

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def expand_path(path):
	return expanduser(path)

# Path to mount name 
# Change path, e.g., /mnt/glusterfs/localvolume to 
# name mnt-glusterfs-localvolume
def path_to_mount_service_name( path ):
	ret = path
	if ret[0]=='/':
		ret = ret[1:]
	if ret[-1]=='/':
		ret = ret[:-1]
	ret = ret.replace('-','\\x2d')
	ret = ret.replace('/','-')
	return ret

# Generate a server IP according to the cluster ip range. 
# E.g., given cluster IP range 10.3.0.0/16, index=1, 
# The generated IP is 10.3.0.1
def generate_ip_from_cluster(cluster_ip_range, index ):
	slash_pos = cluster_ip_range.find("/")
	ips = cluster_ip_range if slash_pos < 0 else cluster_ip_range[:slash_pos]
	ips3 = ips[:ips.rfind(".")]
	return ips3 + "." + str(index)
	
# Return a path name, expand on ~, for a particular config, 
# e.g., ssh_key
def expand_path_in_config(key_in_config):
	if key_in_config in config:
		return expand_path(config[key_in_config])
	else:
		raise Exception("Error: no %s in config " % key_in_config)

def parse_capacity_in_GB( inp ):
	# print "match capacity of %s" % inp
	mt = capacityMatch.search(inp)
	if mt is None: 
		return 0.0
	else:
		digits = digitsMatch.search(mt.group(0)).group(0)
		val = float(digits)
		if "GB" in mt.group(0):
			return float(val)
		elif "TB" in mt.group(0):
			return float(val) * 1000.0
		elif "PB" in mt.group(0):
			return float(val) * 1000000.0
		elif "KB" in mt.group(0):
			return float(val) / 1000000.0
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
	if not os.path.exists("./deploy"):
		os.system("mkdir -p ./deploy")
	config = {}
	for k,v in default_config_parameters.iteritems():
		config[ k ] = v
	return config

def apply_config_mapping():
	for k,tuple in default_config_mapping.iteritems():
		if not ( k in config ) or len(config[k])<=0:
			dstname = tuple[0]
			value = fetch_config(dstname)
			if not (value is None):
				config[k] = tuple[1](value)
				if verbose:
					print "Config[%s] = %s" %(k, config[k])

def _check_config_items(cnfitem, cnf):
	if not cnfitem in cnf:
		raise Exception("ERROR: we cannot find %s in config file" % cnfitem) 
	else:
		print "Checking configurations '%s' = '%s'" % (cnfitem, cnf[cnfitem])
 
def check_config(cnf):
	if not config["isacs"]:
		_check_config_items("discovery_url",cnf)
	_check_config_items("kubernetes_master_node",cnf)
	_check_config_items("kubernetes_master_ssh_user",cnf)
	_check_config_items("api_servers",cnf)
	_check_config_items("etcd_user",cnf)
	_check_config_items("etcd_node",cnf)
	_check_config_items("etcd_endpoints",cnf)
	_check_config_items("ssh_cert",cnf)
	_check_config_items("pod_ip_range",cnf)
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

def generate_trusted_domains(network_config, start_idx ):
	ret = ""
	domain = fetch_dictionary(network_config, ["domain"])
	if not (domain is None):
		ret += "DNS.%d = %s\n" % (start_idx, "*." + domain)
		start_idx +=1
	trusted_domains = fetch_dictionary(network_config, ["trusted-domains"])
	if not trusted_domains is None:
		for domain in trusted_domains:
			# "*." is encoded in domain for those entry
			ret += "DNS.%d = %s\n" % (start_idx, domain)
			start_idx +=1
	return ret

def get_platform_script_directory( target ):
	targetdir = target+"/"
	if target is None or target=="default":
		targetdir = "./"
	return targetdir

def get_root_passwd():
	fname = "./deploy/sshkey/rootpasswd"
	os.system("mkdir -p ./deploy/sshkey")
	if not os.path.exists(fname):
		with open(fname,'w') as f:
			passwd = uuid.uuid4().hex
			f.write(passwd)
			f.close()
	with open(fname,'r') as f:
		rootpasswd = f.read()
		f.close()
	return rootpasswd
	
# These parameter will be mapped if non-exist
# Each mapping is the form of: dstname: ( srcname, lambda )
# dstname: config name to be used.
# srcname: config name to be searched for (expressed as a list, see fetch_config)
# lambda: lambda function to translate srcname to target name
default_config_mapping = { 
	"dockerprefix": (["cluster_name"], lambda x:x.lower()+"/"), 
	"infrastructure-dockerregistry": (["dockerregistry"], lambda x:x), 
	"worker-dockerregistry": (["dockerregistry"], lambda x:x),
	"glusterfs-device": (["glusterFS"], lambda x: "/dev/%s/%s" % (fetch_dictionary(x, ["volumegroup"]), fetch_dictionary(x, ["volumename"]) ) ),
	"glusterfs-localvolume": (["glusterFS"], lambda x: fetch_dictionary(x, ["mountpoint"]) ),
	"storage-mount-path-name": (["storage-mount-path" ], lambda x: path_to_mount_service_name(x) ),
	"api-server-ip": (["service_cluster_ip_range"], lambda x: generate_ip_from_cluster(x, 1) ), 
	"dns-server-ip": (["service_cluster_ip_range"], lambda x: generate_ip_from_cluster(x, 53) ),
	"network-trusted-domains": (["network"], lambda x: generate_trusted_domains(x, 5 )),
	#master deployment scripts
	"premasterdeploymentscript" : (["platform-scripts"], lambda x: get_platform_script_directory(x)+"pre-master-deploy.sh"),
	"postmasterdeploymentscript" : (["platform-scripts"], lambda x: get_platform_script_directory(x)+"post-master-deploy.sh"),
	"mastercleanupscript" : (["platform-scripts"], lambda x: get_platform_script_directory(x)+"cleanup-master.sh"),
	"masterdeploymentlist" : (["platform-scripts"], lambda x: get_platform_script_directory(x)+"deploy.list"),
	#worker deployment scripts
	"preworkerdeploymentscript" : (["platform-scripts"], lambda x: get_platform_script_directory(x)+"pre-worker-deploy.sh"),
	"postworkerdeploymentscript" : (["platform-scripts"], lambda x: get_platform_script_directory(x)+"post-worker-deploy.sh"),
	"workercleanupscript" : (["platform-scripts"], lambda x: get_platform_script_directory(x)+"cleanup-worker.sh"),
	"workerdeploymentlist" : (["platform-scripts"], lambda x: get_platform_script_directory(x)+"deploy.list"),
	"pxeserverip": (["pxeserver"], lambda x: fetch_dictionary(x,["ip"])), 
	"pxeserverrootpasswd": (["pxeserver"], lambda x: get_root_passwd()), 
	"pxeoptions": (["pxeserver"], lambda x: "" if fetch_dictionary(x,["options"]) is None else fetch_dictionary(x,["options"])), 
	"hdfs_cluster_name" : ( ["cluster_name"], lambda x:x ),     
}
	
# Merge entries in config2 to that of config1, if entries are dictionary. 
# If entry is list or other variable, it will just be replaced. 
# say config1 = { "A" : { "B": 1 } }, config2 = { "A" : { "C": 2 } }
# C python operation: config1.update(config2) give you { "A" : { "C": 2 } }
# merge_config will give you: { "A" : { "B": 1, "C":2 } }
def merge_config( config1, config2 ):
	for entry in config2:
		if entry in config1:
			if isinstance( config1[entry], dict): 
				if isinstance( config2[entry], dict): 
					merge_config( config1[entry], config2[entry] )
				else:
					print "Error in configuration: %s should be of type %s, but is written as type %s in configuration" %(entry, type(config1[entry]), type(config2[entry]) )
					exit(1)
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

	for (cf, loc) in [('master', 'master'), ('worker', 'kubelet')]:
		exec("config[\"%s_predeploy\"] = os.path.join(\"./deploy/%s\", config[\"pre%sdeploymentscript\"])" % (cf, loc, cf))
		exec("config[\"%s_filesdeploy\"] = os.path.join(\"./deploy/%s\", config[\"%sdeploymentlist\"])" % (cf, loc, cf))
		exec("config[\"%s_postdeploy\"] = os.path.join(\"./deploy/%s\", config[\"post%sdeploymentscript\"])" % (cf, loc, cf))

def add_ssh_key():
	keys = fetch_config(["sshKeys"])
	if isinstance( keys, list ):
		if "sshkey" in config and "sshKeys" in config and not (config["sshkey"] in config["sshKeys"]):
			config["sshKeys"].append(config["sshkey"])
	elif "sshkey" in config:
		config["sshKeys"] = []
		config["sshKeys"].append(config["sshkey"])

def create_cluster_id():
	if (not os.path.exists('./deploy/clusterID.yml')):
		clusterId = {}
		clusterId["clusterId"] = str(uuid.uuid4())
		with open('./deploy/clusterID.yml', 'w') as f:
			f.write(yaml.dump(clusterId))
		config["clusterId"] = utils.get_cluster_ID_from_file()	
		print "Cluster ID is " + config["clusterId"]

def add_acs_config(command):
	if (command=="kubectl" and os.path.exists("./deploy/"+config["acskubeconfig"])):
		# optimize for faster execution
		config["isacs"] = True
	elif (command=="acs" or os.path.exists("./deploy/"+config["acskubeconfig"])):
		config["isacs"] = True
		create_cluster_id()

		#print "Config:{0}".format(config)
		#print "Dockerprefix:{0}".format(config["dockerprefix"])

		# Set ACS params to match
		acs_tools.config = config
		acs_tools.verbose = verbose

		# Use az tools to generate default config params and overwrite if they don't exist
		configAzure = acs_tools.acs_update_azconfig(False)
		if verbose:
			print "AzureConfig:\n{0}".format(configAzure)
		utils.mergeDict(config, configAzure, True) # ovewrites defaults with Azure defaults
		if verbose:
			print "Config:\n{0}".format(config)

		config["master_dns_name"] = config["cluster_name"]
		config["resource_group"] = az_tools.config["azure_cluster"]["resource_group_name"]
		config["platform-scripts"] = "acs"
		config["WinbindServers"] = []
		config["etcd_node_num"] = config["master_node_num"]
		config["kube_addons"] = [] # no addons
		config["mountpoints"]["rootshare"]["azstoragesku"] = config["azstoragesku"]
		config["mountpoints"]["rootshare"]["azfilesharequota"] = config["azfilesharequota"]
		config["freeflow"] = True

		if ("azure-sqlservername" in config) and (not "sqlserver-hostname" in config):
			config["sqlserver-hostname"] = ("tcp:%s.database.windows.net" % config["azure-sqlservername"])
		else:
			# find name for SQL Azure
			match = re.match('tcp:(.*)\.database\.windows\.net', config["sqlserver-hostname"])
			config["azure-sqlservername"] = match.group(1)

		# Some locations put VMs in child resource groups
		acs_tools.acs_set_resource_grp(False)

		# check for GPU sku
		match = re.match('.*\_N.*', config["acsagentsize"])
		if not match is None:
			config["acs_isgpu"] = True		
		else:
			config["acs_isgpu"] = False

		# Add users -- hacky going into CCSAdmins group!!
		if "webui_admins" in config:
			for name in config["webui_admins"]:
				if not name in config["UserGroups"]["CCSAdmins"]["Allowed"]:
					config["UserGroups"]["CCSAdmins"]["Allowed"].append(name)

		# domain name
		config["network"] = {}
		config["network"]["domain"] = "{0}.cloudapp.azure.com".format(config["cluster_location"])

		try:
			if not ("accesskey" in config["mountpoints"]["rootshare"]):
				azureKey = acs_get_storage_key()
				#print "ACS Storage Key: " + azureKey
				config["mountpoints"]["rootshare"]["accesskey"] = azureKey
		except:
			()

		if verbose:
			print "Config:{0}".format(config)

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
	gen_new_key = True
	regenerate_key = False
	if (os.path.isfile("./deploy/clusterID.yml")):
		clusterID = utils.get_cluster_ID_from_file()
		response = raw_input_with_default("There is a cluster (ID:%s) deployment in './deploy', do you want to keep the existing ssh key and CA certificates (y/n)?" % clusterID)
		if first_char(response) == "n":
			# Backup old cluster 
			utils.backup_keys(config["cluster_name"])
			regenerate_key = True
		else:
			gen_new_key = False
	if gen_new_key:
		utils.gen_SSH_key(regenerate_key)
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

	os.system( "mkdir -p ./deploy/cloud-config/")
	os.system( "mkdir -p ./deploy/iso-creator/")

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
	status = os.system('ssh -o "StrictHostKeyChecking no" -o "UserKnownHostsFile=/dev/null" -i %s -oBatchMode=yes %s@%s hostname > /dev/null' % (config["admin_username"], config["ssh_cert"], ipAddress))
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
				if len(nodename.split("."))<3:
					Nodes.append(nodename+domain)
				else:
					Nodes.append(nodename)
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
			hostname = utils.get_host_name(config["ssh_cert"], config["admin_username"], node[ipAddrMetaname])
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

def get_nodes_from_acs(tomatch=""):
	bFindNodes = True
	if not ("acsnodes" in config):
		machines = acs_tools.acs_get_machinesAndIPsFast()
		config["acsnodes"] = machines
	else:
		bFindNodes = not (tomatch == "" or tomatch == "master" or tomatch == "agent")
		machines = config["acsnodes"]
	Nodes = []
	if bFindNodes:
		masterNodes = []
		agentNodes = []
		allNodes = []
		for m in machines:
			match = re.match('k8s-'+tomatch+'.*', m)
			ip = machines[m]["publicip"]
			allNodes.append(ip)
			if not (match is None):
				Nodes.append(ip)
			match = re.match('k8s-master', m)
			if not (match is None):
				masterNodes.append(ip)
			match = re.match('k8s-agent', m)
			if not (match is None):
				agentNodes.append(ip)
		config["etcd_node"] = masterNodes
		config["kubernetes_master_node"] = masterNodes
		config["worker_node"] = agentNodes
		config["all_node"] = allNodes
	else:
		if tomatch == "":
			Nodes = config["all_node"]
		elif tomatch == "master":
			Nodes = config["kubernetes_master_node"]
		elif tomatch == "agent":
			Nodes = config["worker_node"]
		else:
			raise Exception("Wrong matching")
	return Nodes

def get_ETCD_master_nodes(clusterId):
	if config["isacs"]:
		return get_nodes_from_acs('master')
	if "etcd_node" in config:
		Nodes = config["etcd_node"]
		config["kubernetes_master_node"] = Nodes
		#print ("From etcd_node " + " ".join(map(str, Nodes)))
		return Nodes
	if "useclusterfile" not in config or not config["useclusterfile"]:
		#print "From cluster portal"
		return get_ETCD_master_nodes_from_cluster_portal(clusterId)
	else:
		#print "From master nodes from config"
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
			hostname = utils.get_host_name(config["ssh_cert"], config["admin_username"], node[ipAddrMetaname])
			Nodes.append(node[ipAddrMetaname])
			config["ipToHostname"][node[ipAddrMetaname]] = hostname
	config["worker_node"] = Nodes
	return Nodes

def get_worker_nodes_from_config(clusterId):
	Nodes = get_nodes_from_config("worker")
	config["worker_node"] = Nodes
	return Nodes

def get_worker_nodes(clusterId):
	if config["isacs"]:
		return get_nodes_from_acs('agent')
	if "worker_node" in config:
		return config["worker_node"]
	if "useclusterfile" not in config or not config["useclusterfile"]:
		return get_worker_nodes_from_cluster_report(clusterId)
	else:
		return get_worker_nodes_from_config(clusterId)

def limit_nodes(nodes):
	if limitnodes is not None:
		matchFunc = re.compile(limitnodes, re.IGNORECASE)
		usenodes = []
		for node in nodes:
			if ( matchFunc.search(node)):
				usenodes.append(node)
		nodes = usenodes
		if verbose:
			print "Operate on: %s" % nodes
		return usenodes
	else:
		return nodes

def get_nodes(clusterId):
	nodes = get_ETCD_master_nodes(clusterId) + get_worker_nodes(clusterId)
	nodes = limit_nodes(nodes)
	return nodes

def check_master_ETCD_status():
	masterNodes = []
	etcdNodes = []
	print "==============================================="
	print "Checking Available Nodes for Deployment..."
	if config["isacs"]:
		get_nodes_from_acs("")
	elif "clusterId" in config:
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
	config["apiserver_ssl_ip"] = "IP.1 = "+config["api-server-ip"]+"\nIP.2 = 127.0.0.1\n"+ "\n".join(["IP."+str(i+3)+" = "+ip for i,ip in enumerate(masterips)])

	for i,value in enumerate(config["etcd_node"]):
		if ippattern.match(value):
			etcdips.append(value)
		else:
			etcddns.append(value)

	config["etcd_ssl_dns"] = "\n".join(["DNS."+str(i+5)+" = "+dns for i,dns in enumerate(etcddns)])
	config["etcd_ssl_ip"] = "IP.1 = 127.0.0.1\n" + "\n".join(["IP."+str(i+2)+" = "+ip for i,ip in enumerate(etcdips)])

def gen_worker_certificates():

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
	if not config["isacs"]:
		config["discovery_url"] = utils.get_ETCD_discovery_URL(int(config["etcd_node_num"]))

	if "ssh_cert" not in config and os.path.isfile("./deploy/sshkey/id_rsa"):
		config["ssh_cert"] = expand_path("./deploy/sshkey/id_rsa")
		
	config["etcd_user"] = config["admin_username"]
	config["kubernetes_master_ssh_user"] = config["admin_username"]

	#config["api_servers"] = ",".join(["https://"+x for x in config["kubernetes_master_node"]])
	config["api_servers"] = "https://"+config["kubernetes_master_node"][0]+":"+str(config["k8sAPIport"])
	config["etcd_endpoints"] = ",".join(["https://"+x+":"+config["etcd3port1"] for x in config["etcd_node"]])

	config["webportal_node"] = None if len(get_node_lists_for_service("webportal"))==0 else get_node_lists_for_service("webportal")[0]


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
	config["etcd_user"] = config["admin_username"]
	config["kubernetes_master_ssh_user"] = config["admin_username"]
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

def get_cni_binary():
	os.system("mkdir -p ./deploy/bin")
	urllib.urlretrieve ("http://ccsdatarepo.westus.cloudapp.azure.com/data/containernetworking/cni-amd64-v0.5.2.tgz", "./deploy/bin/cni-amd64-v0.5.2.tgz")
	os.system("tar -zxvf ./deploy/bin/cni-amd64-v0.5.2.tgz -C ./deploy/bin")


def get_kubectl_binary(force = False):
	get_hyperkube_docker(force = force)
	#os.system("mkdir -p ./deploy/bin")
	urllib.urlretrieve ("http://ccsdatarepo.westus.cloudapp.azure.com/data/kube/kubelet/kubelet", "./deploy/bin/kubelet-old")
	#urllib.urlretrieve ("http://ccsdatarepo.westus.cloudapp.azure.com/data/kube/kubelet/kubectl", "./deploy/bin/kubectl")
	#os.system("chmod +x ./deploy/bin/*")
	get_cni_binary()

def get_hyperkube_docker(force = False) :
	os.system("mkdir -p ./deploy/bin")
	if force or not os.path.exists("./deploy/bin/hyperkube"):
		copy_from_docker_image(config['kubernetes_docker_image'], "/hyperkube", "./deploy/bin/hyperkube")
	if force or not os.path.exists("./deploy/bin/kubelet"):
		copy_from_docker_image(config['kubernetes_docker_image'], "/kubelet", "./deploy/bin/kubelet")
	if force or not os.path.exists("./deploy/bin/kubectl"):
		copy_from_docker_image(config['kubernetes_docker_image'], "/kubectl", "./deploy/bin/kubectl")
	# os.system("cp ./deploy/bin/hyperkube ./deploy/bin/kubelet")
	# os.system("cp ./deploy/bin/hyperkube ./deploy/bin/kubectl")

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
	deploycmd = """
		until curl -q http://127.0.0.1:8080/version/ ; do 
			sleep 5; 
			echo 'waiting for master...'; 
		done; 
		
		until sudo /opt/bin/kubectl apply -f /opt/addons/kube-addons/weave.yaml --validate=false ; do 
			sleep 5; 
			echo 'waiting for master...'; 
		done ;

		until sudo /opt/bin/kubectl apply -f /opt/addons/kube-addons/dashboard.yaml --validate=false ; do 
			sleep 5; 
			echo 'waiting for master...'; 
		done ;

		until sudo /opt/bin/kubectl apply -f /opt/addons/kube-addons/dns-addon.yml --validate=false ;  do 
			sleep 5; 
			echo 'waiting for master...'; 
		done ; 

		until sudo /opt/bin/kubectl apply -f /opt/addons/kube-addons/kube-proxy.json --validate=false ;  do 
			sleep 5; 
			echo 'waiting for master...'; 
		done ; 

		until sudo /opt/bin/kubectl apply -f /opt/addons/kube-addons/heapster.yaml --validate=false ; do 
			sleep 5; 
			echo 'waiting for master...'; 
		done ;		
	"""
	utils.SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_masters[0], deploycmd , False)


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
	utils.render_template_directory("./template/pxe", "./deploy/pxe",config, verbose=verbose )
	# cloud-config should be rendered already
	os.system("cp -r ./deploy/cloud-config/* ./deploy/pxe/tftp/usr/share/oem")
	
	dockername = push_one_docker("./deploy/pxe", config["dockerprefix"], config["dockertag"], "pxe-coreos", config )

	#tarname = "deploy/docker/dlworkspace-pxe-%s.tar" % config["cluster_name"]
	# os.system("docker save " + dockername + " > " + tarname )
	print ("A DL workspace docker is built at: "+ dockername)
	# print ("It is also saved as a tar file to: "+ tarname)
	
	#os.system("docker rmi dlworkspace-pxe:%s" % config["cluster_name"])

def config_ubuntu():
	# print config["ubuntuconfig"]
	ubuntuConfig = fetch_config( ["ubuntuconfig"] )
	# print ubuntuConfig
	useversion = fetch_dictionary( ubuntuConfig, [ "version" ] )
	specificConfig = fetch_dictionary( ubuntuConfig, [ useversion ] )
	for key, value in specificConfig.iteritems():
		config[key] = value
	config["ubuntuVersion"] = useversion

def create_PXE_ubuntu():
	config_ubuntu()
	os.system("rm -r ./deploy/pxe")
	os.system("mkdir -p ./deploy/docker")
	utils.render_template_directory("./template/pxe-ubuntu", "./deploy/pxe-ubuntu",config, verbose=verbose )

	dockername = push_one_docker("./deploy/pxe-ubuntu", config["dockerprefix"], config["dockertag"], "pxe-ubuntu", config )
	# tarname = "deploy/docker/pxe-ubuntu.tar" 
	
	# os.system("docker save " + dockername + " > " + tarname )
	print ("A DL workspace docker is built at: "+ dockername)
	# print ("It is also saved as a tar file to: "+ tarname)
	

def clean_worker_nodes():
	workerNodes = get_worker_nodes(config["clusterId"])
	for nodeIP in workerNodes:
		print "==============================================="
		print "cleaning worker node: %s ..."  % nodeIP		
		utils.SSH_exec_script(config["ssh_cert"],kubernetes_master_user, kubernetes_master, "./deploy/kubelet/%s" % config["workercleanupscript"])



def reset_worker_node(nodeIP):

	print "==============================================="
	print "updating worker node: %s ..."  % nodeIP

	worker_ssh_user = config["admin_username"]
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

	worker_ssh_user = config["admin_username"]
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
	
	#urllib.urlretrieve ("http://ccsdatarepo.westus.cloudapp.azure.com/data/kube/kubelet/kubelet", "./deploy/bin/kubelet")
	get_hyperkube_docker()

	workerNodes = get_worker_nodes(config["clusterId"])
	workerNodes = limit_nodes(workerNodes)
	for node in workerNodes:
		if in_list(node, nargs):
			update_worker_node(node)

	os.system("rm ./deploy/kubelet/options.env")
	os.system("rm ./deploy/kubelet/kubelet.service")
	os.system("rm ./deploy/kubelet/worker-kubeconfig.yaml")

	#if len(config["kubernetes_master_node"]) > 0:
		#utils.SSH_exec_cmd(config["ssh_cert"], config["admin_username"], config["kubernetes_master_node"][0], "sudo /opt/bin/kubelet get nodes")

def reset_worker_nodes():
	utils.render_template_directory("./template/kubelet", "./deploy/kubelet",config)
	workerNodes = get_worker_nodes(config["clusterId"])
	workerNodes = limit_nodes(workerNodes)
	for node in workerNodes:
		reset_worker_node(node)



def create_MYSQL_for_WebUI():
	#todo: create a mysql database, and set "mysql-hostname", "mysql-username", "mysql-password", "mysql-database"
	pass

def deploy_restful_API_on_node(ipAddress):
	masterIP = ipAddress
	dockername = "%s/dlws-restfulapi" %  (config["dockerregistry"])

	# if user didn't give storage server information, use CCS public storage in default. 
	if "nfs-server" not in config:
		config["nfs-server"] = "10.196.44.241:/mnt/data"

	if not os.path.exists("./deploy/RestfulAPI"):
		os.system("mkdir -p ./deploy/RestfulAPI")
	
	utils.render_template("./template/RestfulAPI/config.yaml","./deploy/RestfulAPI/config.yaml",config)
	utils.render_template("./template/master/restapi-kubeconfig.yaml","./deploy/master/restapi-kubeconfig.yaml",config)

	utils.sudo_scp(config["ssh_cert"],"./deploy/RestfulAPI/config.yaml","/etc/RestfulAPI/config.yaml", config["admin_username"], masterIP )
	utils.sudo_scp(config["ssh_cert"],"./deploy/master/restapi-kubeconfig.yaml","/etc/kubernetes/restapi-kubeconfig.yaml", config["admin_username"], masterIP )

	if config["isacs"]:
		# copy needed keys
		utils.SSH_exec_cmd(config["ssh_cert"], config["admin_username"], masterIP, "sudo mkdir -p /etc/kubernetes/ssl")
		utils.SSH_exec_cmd(config["ssh_cert"], config["admin_username"], masterIP, "sudo cp /etc/kubernetes/certs/client.crt /etc/kubernetes/ssl/apiserver.pem")
		utils.SSH_exec_cmd(config["ssh_cert"], config["admin_username"], masterIP, "sudo cp /etc/kubernetes/certs/client.key /etc/kubernetes/ssl/apiserver-key.pem")
		utils.SSH_exec_cmd(config["ssh_cert"], config["admin_username"], masterIP, "sudo cp /etc/kubernetes/certs/ca.crt /etc/kubernetes/ssl/ca.pem")
		# overwrite ~/.kube/config (to be mounted from /etc/kubernetes/restapi-kubeconfig.yaml)
		utils.SSH_exec_cmd(config["ssh_cert"], config["admin_username"], masterIP, "sudo cp /home/%s/.kube/config /etc/kubernetes/restapi-kubeconfig.yaml" % config["admin_username"])

	# utils.SSH_exec_cmd(config["ssh_cert"], config["admin_username"], masterIP, "sudo mkdir -p /dlws-data && sudo mount %s /dlws-data ; docker rm -f restfulapi; docker rm -f jobScheduler ; docker pull %s ; docker run -d -p %s:80 --restart always -v /etc/RestfulAPI:/RestfulAPI --name restfulapi %s ; docker run -d -v /dlws-data:/dlws-data -v /etc/RestfulAPI:/RestfulAPI -v /etc/kubernetes/restapi-kubeconfig.yaml:/root/.kube/config -v /etc/kubernetes/ssl:/etc/kubernetes/ssl --restart always --name jobScheduler %s /runScheduler.sh ;" % (config["nfs-server"], dockername,config["restfulapiport"],dockername,dockername))

	print "==============================================="
	print "restful api is running at: http://%s:%s" % (masterIP,config["restfulapiport"])
	config["restapi"] = "http://%s:%s" %  (masterIP,config["restfulapiport"])

def deploy_webUI_on_node(ipAddress):

	sshUser = config["admin_username"]
	webUIIP = ipAddress
	dockername = "%s/dlws-webui" %  (config["dockerregistry"])

	if "restapi" not in config:
		print "!!!! Cannot deploy Web UI - RestfulAPI is not deployed"
		return

	if not os.path.exists("./deploy/WebUI"):
		os.system("mkdir -p ./deploy/WebUI")

	utils.render_template("./template/WebUI/userconfig.json","./deploy/WebUI/userconfig.json", config)
	os.system("cp --verbose ./deploy/WebUI/userconfig.json ../WebUI/dotnet/WebPortal/") # used for debugging, when deploy, it will be overwritten by mount from host, contains secret
	utils.render_template("./template/WebUI/configAuth.json","./deploy/WebUI/configAuth.json", config)
	os.system("cp --verbose ./deploy/WebUI/configAuth.json ../WebUI/dotnet/WebPortal/")
	
	# write into host, mounted into container
	utils.sudo_scp(config["ssh_cert"],"./deploy/WebUI/userconfig.json","/etc/WebUI/userconfig.json", sshUser, webUIIP )


	utils.render_template("./template/WebUI/Master-Templates.json", "./deploy/WebUI/Master-Templates.json", config)
	#os.system("cp --verbose ./template/WebUI/Master-Templates.json ./deploy/WebUI/Master-Templates.json")
	os.system("cp --verbose ./deploy/WebUI/Master-Templates.json ../WebUI/dotnet/WebPortal/Master-Templates.json")
	utils.sudo_scp(config["ssh_cert"],"./deploy/WebUI/Master-Templates.json","/etc/WebUI/Master-Templates.json", sshUser, webUIIP )



	utils.render_template_directory("./template/RestfulAPI", "./deploy/RestfulAPI",config)
	utils.sudo_scp(config["ssh_cert"],"./deploy/RestfulAPI/config.yaml","/etc/RestfulAPI/config.yaml", sshUser, webUIIP )


	# utils.SSH_exec_cmd(config["ssh_cert"], sshUser, webUIIP, "docker pull %s ; docker rm -f webui ; docker run -d -p %s:80 -v /etc/WebUI:/WebUI --restart always --name webui %s ;" % (dockername,str(config["webuiport"]),dockername))

	print "==============================================="
	print "Web UI is running at: http://%s:%s" % (webUIIP,str(config["webuiport"]))

# Install ssh key remotely
def install_ssh_key(key_files):
	all_nodes = get_nodes(config["clusterId"])

	rootpasswdfile = "./deploy/sshkey/rootpasswd"
	rootuserfile = "./deploy/sshkey/rootuser"


	with open(rootpasswdfile, "r") as f:
		rootpasswd = f.read().strip()
		f.close()

	rootuser = config["admin_username"]
	if os.path.isfile(rootuserfile):
		with open(rootuserfile, "r") as f:
			rootuser = f.read().strip()
			f.close()


	for node in all_nodes:
		if len(key_files)>0:
			for key_file in key_files:
				print "Install key %s on %s" % (key_file, node)
				os.system("""sshpass -f %s ssh-copy-id -o "StrictHostKeyChecking=no" -o "UserKnownHostsFile=/dev/null" -i %s %s@%s""" %(rootpasswdfile, key_file, rootuser, node))
		else:
			print "Install key %s on %s" % ("./deploy/sshkey/id_rsa.pub", node)
			os.system("""sshpass -f %s ssh-copy-id -o "StrictHostKeyChecking=no" -o "UserKnownHostsFile=/dev/null" -i ./deploy/sshkey/id_rsa.pub %s@%s""" %(rootpasswdfile, rootuser, node))


	if rootuser != config["admin_username"]:
	 	for node in all_nodes:
	 		os.system('sshpass -f %s ssh  -o "StrictHostKeyChecking=no" -o "UserKnownHostsFile=/dev/null" %s@%s "sudo useradd -p %s -d /home/%s -m -s /bin/bash %s"' % (rootpasswdfile,rootuser, node, rootpasswd,config["admin_username"],config["admin_username"]))
	 		os.system('sshpass -f %s ssh  -o "StrictHostKeyChecking=no" -o "UserKnownHostsFile=/dev/null" %s@%s "sudo usermod -aG sudo %s"' % (rootpasswdfile,rootuser, node,config["admin_username"]))
	 		os.system('sshpass -f %s ssh  -o "StrictHostKeyChecking=no" -o "UserKnownHostsFile=/dev/null" %s@%s "sudo mkdir -p /home/%s/.ssh"' % (rootpasswdfile,rootuser, node, config["admin_username"]))


			if len(key_files)>0:
				for key_file in key_files:
					print "Install key %s on %s" % (key_file, node)
					with open(key_file, "r") as f:
						publicKey = f.read().strip()
						f.close()		
	 				os.system('sshpass -f %s ssh  -o "StrictHostKeyChecking=no" -o "UserKnownHostsFile=/dev/null" %s@%s "echo %s | sudo tee /home/%s/.ssh/authorized_keys"' % (rootpasswdfile,rootuser, node,publicKey,config["admin_username"]))

			else:
				print "Install key %s on %s" % ("./deploy/sshkey/id_rsa.pub", node)
				with open("./deploy/sshkey/id_rsa.pub", "r") as f:
					publicKey = f.read().strip()
					f.close()		
 				os.system('sshpass -f %s ssh  -o "StrictHostKeyChecking=no" -o "UserKnownHostsFile=/dev/null" %s@%s "echo %s | sudo tee /home/%s/.ssh/authorized_keys"' % (rootpasswdfile,rootuser, node,publicKey,config["admin_username"]))

	 		os.system('sshpass -f %s ssh  -o "StrictHostKeyChecking=no" -o "UserKnownHostsFile=/dev/null" %s@%s "sudo chown %s:%s -R /home/%s"' % (rootpasswdfile,rootuser, node,config["admin_username"],config["admin_username"],config["admin_username"]))
	 		os.system('sshpass -f %s ssh  -o "StrictHostKeyChecking=no" -o "UserKnownHostsFile=/dev/null" %s@%s "sudo chmod 400 /home/%s/.ssh/authorized_keys"' % (rootpasswdfile,rootuser, node,config["admin_username"]))
	 		os.system("""sshpass -f %s ssh  -o "StrictHostKeyChecking=no" -o "UserKnownHostsFile=/dev/null" %s@%s "echo '%s ALL=(ALL) NOPASSWD: ALL' | sudo tee -a /etc/sudoers.d/%s " """ % (rootpasswdfile,rootuser, node,config["admin_username"],config["admin_username"]))



def pick_server( nodelists, curNode ):
	if curNode is None or not (curNode in nodelists):
		return random.choice(nodelists)
	else:
		return curNode

# simple utils
def exec_rmt_cmd(node, cmd):
	utils.SSH_exec_cmd(config["ssh_cert"], config["admin_username"], node, cmd)

def rmt_cp(node, source, target):
	utils.sudo_scp(config["ssh_cert"], source, target, config["admin_username"], node)

# copy list of files to a node
def copy_list_of_files(listOfFiles, node):	
	with open(listOfFiles, "r") as f:
		copy_files = [s.split(",") for s in f.readlines() if len(s.split(",")) == 2]
	for (source, target) in copy_files:
		if (os.path.isfile(source.strip()) or os.path.exists(source.strip())):
			rmt_cp(node, source, target)

def copy_list_of_files_to_nodes(listOfFiles, nodes):
	with open(listOfFiles, "r") as f:
		copy_files = [s.split(",") for s in f.readlines() if len(s.split(",")) == 2]
	for node in nodes:
		for (source, target) in copy_files:
			if (os.path.isfile(source.strip()) or os.path.exists(source.strip())):
				rmt_cp(node, source, target)		

# run scripts
def run_script_on_node(script, node):
	utils.SSH_exec_script(config["ssh_cert"], config["admin_username"], node, script)

def run_script_on_nodes(script, nodes):
	for node in nodes:
		utils.SSH_exec_script(config["ssh_cert"], config["admin_username"], node, script)

# deployment
def deploy_on_nodes(prescript, listOfFiles, postscript, nodes):
	run_script_on_nodes(prescript, nodes)
	copy_list_of_files_to_nodes(listOfFiles, nodes)
	run_script_on_nodes(postscript, nodes)

# addons
def kube_master0_wait():
	get_nodes_from_acs()
	node = config["kubernetes_master_node"][0]
	exec_rmt_cmd(node, "until curl -q http://127.0.0.1:8080/version/ ; do sleep 5; echo 'waiting for master...'; done")
	return node

def kube_deploy_addons():
	node = kube_master0_wait()
	for addon in config["kube_addons"]:
		exec_rmt_cmd(node, "sudo kubectl create -f "+addon)

# config changes		
def kube_dpeloy_configchanges():
	node = kube_master0_wait()
	for configChange in config["kube_configchanges"]:
		exec_rmt_cmd(node, "sudo kubectl apply -f "+configChange)

def acs_deploy_addons():
	kube_dpeloy_configchanges()
	kube_deploy_addons()

def acs_label_webui():
	for n in config["kubernetes_master_node"]:
		nodeName = config["nodenames_from_ip"][n]
		if verbose:
			print "Label node: "+nodeName
		label_webUI(nodeName)

def acs_untaint_nodes():
	for n in config["kubernetes_master_node"]:
		nodeName = config["nodenames_from_ip"][n]
		if verbose:
			print "Untaint node: "+nodeName
		run_kubectl(["taint nodes {0} node-role.kubernetes.io/master-".format(nodeName)])

# other config post deploy -- ACS cluster is complete
# Run prescript, copyfiles, postscript
def acs_post_deploy():
	# Attach DNS name to nodes
	acs_attach_dns_name()

	# Label nodes
	ip = get_nodes_from_acs("")
	acs_label_webui()
	kubernetes_label_nodes("active", [], args.yes)

	# Untaint the master nodes
	acs_untaint_nodes()

	# Copy files, etc.
	get_nodes_from_acs()
	gen_configs()
	utils.render_template_directory("./template/kubelet", "./deploy/kubelet", config)
	write_nodelist_yaml()
	# get CNI binary
	get_cni_binary()
	# deploy
	#print config["master_predeploy"]
	#print config["master_filesdeploy"]
	#print config["master_postdeploy"]
	deploy_on_nodes(config["master_predeploy"], config["master_filesdeploy"], config["master_postdeploy"], 
		            config["kubernetes_master_node"])
	deploy_on_nodes(config["worker_predeploy"], config["worker_filesdeploy"], config["worker_postdeploy"],
	                config["worker_node"])

def acs_attach_dns_name():
	get_nodes_from_acs()
	firstMasterNode = config["kubernetes_master_node"][0]
	acs_tools.acs_attach_dns_to_node(firstMasterNode, config["master_dns_name"])
	for i in range(len(config["kubernetes_master_node"])):
		if (i != 0):
			acs_tools.acs_attach_dns_to_node(config["kubernetes_master_node"][i])
	for node in config["worker_node"]:
		acs_tools.acs_attach_dns_to_node(node)

def acs_install_gpu():
	nodes = get_worker_nodes(config["clusterId"])
	for node in nodes:
		#exec_rmt_cmd(node, "curl -L -sf https://raw.githubusercontent.com/ritazh/acs-k8s-gpu/master/install-nvidia-driver.sh | sudo sh")
		run_script(node, ["./scripts/prepare_acs.sh"], True)

def acs_get_jobendpt(jobId):
	get_nodes_from_acs("")
	addr = k8sUtils.GetServiceAddress(jobId)
	#print addr
	#print config["acsnodes"]
	ip = config["acsnodes"][addr[0]['hostName']]['publicip']
	port = addr[0]['hostPort']
	ret = "http://%s:%s" % (ip, port)
	print ret

def get_mount_fileshares(curNode = None):
	allmountpoints = { }
	fstab = ""
	bHasDefaultMountPoints = False
	physicalmountpoint = config["physical-mount-path"] 
	storagemountpoint = config["storage-mount-path"]
	mountshares = {}
	for k,v in config["mountpoints"].iteritems():
		if "type" in v:
			if ("mountpoints" in v):
				if isinstance( v["mountpoints"], basestring):
					if len(v["mountpoints"])>0:
						mountpoints = [v["mountpoints"]] 
					else:
						mountpoints = []
				elif isinstance( v["mountpoints"], list):
					mountpoints = v["mountpoints"]
			else:
				mountpoints = []
			
			if len(mountpoints)==0:
				if bHasDefaultMountPoints:
					errorMsg = "there are more than one default mount points in configuration. "
					print "!!!Configuration Error!!! " + errorMsg
					raise ValueError(erorMsg)
				else:
					bHasDefaultMountPoints = True
					mountpoints = config["default-storage-folders"]
			
			mountsharename = v["mountsharename"] if "mountsharename" in v else v["filesharename"]
			if mountsharename in mountshares:
				errorMsg = "There are multiple file share to be mounted at %s" % mountsharename
				print "!!!Configuration Error!!! " + errorMsg
				raise ValueError(erorMsg) 
			
			if os.path.isabs(mountsharename):
				curphysicalmountpoint = mountsharename
			else:
				curphysicalmountpoint = os.path.join( physicalmountpoint, mountsharename )
			v["curphysicalmountpoint"] = curphysicalmountpoint
			bMount = False
			errorMsg = None
			if v["type"] == "azurefileshare":
				if "accountname" in v and "filesharename" in v and "accesskey" in v:
					allmountpoints[k] = copy.deepcopy( v )
					bMount = True
					allmountpoints[k]["url"] = "//" + allmountpoints[k]["accountname"] + ".file.core.windows.net/"+allmountpoints[k]["filesharename"]
					options = fetch_config(["mountconfig", "azurefileshare", "options"]) % (v["accountname"], v["accesskey"])
					allmountpoints[k]["options"] = options
					fstab += "%s %s cifs %s\n" % (allmountpoints[k]["url"], curphysicalmountpoint, options )
				else:
					errorMsg = "Error: fileshare %s, type %s, miss one of the parameter accountname, filesharename, mountpoints, accesskey" %(k, v["type"])
			elif v["type"] == "glusterfs":
				if "filesharename" in v:
					allmountpoints[k] = copy.deepcopy( v )
					bMount = True
					glusterfs_nodes = get_node_lists_for_service("glusterfs")
					allmountpoints[k]["node"] = pick_server( glusterfs_nodes, curNode )
					options = fetch_config(["mountconfig", "glusterfs", "options"])
					allmountpoints[k]["options"] = options
					fstab += "%s:/%s %s glusterfs %s 0 0\n" % (allmountpoints[k]["node"], v["filesharename"], curphysicalmountpoint, options)
				else:
					errorMsg = "glusterfs fileshare %s, there is no filesharename parameter" % (k)
			elif v["type"] == "nfs" and "server" in v:
				if "filesharename" in v and "server" in v:
					allmountpoints[k] = copy.deepcopy( v )
					bMount = True
					options = fetch_config(["mountconfig", "nfs", "options"])
					allmountpoints[k]["options"] = options
					fstab += "%s:/%s %s /nfsmnt nfs %s\n" % (v["server"], v["filesharename"], curphysicalmountpoint, options)
				else:
					errorMsg = "nfs fileshare %s, there is no filesharename or server parameter" % (k)
			elif v["type"] == "hdfs":
				allmountpoints[k] = copy.deepcopy( v )
				if "server" not in v or v["server"] =="":
					hdfsconfig = generate_hdfs_config( config, None)
					allmountpoints[k]["server"] = []
					for ( k1,v1) in hdfsconfig["namenode"].iteritems():
						if k1.find("namenode")>=0:
							allmountpoints[k]["server"].append(v1)
				bMount = True
				options = fetch_config(["mountconfig", "hdfs", "options"])
				allmountpoints[k]["options"] = options
				fstaboptions = fetch_config(["mountconfig", "hdfs", "fstaboptions"])
				fstab += "hadoop-fuse-dfs#hdfs://%s %s fuse %s\n" % (allmountpoints[k]["server"][0], curphysicalmountpoint, fstaboptions)
			elif (v["type"] == "local" or v["type"] == "localHDD") and "device" in v:
				allmountpoints[k] = copy.deepcopy( v )
				bMount = True
				fstab += "%s %s ext4 defaults 0 0\n" % (v["device"], curphysicalmountpoint)				
			elif v["type"] == "emptyDir":
				allmountpoints[k] = copy.deepcopy( v )
				bMount = True
			else:
				errorMsg = "Error: Unknown or missing critical parameter in fileshare %s with type %s" %( k, v["type"])
			if not (errorMsg is None):
				print errorMsg
				raise ValueError(errorMsg)
			if bMount:
				allmountpoints[k]["mountpoints"] = mountpoints
		else:
			print "Error: fileshare %s with no type" %( k )
	return allmountpoints, fstab

def insert_fstab_section( node, secname, content):
	fstabcontent = utils.SSH_exec_cmd_with_output(config["ssh_cert"], config["admin_username"], node, "cat /etc/fstab")
	fstabmask =    "##############%sMOUNT#################\n" % secname
	fstabmaskend = "#############%sMOUNTEND###############\n" % secname
	if not content.endswith("\n"):
		content += "\n"
	fstab = fstabmask + content + fstabmaskend
	usefstab = fstab
	if fstabcontent.find("No such file or directory")==-1:
		indexst = fstabcontent.find(fstabmask) 
		indexend = fstabcontent.find(fstabmaskend)
		if indexst > 1:
			if indexend < 0:
				usefstab = fstabcontent[:indexst] + fstab 
			else:
				usefstab = fstabcontent[:indexst] + fstab + fstabcontent[indexend+len(fstabmaskend):]
		else:
			if fstabcontent.endswith("\n"):
				usefstab = 	fstabcontent + fstab 
			else:
				usefstab = fstabcontent + "\n" + fstab 
	if verbose:
		print "----------- Resultant /etc/fstab --------------------"
		print usefstab
	os.system("mkdir -p ./deploy/etc")
	with open("./deploy/etc/fstab","w") as f:
		f.write(usefstab)
		f.close()
	utils.sudo_scp( config["ssh_cert"], "./deploy/etc/fstab", "/etc/fstab", config["admin_username"], node)

def remove_fstab_section( node, secname):
	fstabmask =    "##############%sMOUNT#################\n" % secname
	fstabmaskend = "#############%sMOUNTEND###############\n" % secname
	fstabcontent = utils.SSH_exec_cmd_with_output(config["ssh_cert"], config["admin_username"], node, "cat /etc/fstab")
	bCopyFStab = False
	if fstabcontent.find("No such file or directory")==-1:
		indexst = fstabcontent.find(fstabmask) 
		indexend = fstabcontent.find(fstabmaskend)
		if indexst > 1:
			bCopyFStab = True
			if indexend < 0:
				usefstab = fstabcontent[:indexst] 
			else:
				usefstab = fstabcontent[:indexst] + fstabcontent[indexend+len(fstabmaskend):]
		if bCopyFStab:
			if verbose:
				print "----------- Resultant /etc/fstab --------------------"
				print usefstab
			os.system("mkdir -p ./deploy/etc")
			with open("./deploy/etc/fstab","w") as f:
				f.write(usefstab)
				f.close()
			utils.sudo_scp( config["ssh_cert"], "./deploy/etc/fstab", "/etc/fstab", config["admin_username"], node)

def fileshare_install():
	all_nodes = get_nodes(config["clusterId"])
	nodes = all_nodes
	for node in nodes:
		allmountpoints, fstab = get_mount_fileshares(node)
		remotecmd = ""
		if (config["isacs"]):
			# when started, ACS machines don't have PIP which is needed to install pyyaml
			# pyyaml is needed by auto_share.py to load mounting.yaml
			remotecmd += "sudo apt-get -y install python-pip; "
			remotecmd += "sudo apt-get -y install python-yaml; "
			remotecmd += "pip install pyyaml; "
		filesharetype = {}
		# In service, the mount preparation install relevant software on remote machine. 
		for k,v in allmountpoints.iteritems():
			if "curphysicalmountpoint" in v:
				physicalmountpoint = v["curphysicalmountpoint"] 
				if v["type"] == "azurefileshare":
					if not ("azurefileshare" in filesharetype):
						filesharetype["azurefileshare"] = True
						remotecmd += "sudo apt-get -y install cifs-utils attr; "
				elif v["type"] == "glusterfs":
					if not ("glusterfs" in filesharetype):
						filesharetype["glusterfs"] = True
						remotecmd += "sudo apt-get install -y glusterfs-client attr; "
				elif v["type"] == "nfs":
					if not ("nfs" in filesharetype):
						filesharetype["nfs"] = True
						remotecmd += "sudo apt-get install -y nfs-common; "
						# Ubuntu has issue of rpc.statd not started automatically 
						# https://bugs.launchpad.net/ubuntu/+source/nfs-utils/+bug/1624715
						remotecmd += "sudo cp /lib/systemd/system/rpc-statd.service /etc/systemd/system/; "
						remotecmd += "sudo systemctl add-wants rpc-statd.service nfs-client.target; "
						remotecmd += "sudo systemctl reenable rpc-statd.service; "
						remotecmd += "sudo systemctl restart rpc-statd.service; "
				elif v["type"] == "hdfs":
					if not ("hdfs" in filesharetype):
						filesharetype["hdfs"] = True
						remotecmd += "wget http://archive.cloudera.com/cdh5/one-click-install/trusty/amd64/cdh5-repository_1.0_all.deb; "
						remotecmd += "sudo dpkg -i cdh5-repository_1.0_all.deb; "
						remotecmd += "sudo rm cdh5-repository_1.0_all.deb; "
						remotecmd += "sudo apt-get update; "
						remotecmd += "sudo apt-get install -y default-jre; "
						remotecmd += "sudo apt-get install -y --allow-unauthenticated hadoop-hdfs-fuse; "
		if len(remotecmd)>0:
			utils.SSH_exec_cmd(config["ssh_cert"], config["admin_username"], node, remotecmd)

def mount_fileshares_by_service(perform_mount=True):
	all_nodes = get_nodes(config["clusterId"])
	if perform_mount:
		nodes = all_nodes
		for node in nodes:
			allmountpoints, fstab = get_mount_fileshares(node)
			remotecmd = ""
			remotecmd += "sudo mkdir -p %s; " % config["storage-mount-path"]
			remotecmd += "sudo mkdir -p %s; " % config["physical-mount-path"]
			mountconfig = { }
			mountconfig["mountpoints"] = allmountpoints
			mountconfig["storage-mount-path"] = config["storage-mount-path"]
			mountconfig["physical-mount-path"] = config["physical-mount-path"]
			for k,v in allmountpoints.iteritems():
				if "curphysicalmountpoint" in v:
					remotecmd += "sudo mkdir -p %s; " % v["curphysicalmountpoint"]
			utils.SSH_exec_cmd( config["ssh_cert"], config["admin_username"], node, "sudo mkdir -p %s; " % config["folder_auto_share"] )
			utils.render_template_directory("./template/storage/auto_share", "./deploy/storage/auto_share", config)
			with open("./deploy/storage/auto_share/mounting.yaml",'w') as datafile:
				yaml.dump(mountconfig, datafile, default_flow_style=False)	
			remotecmd += "sudo systemctl stop auto_share.timer; "
			# remotecmd += "sudo systemctl stop auto_share.service; "
			if len(remotecmd)>0:
				utils.SSH_exec_cmd(config["ssh_cert"], config["admin_username"], node, remotecmd)
			remotecmd = ""			
			utils.sudo_scp( config["ssh_cert"], "./deploy/storage/auto_share/auto_share.timer","/etc/systemd/system/auto_share.timer", config["admin_username"], node )
			utils.sudo_scp( config["ssh_cert"], "./deploy/storage/auto_share/auto_share.target","/etc/systemd/system/auto_share.target", config["admin_username"], node )
			utils.sudo_scp( config["ssh_cert"], "./deploy/storage/auto_share/auto_share.service","/etc/systemd/system/auto_share.service", config["admin_username"], node )
			utils.sudo_scp( config["ssh_cert"], "./deploy/storage/auto_share/logging.yaml",os.path.join(config["folder_auto_share"], "logging.yaml"), config["admin_username"], node )
			utils.sudo_scp( config["ssh_cert"], "./deploy/storage/auto_share/auto_share.py",os.path.join(config["folder_auto_share"], "auto_share.py"), config["admin_username"], node )
			utils.sudo_scp( config["ssh_cert"], "./template/storage/auto_share/glusterfs.mount",os.path.join(config["folder_auto_share"], "glusterfs.mount"), config["admin_username"], node )
			utils.sudo_scp( config["ssh_cert"], "./deploy/storage/auto_share/mounting.yaml",os.path.join(config["folder_auto_share"], "mounting.yaml"), config["admin_username"], node )
			remotecmd += "sudo chmod +x %s; " % os.path.join(config["folder_auto_share"], "auto_share.py")
			remotecmd += "sudo " + os.path.join(config["folder_auto_share"], "auto_share.py") + "; " # run it once now
			remotecmd += "sudo systemctl daemon-reload; "
			remotecmd += "sudo rm /opt/auto_share/lock; "
			remotecmd += "sudo systemctl enable auto_share.timer; "
			remotecmd += "sudo systemctl restart auto_share.timer; "
			# remotecmd += "sudo systemctl stop auto_share.service; "
			if len(remotecmd)>0:
				utils.SSH_exec_cmd(config["ssh_cert"], config["admin_username"], node, remotecmd)
			# We no longer recommend to insert fstabl into /etc/fstab file, instead, 
			# we recommend to use service to start auto mount if needed
			# insert_fstab_section( node, "DLWS", fstab )
	for k, v in allmountpoints.iteritems():
		allmountpoints[k].pop("accesskey", None)
	# print mountpoints
	return allmountpoints

def unmount_fileshares_by_service(clean=False):
	all_nodes = get_nodes(config["clusterId"])
	allmountpoints, fstab = get_mount_fileshares()
	# print fstab
	if True:
		nodes = all_nodes
		for node in nodes:
			remotecmd = ""
			remotecmd += "sudo systemctl disable auto_share.timer; "
			remotecmd += "sudo systemctl stop auto_share.timer; "
			for k,v in allmountpoints.iteritems():
				if "curphysicalmountpoint" in v:
					output = utils.SSH_exec_cmd_with_output(config["ssh_cert"], config["admin_username"], node, "sudo mount | grep %s" % v["curphysicalmountpoint"])
					umounts = []
					for line in output.splitlines():
						words = line.split()
						if len(words)>3 and words[1]=="on":
							umounts.append( words[2] )
					umounts.sort()
					for um in umounts:
						remotecmd += "sudo umount %s; " % um
			if clean:
				for k,v in allmountpoints.iteritems():
					if "curphysicalmountpoint" in v:
						remotecmd += "sudo rm -rf %s; " % v["curphysicalmountpoint"]
			if len(remotecmd)>0:
				utils.SSH_exec_cmd(config["ssh_cert"], config["admin_username"], node, remotecmd)	

def del_fileshare_links():
	all_nodes = get_nodes(config["clusterId"])
	for node in all_nodes:
		remotecmd = "sudo rm -r %s; " % config["storage-mount-path"]	
		remotecmd = "sudo mkdir -p %s; " % config["storage-mount-path"]
		exec_rmt_cmd(node, remotecmd)
			 
def link_fileshares(allmountpoints, bForce=False):
	all_nodes = get_nodes(config["clusterId"])
	# print fstab
	if True:
		nodes = all_nodes
		firstdirs = {}
		for k,v in allmountpoints.iteritems():
			if "mountpoints" in v:
				firstdirs[v["curphysicalmountpoint"]] = True
		for node in nodes:
			remotecmd = ""
			if bForce:
				for k,v in allmountpoints.iteritems():
					if "mountpoints" in v and v["type"]!="emptyDir":
						for basename in v["mountpoints"]:
							dirname = os.path.join(v["curphysicalmountpoint"], basename )
							remotecmd += "sudo rm %s; " % dirname
				remotecmd += "sudo rm -r %s; " % config["storage-mount-path"]
				remotecmd += "sudo mkdir -p %s; " % config["storage-mount-path"]
				
			output = utils.SSH_exec_cmd_with_output(config["ssh_cert"], config["admin_username"], node, "sudo mount" )
			for k,v in allmountpoints.iteritems():
				if "mountpoints" in v and v["type"]!="emptyDir":
					if output.find(v["curphysicalmountpoint"])<0:
						print "!!!Warning!!! %s has not been mounted at %s " % (k, v["curphysicalmountpoint"])
					else:
						if ( firstdirs[v["curphysicalmountpoint"]]):
							firstdirs[v["curphysicalmountpoint"]] = True
							for basename in v["mountpoints"]:
								dirname = os.path.join(v["curphysicalmountpoint"], basename )
								remotecmd += "sudo mkdir -p %s; " % dirname
								remotecmd += "sudo chmod ugo+rwx %s; " %dirname
					for basename in v["mountpoints"]:
						dirname = os.path.join(v["curphysicalmountpoint"], basename )
						linkdir = os.path.join(config["storage-mount-path"], basename )
						remotecmd += "if [ ! -e %s ]; then sudo ln -s %s %s; fi; " % (linkdir, dirname, linkdir)
			# following node need not make the directory
			if len(remotecmd)>0:
				utils.SSH_exec_cmd(config["ssh_cert"], config["admin_username"], node, remotecmd)
	()

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
	output = utils.SSH_exec_cmd_with_output(config["ssh_cert"], config["admin_username"], node, "sudo parted -l -s", True)
	if verbose:
		print node
		print output
	# print output
	drives = prog.search( output )
	# print(drives)
	drivesInfo = prog.split( output )
	# print len(drivesInfo)
	ndrives = len(drivesInfo)/2
	#for i in range(len(drivesInfo)):
	#	print "Segment %d: %s" %(i, drivesInfo[i])

	partinfo = {}
	blockdevice = 1
	for i in range(ndrives):
		deviceinfo = {}
		pos_semi = drivesInfo[i*2+2].find(":")
		if pos_semi < 0:
			continue;
		pos_model = drivesInfo[i*2].rfind("Model:")
		modelName = drivesInfo[i*2][pos_model+7:].splitlines()[0] if pos_model >=0 else "None"
		drivename = drivesInfo[i*2+1] + drivesInfo[i*2+2][:pos_semi]
		driveString = drivesInfo[i*2+2][pos_semi+1:]
		#print "Drive Name: " + drivename
		#print "Drive String: " + driveString
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
			deviceinfo["modelName"] = modelName
			deviceinfo["name"] = drivename
			deviceinfo["capacity"] = capacity
			deviceinfo["parted"] = parted
			partinfo[blockdevice] = deviceinfo
			blockdevice += 1
	return partinfo 
	
# Get Partition of all nodes in a cluster
def get_partitions(nodes, regexp):
	while regexp[-1].isdigit():
		regexp = regexp[:-1]
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
			print deviceinfo["name"] + ", "+ deviceinfo["modelName"] + ", Capacity: " + str(deviceinfo["capacity"]) + "GB" + ", Partition: " + str(deviceinfo["parted"])
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
			if npart > 0:
				cmd += "sudo parted -s " + deviceinfo["name"] + " mklabel gpt; "
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
			utils.SSH_exec_cmd(config["ssh_cert"], config["admin_username"], node, cmd)
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
	utils.SSH_exec_cmd_with_directory( config["ssh_cert"], config["admin_username"], masternodes[0], "deploy/storage/glusterFS", remotecmd, dstdir = rundir )

# Deploy glusterFS on a cluster
def remove_glusterFS_volumes_heketi( masternodes, ipToHostname, nodesinfo, glusterFSargs, nodes ):
	exit()
	start_glusterFS_heketi( masternodes, ipToHostname, nodesinfo, glusterFSargs, flag = "-g --yes --abort")
	for node in nodes:
		glusterFS_copy()
		rundir = "/tmp/glusterFSAdmin"
		remotecmd = "sudo python RemoveLVM.py "
		utils.SSH_exec_cmd_with_directory( config["ssh_cert"], config["admin_username"], node, "deploy/storage/glusterFS", remotecmd, dstdir = rundir )
		
def regmatch_glusterFS( glusterFSargs ):
	if isinstance( glusterFSargs, (int,long) ):
		regexp = "/dev/[s|h]d[^a]"+str(glusterFSargs)
	else:
		regexp = glusterFSargs
	#print regexp
	regmatch = re.compile(regexp)
	return regmatch

def find_matched_volume( alldeviceinfo, regmatch ):	
	deviceList = {}
	for bdevice in alldeviceinfo:
		deviceinfo = alldeviceinfo[bdevice] 
		for part in deviceinfo["parted"]:
			bdevicename = deviceinfo["name"] + str(part)
			# print bdevicename
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
	os.system("mkdir -p %s" %os.path.dirname(config_file))
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

def format_mount_partition_volume( nodes, deviceSelect, format=True ):
	nodesinfo = get_partitions(nodes, deviceSelect )
	#if verbose: 
	#	print nodesinfo
	reg = re.compile( deviceSelect )
	for node in nodesinfo:
		alldeviceinfo = nodesinfo[node]
		volumes = find_matched_volume( alldeviceinfo, reg )
		if verbose:
			print "................. Node %s ................." % node
			print "Node = %s, volume = %s " % ( node, str(volumes)) 
		remotecmd = ""
		if format: 
			for volume in volumes:
				remotecmd += "sudo %s %s; " % ( fetch_config( ["localdisk", "mkfscmd"]), volume)
		hdfsconfig = {} 
		for volume in volumes:
			# mount remote volumes. 
			mountpoint = config["hdfs"]["datadir"][volume]
			remotecmd += "sudo mkdir -p %s; " % mountpoint
			remotecmd += "sudo mount %s %s; " % ( volume, mountpoint )
		utils.SSH_exec_cmd( config["ssh_cert"], config["admin_username"], node, remotecmd, showCmd=verbose )
		fstabcontent = "%s %s %s" %( volume, mountpoint, fetch_config( ["localdisk", "mountoptions"]))
		insert_fstab_section( node, "MOUNTLOCALDISK", fstabcontent )

def unmount_partition_volume( nodes, deviceSelect ):
	nodesinfo = get_partitions(nodes, deviceSelect )
	#if verbose: 
	#	print nodesinfo
	reg = re.compile( deviceSelect )
	for node in nodesinfo:
		alldeviceinfo = nodesinfo[node]
		volumes = find_matched_volume( alldeviceinfo, reg )
		if verbose:
			print "................. Node %s ................." % node
			print "Node = %s, volume = %s " % ( node, str(volumes)) 
		remotecmd = ""
		for volume in volumes:
			# mount remote volumes. 
			mountpoint = config["hdfs"]["datadir"][volume]
			remotecmd += "sudo umount %s; " % ( mountpoint )
		utils.SSH_exec_cmd( config["ssh_cert"], config["admin_username"], node, remotecmd, showCmd=verbose )
		remove_fstab_section( node, "MOUNTLOCALDISK" )

def generate_hdfs_nodelist( nodes, port, sepchar):
	return sepchar.join( map( lambda x: x+":"+str(port), nodes))

def generate_hdfs_containermounts():
	config["hdfs"]["containermounts"] = {}
	for (k,v) in config["hdfs"]["datadir"].iteritems():
		volumename = k[1:].replace("/","-")
		config["hdfs"]["containermounts"][volumename] = v

def generate_hdfs_config( nodes, deviceSelect):
	generate_hdfs_containermounts()
	hdfsconfig = copy.deepcopy( config["hdfsconfig"] )
	hdfsconfig["hdfs_cluster_name"] = config["hdfs_cluster_name"]
	zknodes = get_node_lists_for_service("zookeeper")
	zknodelist = generate_hdfs_nodelist( zknodes, fetch_config( ["hdfsconfig", "zks", "port"]), ",")
	if verbose:
		print "Zookeeper nodes: " + zknodelist
	hdfsconfig["zks"]["nodes"] = zknodelist
	hdfsconfig["namenode"]["namenode1"] = get_node_lists_for_service("namenode1")[0]
	namenode2list = get_node_lists_for_service("namenode2")
	if len(namenode2list)>0:
		hdfsconfig["namenode"]["namenode2"] = get_node_lists_for_service("namenode2")[0]
	journalnodes = get_node_lists_for_service("journalnode")
	if verbose:
		print "Journal nodes: " + zknodelist
	journalnodelist = generate_hdfs_nodelist( journalnodes, fetch_config( ["hdfsconfig", "journalnode", "port"]), ";")
	hdfsconfig["journalnode"]["nodes"] = journalnodelist
	config["hdfsconfig"]["namenode"] = hdfsconfig["namenode"]
	return hdfsconfig

# Write configuration for each hdfs node. 
def hdfs_config( nodes, deviceSelect):
	hdfsconfig = generate_hdfs_config( nodes, deviceSelect )
	if verbose: 
		print "HDFS Configuration: %s " % hdfsconfig
	nodesinfo = get_partitions(nodes, deviceSelect )
	#if verbose: 
	#	print nodesinfo
	reg = re.compile( deviceSelect )
	for node in nodesinfo:
		alldeviceinfo = nodesinfo[node]
		volumes = find_matched_volume( alldeviceinfo, reg )
		if verbose:
			print "................. Node %s ................." % node
			print "Node = %s, volume = %s " % ( node, str(volumes)) 
		volumelist = []
		for volume in volumes:
			# mount remote volumes. 
			devicename = volume[volume.rfind("/")+1:]
			mountpoint = os.path.join( config["local-mount-path"], devicename )
			volumelist.append( mountpoint )
		volumelist.sort()
		volumeinfo = ",".join(volumelist)
		hdfsconfig["dfs"]["data"] = volumeinfo
		os.system( "mkdir -p %s" % config["docker-run"]["hdfs"]["volumes"]["configDir"]["from"])
		config_file = "%s/config.yaml" % config["docker-run"]["hdfs"]["volumes"]["configDir"]["from"]		
		with open(config_file,'w') as datafile:
			yaml.dump(hdfsconfig, datafile, default_flow_style=False)
		utils.sudo_scp( config["ssh_cert"], config_file, config["hdfsconfig"]["configfile"], config["admin_username"], node)
	zknodes = get_node_lists_for_service("zookeeper")
	for node in zknodes:
		if not (node in nodesinfo):
			# The node is used for HDFS infrastructure, and needs configuration. 
			os.system( "mkdir -p %s" % config["docker-run"]["hdfs"]["volumes"]["configDir"]["from"])
			config_file = "%s/config.yaml" % config["docker-run"]["hdfs"]["volumes"]["configDir"]["from"]
			hdfsconfig["dfs"]["data"] = ""
			with open(config_file,'w') as datafile:
				yaml.dump(hdfsconfig, datafile, default_flow_style=False)
			utils.sudo_scp( config["ssh_cert"], config_file, config["hdfsconfig"]["configfile"], config["admin_username"], node)
			
	# Render docker. 
	# utils.render_template_directory("../docker-images/hdfs", "./deploy/docker-images/hdfs", config, verbose)

# Create gluster FS volume 
def create_glusterFS_volume( nodesinfo, glusterFSargs ):
	utils.render_template_directory("./storage/glusterFS", "./deploy/storage/glusterFS", config, verbose)
	config_glusterFS = write_glusterFS_configuration( nodesinfo, glusterFSargs )
	regmatch = regmatch_glusterFS(glusterFSargs)
	# print nodesinfo
	for node in nodesinfo:
		alldeviceinfo = nodesinfo[node]
		volumes = find_matched_volume( alldeviceinfo, regmatch )
		print "................. Node %s ................." % node
		# print volumes
		# print alldeviceinfo
		remotecmd = ""
		remotecmd += "sudo modprobe dm_thin_pool; "
		remotecmd += "sudo apt-get install -y thin-provisioning-tools; "
		capacityGB = 0.0
		for volume in volumes:
			remotecmd += "sudo pvcreate -f "  
			dataalignment = fetch_config( ["glusterFS", "dataalignment"] )
			if not dataalignment is None: 
				remotecmd += " --dataalignment " + dataalignment
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
		utils.sudo_scp(config["ssh_cert"],"./deploy/storage/glusterFS/mnt-glusterfs-localvolume.mount", "/etc/systemd/system/" + remotemount, config["admin_username"], node, verbose=verbose )
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
		utils.SSH_exec_cmd( config["ssh_cert"], config["admin_username"], node, remotecmd )
	
def remove_glusterFS_volume( nodesinfo, glusterFSargs ):
	regmatch = regmatch_glusterFS(glusterFSargs)
	for node in nodesinfo:
		alldeviceinfo = nodesinfo[node]
		volumes = find_matched_volume( alldeviceinfo, regmatch )
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
		utils.SSH_exec_cmd( config["ssh_cert"], config["admin_username"], node, remotecmd )		

def display_glusterFS_volume( nodesinfo, glusterFSargs ):
	for node in nodesinfo:
		print "................. Node %s ................." % node
		remotecmd = "sudo pvdisplay; sudo vgdisplay; sudo lvdisplay"
		utils.SSH_exec_cmd( config["ssh_cert"], config["admin_username"], node, remotecmd )

def exec_on_all(nodes, args, supressWarning = False):
	cmd = ""
	for arg in args:
		if cmd == "":
			cmd += arg
		else:
			cmd += " " + arg
	for node in nodes:
		utils.SSH_exec_cmd(config["ssh_cert"], config["admin_username"], node, cmd)
		print "Node: " + node + " exec: " + cmd

def exec_on_all_with_output(nodes, args, supressWarning = False):
	cmd = ""
	for arg in args:
		if cmd == "":
			cmd += arg
		else:
			cmd += " " + arg
	for node in nodes:
		output = utils.SSH_exec_cmd_with_output(config["ssh_cert"], config["admin_username"], node, cmd, supressWarning)
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
	utils.SSH_exec_cmd_with_directory(config["ssh_cert"], config["admin_username"], node, srcdir, fullcmd, supressWarning)
		

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
			macs = utils.get_mac_address(config["ssh_cert"],config["admin_username"], node, show=False )
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
				utils.SSH_exec_cmd( config["ssh_cert"], config["admin_username"], node, cmd )

def set_freeflow_router(  ):
	nodes = get_worker_nodes(config["clusterId"]) + get_ETCD_master_nodes(config["clusterId"])
	for node in nodes:
		set_freeflow_router_on_node(node)



def set_freeflow_router_on_node( node ):
	docker_image = config["freeflow_route_docker_image"]
	docker_name = "freeflow"
	network = config["network"]["container-network-iprange"]
	#setup HOST_IP, iterate all the host IP, find the one in ip range {{network.Container-networking}}
	output = utils.SSH_exec_cmd_with_output(config["ssh_cert"], config["admin_username"], node, "ifconfig | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*'")
	ips = output.split("\n")
	for ip in ips:
		if utils.addressInNetwork(ip, network):
			utils.SSH_exec_cmd(config["ssh_cert"], config["admin_username"], node, "sudo docker rm -f freeflow")
			utils.SSH_exec_cmd(config["ssh_cert"], config["admin_username"], node, "sudo docker run -d -it --privileged --net=host -v /freeflow:/freeflow -e \"HOST_IP=%s\" --name %s %s" % (ip, docker_name, docker_image))
			break

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
	one_command = " ".join(commands)
	kube_command = ""
	if (config["isacs"]):
		kube_command = "%s --kubeconfig=./deploy/%s %s" % (prog, config["acskubeconfig"], one_command)
	else:
		nodes = get_ETCD_master_nodes(config["clusterId"])
		master_node = random.choice(nodes)
		kube_command = ("%s --server=https://%s:%s --certificate-authority=%s --client-key=%s --client-certificate=%s %s" % (prog, master_node, config["k8sAPIport"], "./deploy/ssl/ca/ca.pem", "./deploy/ssl/kubelet/apiserver-key.pem", "./deploy/ssl/kubelet/apiserver.pem", one_command) )
	if verbose:
		print kube_command
	os.system(kube_command)

def run_kubectl( commands ):
	run_kube( "./deploy/bin/kubectl", commands)
	
def kubernetes_get_node_name(node):
	if config["isacs"]:
		return config["nodenames_from_ip"][node]
	else:
		domain = get_domain()
		if len(domain) < 2: 
			return node
		elif domain in node:
			# print "Remove domain %d" % len(domain)
			return node[:-(len(domain))]
		else:
			return node

def set_zookeeper_cluster():
	nodes = get_node_lists_for_service("zookeeper")
	config["zookeepernodes"] = ";".join(nodes)
	config["zookeepernumberofnodes"] = str(len(nodes))

def render_service_templates():
	allnodes = get_nodes(config["clusterId"])
	# Additional parameter calculation
	set_zookeeper_cluster()
	# Multiple call of render_template will only render the directory once during execution. 
	utils.render_template_directory( "./services/", "./deploy/services/", config)
	
def get_all_services():
	render_service_templates()
	rootdir = "./deploy/services"
	servicedic = {}
	for service in os.listdir(rootdir):
		dirname = os.path.join(rootdir, service)
		if os.path.isdir(dirname):
			launch_order_file = os.path.join( dirname, "launch_order")
			if os.path.isfile( launch_order_file ):
				servicedic[service] = launch_order_file
			else:
				yamlname = os.path.join(dirname, service + ".yaml")
				if not os.path.isfile(yamlname):
					yamls = glob.glob("*.yaml")
					yamlname = yamls[0]
				with open( yamlname ) as f:
					content = f.read()
					f.close()
					if content.find( "DaemonSet" )>=0 or content.find("ReplicaSet")>=0:
						# Only add service if it is a daemonset. 
						servicedic[service] = yamlname
	return servicedic
	
def get_service_name(service_config_file):
	f = open(service_config_file)
	try:
		service_config = yaml.load(f)
	except:
		return None
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
	# print	servicedic
	newentries = {}
	for service in servicedic:
		servicename = get_service_name(servicedic[service])
		newentries[servicename] = servicedic[service]
	servicedic.update(newentries)
	# print servicedic
	fname = servicedic[use_service]
	return fname
			
def kubernetes_label_node(cmdoptions, nodename, label):
	run_kubectl(["label nodes %s %s %s" % (cmdoptions, nodename, label)])

# Get the list of nodes for a particular service
# 
def get_node_lists_for_service(service):
		labels = fetch_config(["kubelabels"])
		nodetype = labels[service] if service in labels else labels["default"]
		if nodetype == "worker_node":
			nodes = config["worker_node"]
		elif nodetype == "etcd_node":
			nodes = config["etcd_node"]
		elif nodetype.find( "etcd_node_" )>=0:
			nodenumber = int(nodetype[nodetype.find( "etcd_node_" )+len("etcd_node_"):])
			if len(config["etcd_node"])>=nodenumber:
				nodes = [ config["etcd_node"][nodenumber-1] ]
			else:
				nodes = []
		elif nodetype == "all":
			nodes = config["worker_node"] + config["etcd_node"]
		else:
			machines = fetch_config(["machines"])
			if machines is None:
				print "Service %s has a nodes type %s, but there is no machine configuration to identify node" % (service, nodetype)
				exit(-1)
			allnodes = config["worker_node"] + config["etcd_node"]
			nodes = []
			for node in allnodes:
				nodename = kubernetes_get_node_name(node)
				if nodename in machines and nodetype in machines[nodename]:
					nodes.append(node)
		return nodes

# Label kubernete nodes according to a service. 
# A service (usually a Kubernete daemon service) can request to be run on:
# all: all nodes
# etcd_node: all etcd node
# etcd_node_n: a particular etcd node
# worker_node: all worker node
# The kubernete node will be marked accordingly to facilitate the running of daemon service. 
def kubernetes_label_nodes( verb, servicelists, force ):
	servicedic = get_all_services()
	# print servicedic
	get_nodes(config["clusterId"])
	labels = fetch_config(["kubelabels"])
	# print labels
	for service, serviceinfo in servicedic.iteritems():
		servicename = get_service_name(servicedic[service])
		# print "Service %s - %s" %(service, servicename )
		if (not service in labels) and (not servicename in labels) and "default" in labels and (not servicename is None):
			labels[servicename] = labels["default"]
	# print servicelists
	# print labels
	if len(servicelists)==0:
		servicelists = labels
	else:
		for service in servicelists:
			if (not service in labels) and "default" in labels:
				labels[service] = labels["default"]
	# print servicelists
	for label in servicelists:
		nodes = get_node_lists_for_service(label)
		if verbose: 
			print "kubernetes: apply action %s to label %s to nodes: %s" %(verb, label, nodes)
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

# Label kubernete nodes according to property of node (usually specified in config.yaml or cluster.yaml)
# Certain property of node:
# E.g., rack 
def kubernetes_mark_nodes( marklist, bMark ):
	if marklist == []:
		marklist = config["kubemarks"]
	if verbose:
		print "Mark %s: %s" % (bMark, marklist)
	nodes = get_nodes(config["clusterId"])
	for node in nodes:
		nodename = kubernetes_get_node_name(node)
		nodeconfig = fetch_config(["machines", nodename])
		if verbose:
			print "----- Node %s ------ " % nodename
			print nodeconfig
		for mark in marklist:
			if mark in nodeconfig:
				if bMark:
					kubernetes_label_node( "--overwrite", nodename, mark+"="+nodeconfig[mark] )
				else:
					kubernetes_label_node( "", nodename, mark+"-" )

def start_one_kube_service(fname):
	if verbose:
		f = open(fname)
		service_yaml = yaml.load(f)
		f.close()
		print "Start service: "
		print service_yaml
	run_kubectl( ["create", "-f", fname ] )

def stop_one_kube_service(fname):
	run_kubectl( ["delete", "-f", fname ] )

def start_kube_service( servicename ):
	fname = get_service_yaml( servicename )
	# print "start service %s with %s" % (servicename, fname)
	dirname = os.path.dirname(fname)
	if os.path.exists(os.path.join(dirname,"launch_order")):
		with open(os.path.join(dirname,"launch_order"),'r') as f:
			allservices = f.readlines()
			for filename in allservices:
				filename = filename.strip('\n')
				start_one_kube_service(os.path.join(dirname,filename))		
	else:
		start_one_kube_service(fname)

def stop_kube_service( servicename ):
	fname = get_service_yaml( servicename )
	dirname = os.path.dirname(fname)
	if os.path.exists(os.path.join(dirname,"launch_order")):
		with open(os.path.join(dirname,"launch_order"),'r') as f:
			allservices = f.readlines()
			for filename in reversed(allservices):
				filename = filename.strip('\n')
				stop_one_kube_service(os.path.join(dirname,filename))		
	else:
		stop_one_kube_service(fname)
	
	
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

def check_buildable_images(nargs):
	for imagename in nargs:
		imagename = imagename.lower()
		if imagename in config["build-docker-via-config"]:
			print "Docker image %s should be built via configuration. " % imagename
			exit()
	
def run_docker_image( imagename, native = False, sudo = False ):
	dockerConfig = fetch_config( ["docker-run", imagename ])
	full_dockerimage_name = build_docker_fullname( config, imagename )
	# print full_dockerimage_name
	matches = find_dockers( full_dockerimage_name )
	if len( matches ) == 0:
		local_dockerimage_name = config["dockerprefix"] + dockername + ":" + config["dockertag"]
		matches = find_dockers( local_dockerimage_name )
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
			run_docker( matches[0], prompt = imagename, dockerConfig = dockerConfig, sudo = sudo )	

def run_command( args, command, nargs, parser ):
	nocache = args.nocache
	
	# If necessary, show parsed arguments. 
	# print args
	global discoverserver
	global homeinserver
	global verbose
	global config
	
	global ipAddrMetaname
	discoverserver = args.discoverserver
	homeinserver = args.homeinserver

	if args.verbose: 
		verbose = True
		utils.verbose = True
	
	if command == "restore":
		utils.restore_keys(nargs)
	
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

	add_acs_config(command)
	if verbose and config["isacs"]:
		print "Using Azure Container Services"

	update_config()
	
	# additional glusterfs launch parameter.
	config["launch-glusterfs-opt"] = args.glusterfs;

	get_ssh_config()
	
	if args.yes:
		global defanswer
		print "Use yes for default answer"
		defanswer = "yes"
		
	if args.public:
		ipAddrMetaname = "clientIP"
		
	
	if verbose: 
		print "deploy " + command + " " + (" ".join(nargs))

	if command == "restore":
		# Second part of restore, after config has been read.
		if os.path.exists("./deploy/acs_kubeclusterconfig"):
			acs_tools.acs_get_config()
		bForce = args.force if args.force is not None else False
		get_kubectl_binary(force=args.force)
		exit()


	if command =="clean":
		clean_deployment()
		exit()
	
	elif command == "sleep":
		sleeptime = 10 if len(nargs)<1 else int(nargs[0])
		print "Sleep for %s sec ... " % sleeptime
		for si in range(sleeptime):
			sys.stdout.write(".")
			sys.stdout.flush()
			time.sleep(1)

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
			utils.SSH_connect( config["ssh_cert"], config["admin_username"], nodename)
			exit()

	elif command == "deploy" and "clusterId" in config:
		deploy_ETCD_master()

	elif command == "build":
		if len(nargs) <=0:
			init_deployment()
#			response = raw_input_with_default("Create ISO file for deployment (y/n)?")
#			if first_char(response) == "y":
#				create_ISO()
#			response = raw_input_with_default("Create PXE docker image for deployment (y/n)?")
#			if first_char(response) == "y":
#				create_PXE()
		elif nargs[0] == "iso-coreos":
			create_ISO()
		elif nargs[0] == "pxe-coreos":
			create_PXE()
		elif nargs[0] == "pxe-ubuntu":
			create_PXE_ubuntu()
		else:
			parser.print_help()
			print "Error: build target %s is not recognized. " % nargs[0] 
			exit()

	elif command == "sshkey":
		if len(nargs) >=1 and nargs[0] == "install":
			install_ssh_key(nargs[1:])
		else:
			parser.print_help()
			print "Error: build target %s is not recognized. " % nargs[0] 
			exit()
			
	elif command == "updateworker":
		response = raw_input_with_default("Deploy Worker Nodes (y/n)?")
		if first_char(response) == "y":
			#utils.render_template_directory("./template/kubelet", "./deploy/kubelet",config)
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
			utils.get_mac_address(config["ssh_cert"], config["admin_username"], node)
			
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

	elif command == "freeflow" and len(nargs) >= 1:
		if nargs[0] == "set":
			set_freeflow_router()
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
		allnodes = get_nodes(config["clusterId"])
		# ToDo: change pending, schedule glusterFS on master & ETCD nodes, 
		nodes = get_node_lists_for_service("glusterfs")
		glusterFSargs = fetch_config( ["glusterFS", "partitions"] )
		if nargs[0] == "display":
			display_glusterFS_volume( nodes, glusterFSargs )
			exit()
				
		nodesinfo = get_partitions(nodes, glusterFSargs )
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

	elif command == "hdfs" and len(nargs) >=1:
		allnodes = get_nodes(config["clusterId"])
		nodes = get_node_lists_for_service("hdfs")
		if nargs[0] == "create":
			print ("This operation will CREATE new volume over all existing hdfs partitions, and will erase the data on those partitions "  )
			response = raw_input ("Please type (CREATE) in ALL CAPITALS to confirm the operation ---> ")
			if response == "CREATE":
				format_mount_partition_volume( nodes, fetch_config(["hdfs", "partitions"]), True )
		elif nargs[0] == "mount":
			format_mount_partition_volume( nodes, fetch_config(["hdfs", "partitions"]), False )
		elif nargs[0] == "umount":
			unmount_partition_volume( nodes, fetch_config(["hdfs", "partitions"]))
		elif nargs[0] == "config":
			hdfs_config( nodes, fetch_config(["hdfs", "partitions"]))
			push_docker_images( ["hdfs"] )
			push_docker_images( ["spark"] )
		else:
			parser.print_help()
			print "Unknown subcommand for hdfs " + nargs[0]
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

	elif command == "mount":
		if len(nargs)<=0:
			fileshare_install()
			allmountpoints = mount_fileshares_by_service(True)
			link_fileshares(allmountpoints, args.force)
		elif nargs[0]=="install":
			fileshare_install()
		elif nargs[0]=="start":
			allmountpoints = mount_fileshares_by_service(True)
			link_fileshares(allmountpoints, args.force)
		elif nargs[0]=="stop":
			unmount_fileshares_by_service(False)
		elif nargs[0]=="clean":
			print ("This operation will CLEAN local content in the physical mount point, and may erase the data on those locations. "  )
			response = raw_input ("Please type (CLEAN) in ALL CAPITALS to confirm the operation ---> ")
			if response == "CLEAN":
				unmount_fileshares_by_service(True)
		elif nargs[0]=="nolink":
			mount_fileshares_by_service(True)
		elif nargs[0]=="link":
			all_nodes = get_nodes(config["clusterId"])
			allmountpoints, fstab = get_mount_fileshares()
			link_fileshares(allmountpoints, args.force)
		else:
			parser.print_help()
			print "Error: mount subcommand %s is not recognized " % nargs[0]
	elif command == "labelwebui":
		label_webUI(nargs[0])
		
	elif command == "production":
		set_host_names_by_lookup()
		success = deploy_ETCD_master()
		if success: 
			update_worker_nodes( [] )

	elif command == "azure":
		config["WinbindServers"] = []
		run_script_blocks(scriptblocks["azure"])

	elif command == "acs":
		k8sconfig["kubelet-path"] = "./deploy/bin/kubectl --kubeconfig=./deploy/%s" % (config["acskubeconfig"])
		#print "Config: " + k8sconfig["kubelet-path"]
		if (len(nargs) == 0):
			run_script_blocks(scriptblocks["acs"])
		elif (len(nargs) >= 1):
			if nargs[0]=="deploy":
				acs_tools.acs_deploy() # Core K8s cluster deployment
			elif nargs[0]=="getconfig":
				acs_tools.acs_get_config()
			elif nargs[0]=="getip":
				ip = acs_tools.acs_get_machinesAndIPsFast()
				print ip
			elif nargs[0]=="getallip":
				ip = acs_tools.acs_get_machinesAndIPs(False)
				print ip
			elif nargs[0]=="createip":
				ip = acs_tools.acs_get_machinesAndIPs(True)
				print ip
			elif nargs[0]=="label":
				ip = get_nodes_from_acs("")
				acs_label_webui()
			elif nargs[0]=="openports":
				acs_tools.acs_add_nsg_rules({"HTTPAllow" : 80, "RestfulAPIAllow" : 5000, "AllowKubernetesServicePorts" : "30000-32767"})
			elif nargs[0]=="restartwebui":
				run_script_blocks(scriptblocks["restartwebui"])
			elif nargs[0]=="getserviceaddr":
				print "Address: =" + json.dumps(k8sUtils.GetServiceAddress(nargs[1]))
			elif nargs[0]=="storage":
				acs_tools.acs_create_storage()
			elif nargs[0]=="storagemount":
				acs_tools.acs_create_storage()
				fileshare_install()
				allmountpoints = mount_fileshares_by_service(True)
				del_fileshare_links()
				link_fileshares(allmountpoints, args.force)		
			elif nargs[0]=="bldwebui":
				run_script_blocks(scriptblocks["bldwebui"])
			elif nargs[0]=="gpudrivers":
				if (config["acs_isgpu"]):
					acs_install_gpu()
			elif nargs[0]=="addons":
				# deploy addons / config changes (i.e. weave.yaml)
				acs_deploy_addons()
			elif nargs[0]=="freeflow":
				if ("freeflow" in config) and (config["freeflow"]):
					kube_dpeloy_configchanges() # starte weave.yaml
					run_script_blocks(["kubernetes start freeflow"])
			elif nargs[0]=="jobendpt":
				acs_get_jobendpt(nargs[1])
			elif nargs[0]=="dns":
				acs_attach_dns_name()
			elif nargs[0]=="postdeploy":
				acs_post_deploy()
			elif nargs[0]=="genconfig":
				acs_tools.acs_update_azconfig(True)
			elif nargs[0]=="delete":
				# for delete, delete the acs_resource_group (the parent group for westus2)
				az_tools.config["azure_cluster"]["resource_group_name"] = config["acs_resource_group"]
				az_tools.delete_cluster()
			elif nargs[0]=="vm":
				if (len(nargs) == 2):
					acs_tools.az_sys("vm {0} --ids $(az vm list -g {1} --query \"[].id\" -o tsv)".format(nargs[1], config["resource_group"]))

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
			generate_hdfs_containermounts()
			if nargs[0] == "start":
				if args.force and "hdfsformat" in servicenames:
					print ("This operation will WIPEOUT HDFS namenode, and erase all data on the HDFS cluster,  "  )
					response = raw_input ("Please type (WIPEOUT) in ALL CAPITALS to confirm the operation ---> ")
					if response == "WIPEOUT":
						config["hdfsconfig"]["formatoptions"] = "--force "
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
					print "Error: kubernetes labels expect a verb which is either active, inactive or remove, but get: " + nargs[1]
			elif nargs[0] == "mark":
				kubernetes_mark_nodes( nargs[1:], True)
			elif nargs[0] == "unmark":
				kubernetes_mark_nodes( nargs[1:], False)
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
			get_kubectl_binary()
	
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
				check_buildable_images(nargs[1:])
				build_docker_images(nargs[1:])
			elif nargs[0] == "push":
				check_buildable_images(nargs[1:])
				push_docker_images(nargs[1:])
			elif nargs[0] == "run":
				if len(nargs)>=2:
					run_docker_image( nargs[1], args.native, sudo = args.sudo ) 
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
	elif command == "rendertemplate":
		if len(nargs) != 2:
			parser.print_help()
			exit()
		template_file = nargs[0]
		target_file = nargs[1]
		utils.render_template(template_file, target_file,config)
	else:
		parser.print_help()
		print "Error: Unknown command " + command

def run_script_blocks( script_collection ):
	if verbose:
		print "Run script blocks %s " % script_collection
	for script in script_collection:
		print "parse script %s" % ( script)
		args = parser.parse_args( script.split(" "))
		command = args.command
		nargs = args.nargs
		print "Run command %s, args %s" % (command, nargs )
		run_command( args, command, nargs, parser )

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
  scriptblocks Execute a block of scripts. 
            azure
  build     [arg] Build deployment environment 
  			arg="": should be executed first, generate keys for the cluster
			arg=iso-coreos: build ISO image fore CoreOS deployment.
			arg=pxe-coreos: build PXE server for CoreOS deployment. 
			arg=pxe-ubuntu: build PXE server for Ubuntu deployment. [We use standard Ubuntu ISO for Ubuntu ISO deployment. ]
  sshkey    install: [Ubuntu] install sshkey to Ubuntu cluster. 
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
  mount     install | start | stop | link
  		    start: mount all fileshares 
			install: install all client components related to the fileshare
			stop: unmount all fileshares
			nolink: mount all fileshares, but doesnot symbolic link to the mount share
  glusterfs [args] manage glusterFS on the cluster. 
            display: display lvm information on each node of the cluster. 
            create: formatting and create lvm for used by glusterfs. 
            remove: deletel and remove glusterfs volumes. 
            config: generate configuration file, build and push glusterfs docker.
            start: start glusterfs service and endpoints. 
            stop: stop glusterfs service and endpoints. 
  hdfs      [args] manage HDFS on the cluster. 
  			create: formatting and create local drive for use by HDFS. 
			mount: mount local drive for use by HDFS. 
			umount: unmount local drive that is used for HDFS.
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
            labels verb [services]: applying labels to node according to service (usually daemon) setup. 
              -y: overwrite existing value
              verb: active, inactive, remove (default=on)
              services: if none, apply to all services in the service directory
			mark [properties]: applying labels on node according to node property (usually in cluster.yaml)
			unmark [properties]: removing labels on node according to node property (usually in cluster.yaml)
  kubectl   [args] run a native kubectl command. 
  docker    [args] manage docker images. 
            build: build one or more docker images associated with the current deployment. 
            push: build and push one or more docker images to register
			run [--sudo]: run a docker image (--sudo: in super user mode)
  execonall [cmd ... ] Execute the command on all nodes and print the output. 
  doonall [cmd ... ] Execute the command on all nodes. 
  runscriptonall [script] Execute the shell/python script on all nodes. 
  listmac   display mac address of the cluster notes
  checkconfig   display config items
  rendertemplate template_file target_file
  ''') )
	parser.add_argument("-y", "--yes", 
		help="Answer yes automatically for all prompt", 
		action="store_true" )
	parser.add_argument("--force", 
		help="Force perform certain operation", 
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
	parser.add_argument("--nodes", 
		help = "Specify an python regular expression that limit the nodes that the operation is applied.", 
        action="store",
		default=None	
		)
		
	parser.add_argument("command", 
		help = "See above for the list of valid command" )
	parser.add_argument('nargs', nargs=argparse.REMAINDER, 
		help="Additional command argument", 
		)
	args = parser.parse_args()
	command = args.command
	nargs = args.nargs
	if args.verbose:
		verbose = True
		utils.verbose = True
	if args.nodes is not None:
		limitnodes = args.nodes

	config = init_config()

	if command == "scriptblocks":
		if nargs[0] in scriptblocks:
			run_script_blocks( scriptblocks[nargs[0]])
		else:
			parser.print_help()
			print "Error: Unknown scriptblocks " + nargs[0]
	else:
		run_command( args, command, nargs, parser)
