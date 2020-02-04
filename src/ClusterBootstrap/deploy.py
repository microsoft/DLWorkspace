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
import requests

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
from DockerUtils import push_one_docker, build_dockers, push_dockers, run_docker, find_dockers, build_docker_fullname, copy_from_docker_image, configuration
import k8sUtils
from config import config as k8sconfig

sys.path.append("../docker-images/glusterfs")
import launch_glusterfs
import az_tools
import acs_tools

from params import default_config_parameters, scriptblocks
from ConfigUtils import *

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
allroles = {"infra", "infrastructure", "worker", "nfs", "sql", "samba", "mysqlserver"}


# default search for all partitions of hdb, hdc, hdd, and sdb, sdc, sdd

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

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
    _check_config_items("service_cluster_ip_range",cnf)
    if not os.path.isfile(config["ssh_cert"]):
        raise Exception("ERROR: we cannot find ssh key file at %s. \n please run 'python build-pxe-coreos.py docker_image_name' to generate ssh key file and pxe server image." % config["ssh_cert"])

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
    "etcd_user": ( ["admin_username"], lambda x:x ),
    "kubernetes_master_ssh_user": ( ["admin_username"], lambda x:x ),
}

def isInstallOnCoreOS():
    return config["platform-scripts"]!="ubuntu" and config["platform-scripts"]!="acs"

def update_docker_image_config():
    # update docker image
    #print "Config:\n{0}\n".format(config)
    if config["kube_custom_scheduler"] or config["kube_custom_cri"]:
        if "container" not in config["dockers"]:
            config["dockers"]["container"] = {}
        if "hyperkube" not in config["dockers"]["container"]:
            config["dockers"]["container"]["hyperkube"] = {}
        # config["dockers"]["container"]["hyperkube"]["fullname"] = config["worker-dockerregistry"] + config["dockerprefix"] + "kubernetes:" + config["dockertag"]

def update_config():
    apply_config_mapping(config, default_config_mapping)
    update_one_config(config, "coreosversion",["coreos","version"], basestring, coreosversion)
    update_one_config(config, "coreoschannel",["coreos","channel"], basestring, coreoschannel)
    update_one_config(config, "coreosbaseurl",["coreos","baseurl"], basestring, coreosbaseurl)
    if config["coreosbaseurl"] == "":
        config["coreosusebaseurl"] = ""
    else:
        config["coreosusebaseurl"] = "-b "+config["coreosbaseurl"]

    for (cf, loc) in [('master', 'master'), ('worker', 'kubelet')]:
        exec("config[\"%s_predeploy\"] = os.path.join(\"./deploy/%s\", config[\"pre%sdeploymentscript\"])" % (cf, loc, cf))
        exec("config[\"%s_filesdeploy\"] = os.path.join(\"./deploy/%s\", config[\"%sdeploymentlist\"])" % (cf, loc, cf))
        exec("config[\"%s_postdeploy\"] = os.path.join(\"./deploy/%s\", config[\"post%sdeploymentscript\"])" % (cf, loc, cf))
    config["webportal_node"] = None if len(get_node_lists_for_service("webportal"))==0 else get_node_lists_for_service("webportal")[0]

    if ("influxdb_node" not in config):
        config["influxdb_node"] = config["webportal_node"]
    if ("elasticsearch_node" not in config):
        config["elasticsearch_node"] = config["webportal_node"]
    if ("mysql_node" not in config):
        config["mysql_node"] = None if len(get_node_lists_for_service("mysql"))==0 else get_node_lists_for_service("mysql")[0]
    if ("host" not in config["prometheus"]):
        config["prometheus"]["host"] = None if len(get_node_lists_for_service("prometheus"))==0 else get_node_lists_for_service("prometheus")[0]

    update_docker_image_config()

def add_ssh_key():
    keys = fetch_config(config, ["sshKeys"])
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

        config["master_dns_name"] = config["cluster_name"]

        # Use az tools to generate default config params and overwrite if they don't exist
        configAzure = acs_tools.acs_update_azconfig(False)
        if verbose:
            print "AzureConfig:\n{0}".format(configAzure)
        utils.mergeDict(config, configAzure, True) # ovewrites defaults with Azure defaults
        if verbose:
            print "Config:\n{0}".format(config)

        if ("resource_group" in config and "acs_resource_group" in config):
            config["resource_group_set"] = True
            az_tools.config["azure_cluster"]["resource_group_name"] = config["resource_group"]

        config["resource_group"] = az_tools.config["azure_cluster"]["resource_group_name"]
        config["platform-scripts"] = "acs"
        config["WinbindServers"] = []
        config["etcd_node_num"] = config["master_node_num"]
        config["kube_addons"] = [] # no addons
        # config["mountpoints"]["rootshare"]["azstoragesku"] = config["azstoragesku"]
        # config["mountpoints"]["rootshare"]["azfilesharequota"] = config["azfilesharequota"]
        config["freeflow"] = True
        config["useclusterfile"] = True

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
        # encode to base64 and decode when used. this is to make STRUCTURED content more robust.
        # refer to {{cnf["ca.pem"]}} in template/cloud-config/cloud-config-worker.yml
        config[file] = base64.b64encode(content.encode('utf-8')).decode('utf-8')

def add_dns_entries():
    addCoreOSNetwork = ""
    dnsEntries = fetch_config(config, ["network", "externalDnsServers"])
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
    # additional entry to be added to write_files
    translate_config_entry( config, ["coreos", "write_files"], "coreoswritefiles", basestring, 2 )
    # additional entry to be added to units
    translate_config_entry( config, ["coreos", "units"], "coreosunits", basestring, 4 )
    # additional startup script to be added to report.sh
    translate_config_entry( config, ["coreos", "startupScripts"], "startupscripts", basestring )

def init_deployment():
    gen_new_key = True
    regenerate_key = False
    if (os.path.exists("./deploy/clusterID.yml")):
        clusterID = utils.get_cluster_ID_from_file()
        response = raw_input_with_default("There is a cluster (ID:%s) deployment in './deploy', do you want to keep the existing ssh key and CA certificates (y/n)?" % clusterID)
        if first_char(response) == "n":
            # Backup old cluster
            utils.backup_keys(config["cluster_name"])
            regenerate_key = True
        else:
            gen_new_key = False
    else:
        create_cluster_id()
    if gen_new_key:
        os.system("mkdir -p ./deploy/cloud-config")
        os.system("rm -r ./deploy/cloud-config")
        os.system("mkdir -p ./deploy/cloud-config")
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
    config["ca.pem"] = base64.b64encode(content.encode('utf-8')).decode('utf-8')

    with open("./deploy/ssl/kubelet/apiserver.pem", 'r') as f:
        content = f.read()
    config["apiserver.pem"] = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    config["worker.pem"] = base64.b64encode(content.encode('utf-8')).decode('utf-8')

    with open("./deploy/ssl/kubelet/apiserver-key.pem", 'r') as f:
        content = f.read()
    config["apiserver-key.pem"] = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    config["worker-key.pem"] = base64.b64encode(content.encode('utf-8')).decode('utf-8')

    add_additional_cloud_config()
    add_kubelet_config()
    template_file = "./template/cloud-config/cloud-config-worker.yml"
    target_file = "./deploy/cloud-config/cloud-config-worker.yml"
    utils.render_template( template_file, target_file ,config)

def check_node_availability(ipAddress):
    status = os.system('ssh -o "StrictHostKeyChecking no" -o "UserKnownHostsFile=/dev/null" -i %s -oBatchMode=yes %s@%s hostname > /dev/null' % (config["admin_username"], config["ssh_cert"], ipAddress))
    #status = sock.connect_ex((ipAddress,22))
    return status == 0

# Get domain of the node, assigned in add_acs_config (line config["network"]["domain"])
def get_domain():
    if "network" in config and "domain" in config["network"] and len(config["network"]["domain"]) > 0 :
        domain = "."+config["network"]["domain"]
    else:
        domain = ""
    return domain

# Get a list of nodes DNS from cluster.yaml
def get_nodes_from_config(machinerole):
    machinerole = "infrastructure" if machinerole == "infra" else machinerole
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

def get_node_full_name(nodename):
    return nodename + get_domain() if len(nodename.split("."))<3 else nodename

# Get a list of scaled nodes from cluster.yaml
def get_scaled_nodes_from_config():
    if "machines" not in config:
        return []
    else:
        domain = get_domain()
        Nodes = []
        for nodename in config["machines"]:
            nodeInfo = config["machines"][nodename]
            if "scaled" in nodeInfo and nodeInfo["scaled"]==True:
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
    if int(config["etcd_node_num"]) == 1:
        for nodename in config["machines"]:
            nodeInfo = config["machines"][nodename]
            if "role" in nodeInfo and nodeInfo["role"]=="infrastructure":
                assert "private-ip" in nodeInfo and "private IP of the infrastructure node is not provided!"
                config["etcd_private_ip"] = nodeInfo["private-ip"]
                break
    config["etcd_node"] = Nodes
    config["kubernetes_master_node"] = Nodes
    return Nodes

def get_ETCD_master_nodes(clusterId):
    if "etcd_node" in config and len(config["etcd_node"]) > 0:
        Nodes = config["etcd_node"]
        config["kubernetes_master_node"] = Nodes
        #print("From etcd_node " + " ".join(map(str, Nodes)))
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

def get_nodes_by_roles(roles):
    """
    role: "infrastructure", "worker", or "nfs"
    this function aims to deprecate get_worker_nodes_from_config and get_ETCD_master_nodes_from_config
    """
    Nodes = []
    for role in roles:
        tmp_nodes = get_nodes_from_config(role)
        if role == "infrastructure" or role == "infra":
            config["etcd_node"] = tmp_nodes
            config["kubernetes_master_node"] = tmp_nodes
        else:
            config["{}_node".format(role)] = tmp_nodes
        Nodes += tmp_nodes
    return Nodes

def get_worker_nodes(clusterId, isScaledOnly):
    nodes = []
    if "worker_node" in config and len(config["worker_node"]) > 0:
        nodes = config["worker_node"]
    if "useclusterfile" not in config or not config["useclusterfile"]:
        nodes = get_worker_nodes_from_cluster_report(clusterId)
    else:
        print("from console")
        nodes = get_nodes_by_roles(["worker"]) #get_worker_nodes_from_config(clusterId)

    if isScaledOnly:
        return get_scaled_nodes_from_config()
    else:
        return nodes

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
    nodes = get_ETCD_master_nodes(clusterId) + get_worker_nodes(clusterId, False)
    nodes = limit_nodes(nodes)
    return nodes

def get_scaled_nodes(clusterId):
    nodes = get_worker_nodes(clusterId, True)
    nodes = limit_nodes(nodes)
    return nodes

def check_master_ETCD_status():
    masterNodes = []
    etcdNodes = []
    print "==============================================="
    print "Checking Available Nodes for Deployment..."
    get_ETCD_master_nodes(config["clusterId"])
    get_worker_nodes(config["clusterId"], False)
    get_nodes_by_roles(["mysqlserver"])
    get_nodes_by_roles(["nfs"])
    get_nodes_by_roles(["samba"])
    print "==============================================="
    print "Activate Master Node(s): %s\n %s \n" % (len(config["kubernetes_master_node"]),",".join(config["kubernetes_master_node"]))
    print "Activate ETCD Node(s):%s\n %s \n" % (len(config["etcd_node"]),",".join(config["etcd_node"]))
    print "Activate Worker Node(s):%s\n %s \n" % (len(config["worker_node"]),",".join(config["worker_node"]))
    print "Activate MySQLServer Node(s):%s\n %s \n" % (len(config["mysqlserver_node"]), ",".join(config["mysqlserver_node"]))
    print "Activate NFS Node(s):%s\n %s \n" % (len(config["nfs_node"]),",".join(config["nfs_node"]))
    print "Activate Samba Node(s):%s\n %s \n" % (len(config["samba_node"]), ",".join(config["samba_node"]))

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
    config["apiserver_ssl_ip"] = "\n".join(["IP.{} = {}".format(i, sslip) for i, sslip in enumerate([config["api-server-ip"]] + config["ssl_localhost_ips"] + masterips)])
    # kube-apiserver aggregator use easyrsa to generate crt files, we need to generate a group of master names for it.
    # It does not care if it's a DNS name or IP.
    masternames = []
    for i,value in enumerate(config["kubernetes_master_node"]):
        masternames.append(value)
    config["apiserver_names_ssl_aggregator"] = ",".join(["DNS:"+name for i,name in enumerate(masternames)])
    # TODO(harry): this only works for single master, if we have multiple masters, we need to have a reserved static IP to be used here and for the whole cluster.
    config["master_ip_ssl_aggregator"] = utils.getIP(config["kubernetes_master_node"][0])


    for i,value in enumerate(config["etcd_node"]):
        if ippattern.match(value):
            etcdips.append(value)
        else:
            etcddns.append(value)

    config["etcd_ssl_dns"] = "\n".join(["DNS."+str(i+5)+" = "+dns for i,dns in enumerate(etcddns)])
    config["etcd_ssl_ip"] = "\n".join(["IP.{} = {}".format(i, sslip) for i, sslip in enumerate(config["ssl_localhost_ips"] + etcdips)])

def gen_worker_certificates():

    utils.render_template_directory("./template/ssl", "./deploy/ssl",config)
    os.system("cd ./deploy/ssl && bash ./gencerts_kubelet.sh")

def gen_master_certificates():

    GetCertificateProperty()

    utils.render_template_directory("./template/ssl", "./deploy/ssl",config)
    os.system("cd ./deploy/ssl && bash ./gencerts_master.sh")
    get_other_binary()
    os.system("cd ./deploy/ssl && bash ./gencerts_aggregator.sh")


def gen_ETCD_certificates():

    GetCertificateProperty()
    utils.render_template_directory("./template/ssl", "./deploy/ssl",config)
    os.system("cd ./deploy/ssl && bash ./gencerts_etcd.sh")

def load_az_params_as_default():
    from az_params import default_az_parameters
    # need az_params default, in case we don't have the key in config.yaml
    default_cfg = { k: v for k, v in default_az_parameters.items() }
    azure_cluster_cfg = { k: v for k, v in config["azure_cluster"].items() } if "azure_cluster" in config else {}
    merge_config(config["azure_cluster"], default_cfg["azure_cluster"])
    merge_config(config["azure_cluster"], azure_cluster_cfg)

def on_premise_params():
    print("Warning: remember to set parameters:\ngpu_count_per_node, gpu_type, worker_node_num\n when using on premise machine!")

def load_platform_type():
    platform_type = list(set(config.keys()) & set(config["supported_platform"]))
    assert len(platform_type) == 1 and "platform type should be specified explicitly and unique!"
    platform_type = platform_type[0]
    config["platform_type"] = platform_type

def gen_platform_wise_config():
    load_platform_type()
    azdefault = { 'network_domain':"config['network']['domain']",
        'worker_node_num':"config['azure_cluster']['worker_node_num']",
        'gpu_count_per_node':'config["sku_mapping"].get(config["azure_cluster"]["worker_vm_size"],config["sku_mapping"]["default"])["gpu-count"]',
        'gpu_type':'config["sku_mapping"].get(config["azure_cluster"]["worker_vm_size"],config["sku_mapping"]["default"])["gpu-type"]',
        'etcd_node_num': "config['azure_cluster']['infra_node_num']" }
    on_premise_default = {'network_domain':"config['network']['domain']"}
    platform_dict = { 'azure_cluster': azdefault, 'onpremise': on_premise_default }
    platform_func = { 'azure_cluster': load_az_params_as_default, 'onpremise': on_premise_params }
    default_dict, default_func = platform_dict[config["platform_type"]], platform_func[config["platform_type"]]
    default_func()
    need_val = ['network_domain', 'worker_node_num', 'gpu_count_per_node', 'gpu_type']
    config['etcd_node_num'] = config.get('etcd_node_num')

    for ky in need_val:
        if ky not in config:
            config[ky] = eval(default_dict[ky])

def gen_configs():
    print "==============================================="
    print "generating configuration files..."
    utils.clean_rendered_target_directory()
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

    if "kubernetes_master_node" in config:
        kubernetes_masters = config["kubernetes_master_node"]
    else:
        kubernetes_masters = []

    if not config["isacs"]:
        config["discovery_url"] = utils.get_ETCD_discovery_URL(int(config["etcd_node_num"]))

    if "ssh_cert" not in config and os.path.isfile("./deploy/sshkey/id_rsa"):
        config["ssh_cert"] = expand_path("./deploy/sshkey/id_rsa")

    config["etcd_user"] = config["admin_username"]
    config["nfs_user"] = config["admin_username"]
    config["kubernetes_master_ssh_user"] = config["admin_username"]

    config["api_servers"] = "https://"+config["kubernetes_master_node"][0]+":"+str(config["k8sAPIport"])
    config["etcd_endpoints"] = ",".join(["https://"+x+":"+config["etcd3port1"] for x in config["etcd_node"]])




    if os.path.isfile(config["ssh_cert"]+".pub"):
        f = open(config["ssh_cert"]+".pub")
        sshkey_public = f.read()
        f.close()

        config["sshkey"] = sshkey_public
    add_ssh_key()

    check_config(config)
    gen_platform_wise_config()

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
    config["nfs_user"] = config["admin_username"]
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

        assert config["priority"] in ["regular", "low"]
        if config["priority"] == "regular":
            config["master_ip"] = utils.getIP(kubernetes_master)
        else:
            config["master_ip"] = config["machines"][kubernetes_master.split(".")[0]]["private-ip"]
        utils.render_template("./template/master/kube-apiserver.yaml","./deploy/master/kube-apiserver.yaml",config)
        utils.render_template("./template/master/dns-kubeconfig.yaml","./deploy/master/dns-kubeconfig.yaml",config)
        utils.render_template("./template/master/kubelet.service","./deploy/master/kubelet.service",config)
        utils.render_template("./template/master/" + config["premasterdeploymentscript"],"./deploy/master/"+config["premasterdeploymentscript"],config)
        utils.render_template("./template/master/" + config["postmasterdeploymentscript"],"./deploy/master/"+config["postmasterdeploymentscript"],config)

        utils.SSH_exec_script(config["ssh_cert"],kubernetes_master_user, kubernetes_master, "./deploy/master/"+config["premasterdeploymentscript"])

        with open("./deploy/master/"+config["masterdeploymentlist"],"r") as f:
            deploy_files = [s.split(",") for s in f.readlines() if len(s.split(",")) == 2]
        for (source, target) in deploy_files:
            if (os.path.isfile(source.strip()) or os.path.exists(source.strip())):
                utils.sudo_scp(config["ssh_cert"],source.strip(),target.strip(),kubernetes_master_user,kubernetes_master, verbose=verbose)

        utils.SSH_exec_script(config["ssh_cert"],kubernetes_master_user, kubernetes_master, "./deploy/master/" + config["postmasterdeploymentscript"])

def get_cni_binary():
    os.system("mkdir -p ./deploy/bin")
    # This tar file contains binary build from https://github.com/containernetworking/cni which used by weave
    copy_from_docker_image(config["dockers"]["container"]["binstore"]["fullname"], "/data/cni/cni-v0.7.1.tgz", "./deploy/bin/cni-v0.7.1.tgz")
    if verbose:
        print "Extracting CNI binaries"
    os.system("tar -zxvf ./deploy/bin/cni-v0.7.1.tgz -C ./deploy/bin")


def get_other_binary():
    os.system("mkdir -p ./deploy/bin/other/easy-rsa/")
    copy_from_docker_image(config["dockers"]["container"]["binstore"]["fullname"], "/data/easy-rsa/v3.0.5.tar.gz", "./deploy/bin/other/easy-rsa/v3.0.5.tar.gz")
    copy_from_docker_image(config["dockers"]["container"]["binstore"]["fullname"], "/data/cfssl/linux/cfssl", "./deploy/bin/other/cfssl")
    copy_from_docker_image(config["dockers"]["container"]["binstore"]["fullname"], "/data/cfssl/linux/cfssljson", "./deploy/bin/other/cfssljson")

def get_kubectl_binary(force = False):
    get_hyperkube_docker(force = force)
    get_cni_binary()
    get_other_binary()

def get_hyperkube_docker(force = False) :
    os.system("mkdir -p ./deploy/bin")
    print( "Use docker container %s" % config["dockers"]["container"]["hyperkube"]["fullname"])
    if force or not os.path.exists("./deploy/bin/hyperkube"):
        copy_from_docker_image(config["dockers"]["container"]["hyperkube"]["fullname"], "/hyperkube", "./deploy/bin/hyperkube")
    if force or not os.path.exists("./deploy/bin/kubelet"):
        copy_from_docker_image(config["dockers"]["container"]["hyperkube"]["fullname"], "/kubelet", "./deploy/bin/kubelet")
    if force or not os.path.exists("./deploy/bin/kubectl"):
        copy_from_docker_image(config["dockers"]["container"]["hyperkube"]["fullname"], "/kubectl", "./deploy/bin/kubectl")
    if config['kube_custom_cri']:
        if force or not os.path.exists("./deploy/bin/crishim"):
            copy_from_docker_image(config["dockers"]["container"]["hyperkube"]["fullname"], "/crishim", "./deploy/bin/crishim")
        if force or not os.path.exists("./deploy/bin/nvidiagpuplugin.so"):
            copy_from_docker_image(config["dockers"]["container"]["hyperkube"]["fullname"], "/nvidiagpuplugin.so", "./deploy/bin/nvidiagpuplugin.so")

def deploy_masters(force = False):
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
    render_service_templates()

    get_kubectl_binary(force)

    for i,kubernetes_master in enumerate(kubernetes_masters):
        deploy_master(kubernetes_master)
    deploycmd = """
        until curl -q http://127.0.0.1:8080/version/ ; do
            sleep 5;
            echo 'waiting for master kubernetes service...';
        done;

        until sudo /opt/bin/kubectl apply -f /opt/addons/kube-addons/weave.yaml --validate=false ; do
            sleep 5;
            echo 'waiting for master kube-addons weave...';
        done ;

        until sudo /opt/bin/kubectl apply -f /opt/addons/kube-addons/dashboard.yaml --validate=false ; do
            sleep 5;
            echo 'waiting for master kube-addons dashboard...';
        done ;

        until sudo /opt/bin/kubectl apply -f /opt/addons/kube-addons/dns-addon.yml --validate=false ;  do
            sleep 5;
            echo 'waiting for master kube-addons dns-addon...';
        done ;

        until sudo /opt/bin/kubectl apply -f /opt/addons/kube-addons/kube-proxy.json --validate=false ;  do
            sleep 5;
            echo 'waiting for master kube-addons kube-proxy.json...';
        done ;

        until sudo /opt/bin/kubectl create -f /etc/kubernetes/clusterroles/ ;  do
            sleep 5;
            echo 'waiting for master kubernetes clusterroles...';
        done ;
        sudo ln -s /opt/bin/kubectl /usr/bin/;
    """
    utils.SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_masters[0], deploycmd , False)


def clean_etcd():
    etcd_servers = config["etcd_node"]
    etcd_server_user = config["etcd_user"]

    for etcd_server_address in etcd_servers:
        print "==============================================="
        print "Clean up etcd servers %s... (It is OK to see 'Errors' in this section)" % etcd_server_address
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
        print "==============================================="
        print "deploy certificates to etcd server %s" % etcd_server_address
        utils.SSH_exec_cmd (config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo mkdir -p /etc/etcd/ssl ; sudo chown %s /etc/etcd/ssl " % (etcd_server_user), showCmd=verbose)
        utils.scp(config["ssh_cert"],"./deploy/ssl/etcd/ca.pem","/etc/etcd/ssl", etcd_server_user, etcd_server_address, verbose=verbose )
        utils.scp(config["ssh_cert"],"./deploy/ssl/etcd/etcd.pem","/etc/etcd/ssl", etcd_server_user, etcd_server_address, verbose=verbose )
        utils.scp(config["ssh_cert"],"./deploy/ssl/etcd/etcd-key.pem","/etc/etcd/ssl", etcd_server_user, etcd_server_address, verbose=verbose )

        print "==============================================="
        print "starting etcd service on %s ..." % etcd_server_address


        config["etcd_node_ip"] = etcd_server_address
        utils.render_template("./template/etcd/docker_etcd_ssl.sh","./deploy/etcd/docker_etcd_ssl.sh",config, verbose=verbose)

        utils.scp(config["ssh_cert"],"./deploy/etcd/docker_etcd_ssl.sh","/home/%s/docker_etcd_ssl.sh" % etcd_server_user, etcd_server_user, etcd_server_address, verbose=verbose )
        utils.SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "chmod +x /home/%s/docker_etcd_ssl.sh ; /home/%s/docker_etcd_ssl.sh" % (etcd_server_user,etcd_server_user), showCmd=verbose)


    print "==============================================="
    print "init etcd service on %s ..."  % etcd_servers[0]


    check_etcd_service()

    utils.scp(config["ssh_cert"],"./deploy/etcd/init_network.sh","/home/%s/init_network.sh" % etcd_server_user, etcd_server_user, etcd_servers[0] )
    utils.SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_servers[0], "chmod +x /home/%s/init_network.sh" % etcd_server_user)
    utils.SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_servers[0], "/home/%s/init_network.sh" % etcd_server_user)


def deploy_ETCD():
    # this condition would not be satisfied at least when deploying new clusters
    if "deploydockerETCD" in config and config["deploydockerETCD"]:
        deploy_ETCD_docker()
        return

    etcd_servers = config["etcd_node"]
    etcd_server_user = config["etcd_user"]

    clean_etcd()

    for i,etcd_server_address in enumerate(etcd_servers):

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

def set_nfs_disk():
    """
    we assume there's only 1 cluster.
    """
    load_platform_type()
    etcd_server_user = config["nfs_user"]
    nfs_servers = config["nfs_node"] if len(config["nfs_node"]) > 0 else config["etcd_node"]
    machine_name_2_full = {nm.split('.')[0]:nm for nm in nfs_servers}
    for srvr_nm, nfs_cnf in config["nfs_disk_mnt"].items():
        nfs_cnf["nfs_client_CIDR"] = config["nfs_client_CIDR"]
        nfs_cnf["platform_type"] = config["platform_type"]
        nfs_server = machine_name_2_full[srvr_nm]
        utils.render_template("./template/nfs/nfs_config.sh.template", "./scripts/setup_nfs_server.sh", nfs_cnf)
        utils.SSH_exec_script( config["ssh_cert"], etcd_server_user, nfs_server, "./scripts/setup_nfs_server.sh")

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
    print("A DL workspace docker is built at: "+ dockername)

def config_ubuntu():
    ubuntuConfig = fetch_config( config, ["ubuntuconfig"] )
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

    print("A DL workspace docker is built at: "+ dockername)


def clean_worker_nodes():
    workerNodes = get_worker_nodes(config["clusterId"], False)
    worker_ssh_user = config["admin_username"]
    for nodeIP in workerNodes:
        print "==============================================="
        print "cleaning worker node: %s ..."  % nodeIP
        utils.SSH_exec_script(config["ssh_cert"], worker_ssh_user, nodeIP, "./deploy/kubelet/%s" % config["workercleanupscript"])


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

def update_scaled_worker_nodes( nargs ):
    utils.render_template_directory("./template/kubelet", "./deploy/kubelet",config)
    write_nodelist_yaml()

    os.system('sed "s/##etcd_endpoints##/%s/" "./deploy/kubelet/options.env.template" > "./deploy/kubelet/options.env"' % config["etcd_endpoints"].replace("/","\\/"))
    os.system('sed "s/##api_servers##/%s/" ./deploy/kubelet/kubelet.service.template > ./deploy/kubelet/kubelet.service' % config["api_servers"].replace("/","\\/"))
    os.system('sed "s/##api_servers##/%s/" ./deploy/kubelet/worker-kubeconfig.yaml.template > ./deploy/kubelet/worker-kubeconfig.yaml' % config["api_servers"].replace("/","\\/"))

    get_hyperkube_docker()

    workerNodes = get_worker_nodes(config["clusterId"], True)
    workerNodes = limit_nodes(workerNodes)
    for node in workerNodes:
        if in_list(node, nargs):
            update_worker_node(node)

    os.system("rm ./deploy/kubelet/options.env")
    os.system("rm ./deploy/kubelet/kubelet.service")
    os.system("rm ./deploy/kubelet/worker-kubeconfig.yaml")

def default_node_type4kubernetes_services():
    servicedic = get_all_services()
    nodetype4service = fetch_config(config, ["kubelabels"])
    if "default" in nodetype4service:
        for service, servicefile in servicedic.iteritems():
            servicename = get_service_name(servicefile)
            if servicename is None or service in nodetype4service or servicename in nodetype4service:
                continue
            nodetype4service[servicename] = nodetype4service["default"]
    return nodetype4service

def service4nodetype(nodetypes, nodetype4service):
    """not including 'all'. if you want it, add it explicitly, e.g., ['worker', 'all']"""
    servicelist = []
    for nodetype in nodetypes:
        for service, type4svc in nodetype4service.items():
          if type4svc == nodetype:
            servicelist += service,
    return servicelist

def render_kubelet_service_by_node_type(nodetype, nodetype4service={}):
    """since this is for cloud init, we only consider the case where we want to label the service as active, and
    we don't consider the overwriting case
    nodetypes should be a kind of nodetype, e.g., 'worker',
    nodetype4service is a dict if specified to overwrite the default dict"""
    temp_keys = ['labels']
    for ky in temp_keys:
        config.pop(ky, None)
    if nodetype in ['worker', 'etcd']:
        nodetype += '_node'
    assert (nodetype in ['worker_node', 'etcd_node'] or (nodetype[:10] == 'etcd_node_' and nodetype[10:].isdigit()))  and \
    'invalid nodetype'
    nd_type4svc = default_node_type4kubernetes_services()
    # overwrite if specified
    for svc in nodetype4service:
        nd_type4svc[svc] = nodetype4service[svc]
    # tried to get rid of this but failed. this doesn't work: https://docs.ansible.com/ansible/latest/user_guide/playbooks_filters.html#regular-expression-filters
    config['labels'] = ["{}=active".format(svc) for svc in service4nodetype([nodetype, 'all'], nd_type4svc)]
    utils.render_template("template/cloud-config/cloudinit.kubelet.service.template",
        "./deploy/cloud-config/{}.kubelet.service".format(nodetype), config)
    for ky in temp_keys:
        config.pop(ky)

def render_mount_script():
    os.system('rm -f deploy/cloud-config/fileshare_install.sh')
    os.system('rm -f deploy/cloud-config/mnt_fs_svc.sh')
    fileshare_install('deploy/cloud-config/fileshare_install.sh')
    allmountpoints = mount_fileshares_by_service(True, 'deploy/cloud-config/mnt_fs_svc.sh')

def render_and_pack_worker_cloud_init_files():
    role = 'worker_node'
    os.system('rm -rf worker_cld_init; mkdir -p worker_cld_init')
    utils.render_template_directory("./template/kubelet", "./deploy/kubelet", config)
    utils.render_template("template/cloud-config/cloud_init_worker.txt.template", "./scripts/cloud_init_worker.txt", config)
    config['role'] = role
    utils.render_template("template/cloud-config/cloudinit.upgrade.list",
        "./deploy/cloud-config/cloudinit.{}.upgrade.list".format(role), config)
    render_kubelet_service_by_node_type('worker_node')
    # write_nodelist_yaml() TODO verify whether this step is necessary
    os.system('sed "s/##etcd_endpoints##/%s/" "./deploy/kubelet/options.env.template" > "./deploy/kubelet/options.env"'
        % config["etcd_endpoints"].replace("/","\\/"))
    os.system('sed "s/##api_servers##/%s/" ./deploy/kubelet/worker-kubeconfig.yaml.template > ./deploy/kubelet/worker-kubeconfig.yaml'
        % config["api_servers"].replace("/","\\/"))
    get_hyperkube_docker()
    render_mount_script()
    with open("./deploy/cloud-config/cloudinit.{}.upgrade.list".format(role),"r") as f:
        deploy_files = [s.split(",") for s in f.readlines() if len(s.split(",")) == 2]
    with open("worker_cld_init/filemap", "w") as wf:
        for (source, target) in deploy_files:
            src_strip, tgt_strip = source.strip(), target.strip()
            if os.path.exists(src_strip):
                fbn = os.path.basename(src_strip)
                os.system('cp {} worker_cld_init/{}'.format(src_strip, fbn))
                wf.write("{},{}\n".format(fbn, tgt_strip))

    files2cp = [ "./deploy/kubelet/%s" % config["preworkerdeploymentscript"], "./deploy/kubelet/%s" % config["postworkerdeploymentscript"],
                "./scripts/cloud_init_worker.sh", "./scripts/mkdir_and_cp.sh", "./scripts/prepare_vm_disk.sh", "./scripts/prepare_ubuntu.sh",
                "./scripts/disable_kernel_auto_updates.sh", "./scripts/docker_network_gc_setup.sh", "./scripts/dns.sh",
                "deploy/cloud-config/fileshare_install.sh", "deploy/cloud-config/mnt_fs_svc.sh", "scripts/lnk_fs.sh"]
    for fn in files2cp:
        os.system('cp {} worker_cld_init/{}'.format(fn, os.path.basename(fn)))

    os.system("tar -cvf worker_cld_init.tar worker_cld_init;")

    # TODO we want to upload to infra node, use a service in a container to serve workers requesting this package.
    os.system("rm ./deploy/kubelet/options.env")
    os.system("rm ./deploy/kubelet/worker-kubeconfig.yaml")

def update_worker_nodes( nargs ):
    utils.render_template_directory("./template/kubelet", "./deploy/kubelet",config)
    write_nodelist_yaml()

    os.system('sed "s/##etcd_endpoints##/%s/" "./deploy/kubelet/options.env.template" > "./deploy/kubelet/options.env"' % config["etcd_endpoints"].replace("/","\\/"))
    os.system('sed "s/##api_servers##/%s/" ./deploy/kubelet/kubelet.service.template > ./deploy/kubelet/kubelet.service' % config["api_servers"].replace("/","\\/"))
    os.system('sed "s/##api_servers##/%s/" ./deploy/kubelet/worker-kubeconfig.yaml.template > ./deploy/kubelet/worker-kubeconfig.yaml' % config["api_servers"].replace("/","\\/"))

    get_hyperkube_docker()

    workerNodes = get_worker_nodes(config["clusterId"], False)
    workerNodes = limit_nodes(workerNodes)
    for node in workerNodes:
        if in_list(node, nargs):
            update_worker_node(node)

    os.system("rm ./deploy/kubelet/options.env")
    os.system("rm ./deploy/kubelet/kubelet.service")
    os.system("rm ./deploy/kubelet/worker-kubeconfig.yaml")

def update_worker_nodes_in_parallel(nargs):
    # TODO: Merge with update_worker_nodes
    utils.render_template_directory("./template/kubelet", "./deploy/kubelet", config)
    write_nodelist_yaml()

    os.system('sed "s/##etcd_endpoints##/%s/" "./deploy/kubelet/options.env.template" > "./deploy/kubelet/options.env"' % config["etcd_endpoints"].replace("/","\\/"))
    os.system('sed "s/##api_servers##/%s/" ./deploy/kubelet/kubelet.service.template > ./deploy/kubelet/kubelet.service' % config["api_servers"].replace("/","\\/"))
    os.system('sed "s/##api_servers##/%s/" ./deploy/kubelet/worker-kubeconfig.yaml.template > ./deploy/kubelet/worker-kubeconfig.yaml' % config["api_servers"].replace("/","\\/"))

    get_hyperkube_docker()

    workerNodes = get_worker_nodes(config["clusterId"], False)
    workerNodes = limit_nodes(workerNodes)
    worker_nodes_to_update = [node for node in workerNodes if in_list(node, nargs)]

    # TODO: Tolerate faults
    from multiprocessing import Pool
    pool = Pool(processes=len(worker_nodes_to_update))
    pool.map(update_worker_node, worker_nodes_to_update)
    pool.close()

    os.system("rm ./deploy/kubelet/options.env")
    os.system("rm ./deploy/kubelet/kubelet.service")
    os.system("rm ./deploy/kubelet/worker-kubeconfig.yaml")


def reset_worker_nodes():
    utils.render_template_directory("./template/kubelet", "./deploy/kubelet",config)
    workerNodes = get_worker_nodes(config["clusterId"], False)
    workerNodes = limit_nodes(workerNodes)
    for node in workerNodes:
        reset_worker_node(node)


def update_nfs_nodes(nargs):
    """Internally use update_worker_node.

    TODO: Should be covered by update_role_nodes in deploy.py V2
    """
    # This is to temporarily replace gpu_type with None to disallow nvidia runtime config to appear in /etc/docker/daemon.json
    prev_gpu_type = config["gpu_type"]
    config["gpu_type"] = "None"
    utils.render_template_directory("./template/kubelet", "./deploy/kubelet", config)
    config["gpu_type"] = prev_gpu_type

    write_nodelist_yaml()

    os.system('sed "s/##etcd_endpoints##/%s/" "./deploy/kubelet/options.env.template" > "./deploy/kubelet/options.env"' % config["etcd_endpoints"].replace("/","\\/"))
    os.system('sed "s/##api_servers##/%s/" ./deploy/kubelet/kubelet.service.template > ./deploy/kubelet/kubelet.service' % config["api_servers"].replace("/","\\/"))
    os.system('sed "s/##api_servers##/%s/" ./deploy/kubelet/worker-kubeconfig.yaml.template > ./deploy/kubelet/worker-kubeconfig.yaml' % config["api_servers"].replace("/","\\/"))

    get_hyperkube_docker()

    nfs_nodes = get_nodes_by_roles(["nfs"])
    nfs_nodes = limit_nodes(nfs_nodes)
    for node in nfs_nodes:
        if in_list(node, nargs):
            update_worker_node(node)

    os.system("rm ./deploy/kubelet/options.env")
    os.system("rm ./deploy/kubelet/kubelet.service")
    os.system("rm ./deploy/kubelet/worker-kubeconfig.yaml")


def update_mysqlserver_nodes(nargs):
    """Internally use update_worker_node.

    TODO: Should be covered by update_role_nodes in deploy.py V2
    """
    # This is to temporarily replace gpu_type with None to disallow nvidia runtime config to appear in /etc/docker/daemon.json
    prev_gpu_type = config["gpu_type"]
    config["gpu_type"] = "None"
    utils.render_template_directory("./template/kubelet", "./deploy/kubelet", config)
    config["gpu_type"] = prev_gpu_type

    write_nodelist_yaml()

    os.system('sed "s/##etcd_endpoints##/%s/" "./deploy/kubelet/options.env.template" > "./deploy/kubelet/options.env"' % config["etcd_endpoints"].replace("/", "\\/"))
    os.system('sed "s/##api_servers##/%s/" ./deploy/kubelet/kubelet.service.template > ./deploy/kubelet/kubelet.service' % config["api_servers"].replace("/", "\\/"))
    os.system('sed "s/##api_servers##/%s/" ./deploy/kubelet/worker-kubeconfig.yaml.template > ./deploy/kubelet/worker-kubeconfig.yaml' % config["api_servers"].replace("/", "\\/"))

    get_hyperkube_docker()

    mysqlserver_nodes = get_nodes_by_roles(["mysqlserver"])
    mysqlserver_nodes = limit_nodes(mysqlserver_nodes)
    for node in mysqlserver_nodes:
        if in_list(node, nargs):
            update_worker_node(node)

    os.system("rm ./deploy/kubelet/options.env")
    os.system("rm ./deploy/kubelet/kubelet.service")
    os.system("rm ./deploy/kubelet/worker-kubeconfig.yaml")


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
        utils.SSH_exec_cmd(config["ssh_cert"], config["admin_username"], masterIP, "sudo chown -R %s /etc/kubernetes" % config["admin_username"])
        utils.SSH_exec_cmd(config["ssh_cert"], config["admin_username"], masterIP, "sudo cp /etc/kubernetes/certs/client.crt /etc/kubernetes/ssl/apiserver.pem")
        utils.SSH_exec_cmd(config["ssh_cert"], config["admin_username"], masterIP, "sudo cp /etc/kubernetes/certs/client.key /etc/kubernetes/ssl/apiserver-key.pem")
        utils.SSH_exec_cmd(config["ssh_cert"], config["admin_username"], masterIP, "sudo cp /etc/kubernetes/certs/ca.crt /etc/kubernetes/ssl/ca.pem")
        utils.SSH_exec_cmd(config["ssh_cert"], config["admin_username"], masterIP, "sudo cp /home/%s/.kube/config /etc/kubernetes/restapi-kubeconfig.yaml" % config["admin_username"])

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

    utils.render_template_directory("./template/WebUI","./deploy/WebUI", config)
    os.system("cp --verbose ./deploy/WebUI/*.json ../WebUI/dotnet/WebPortal/") # used for debugging, when deploy, it will be overwritten by mount from host, contains secret

    # write into host, mounted into container
    utils.sudo_scp(config["ssh_cert"],"./deploy/WebUI/userconfig.json","/etc/WebUI/userconfig.json", sshUser, webUIIP )
    utils.sudo_scp(config["ssh_cert"],"./deploy/WebUI/configAuth.json","/etc/WebUI/configAuth.json", sshUser, webUIIP )

    # write report configuration
    masternodes = get_ETCD_master_nodes(config["clusterId"])
    if ( "servers" not in config["Dashboards"]["influxDB"]):
        config["Dashboards"]["influxDB"]["servers"] = masternodes[0]
    if ( "servers" not in config["Dashboards"]["grafana"]):
        config["Dashboards"]["grafana"]["servers"] = masternodes[0]

    config["grafana_endpoint"] = "http://%s:%s" % (config["Dashboards"]["grafana"]["servers"], config["Dashboards"]["grafana"]["port"])
    config["prometheus_endpoint"] = "http://%s:%s" % (config["prometheus"]["host"], config["prometheus"]["port"])



    reportConfig = config["Dashboards"]
    reportConfig["kuberneteAPI"] = {}
    reportConfig["kuberneteAPI"]["port"] = config["k8sAPIport"]
    reportConfig["kuberneteAPI"]["servers"] = masternodes
    reportConfig["kuberneteAPI"]["https"] = True

    with open("./deploy/WebUI/dashboardConfig.json","w") as fp:
        json.dump(reportConfig, fp)
    os.system("cp --verbose ./deploy/WebUI/dashboardConfig.json ../WebUI/dotnet/WebPortal/")
    # write into host, mounted into container
    utils.sudo_scp(config["ssh_cert"],"./deploy/WebUI/dashboardConfig.json","/etc/WebUI/dashboardConfig.json", sshUser, webUIIP )

    utils.render_template("./template/WebUI/Master-Templates.json", "./deploy/WebUI/Master-Templates.json", config)
    os.system("cp --verbose ./deploy/WebUI/Master-Templates.json ../WebUI/dotnet/WebPortal/Master-Templates.json")
    utils.sudo_scp(config["ssh_cert"],"./deploy/WebUI/Master-Templates.json","/etc/WebUI/Master-Templates.json", sshUser, webUIIP )



    utils.render_template_directory("./template/RestfulAPI", "./deploy/RestfulAPI",config)
    utils.sudo_scp(config["ssh_cert"],"./deploy/RestfulAPI/config.yaml","/etc/RestfulAPI/config.yaml", sshUser, webUIIP )

    utils.render_template_directory("./template/dashboard", "./deploy/dashboard",config)
    utils.sudo_scp(config["ssh_cert"],"./deploy/dashboard/production.yaml","/etc/dashboard/production.yaml", sshUser, webUIIP )

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
    if verbose:
        print "Copy file {0} to node {1} as file {2}".format(source, node, target)
    utils.sudo_scp(config["ssh_cert"], source, target, config["admin_username"], node)

# copy list of files to a node
def copy_list_of_files(listOfFiles, node):
    with open(listOfFiles, "r") as f:
        copy_files = [s.split(",") for s in f.readlines() if len(s.split(",")) == 2]
    for (source, target) in copy_files:
        if (os.path.isfile(source.strip()) or os.path.exists(source.strip())):
            rmt_cp(node, source.strip(), target.strip())

def copy_list_of_files_to_nodes(listOfFiles, nodes):
    with open(listOfFiles, "r") as f:
        copy_files = [s.split(",") for s in f.readlines() if len(s.split(",")) == 2]
    for node in nodes:
        for (source, target) in copy_files:
            if (os.path.isfile(source.strip()) or os.path.exists(source.strip())):
                rmt_cp(node, source.strip(), target.strip())

# run scripts
def run_script_on_node(script, node):
    if verbose:
        print "Running script {0} on node {1}".format(script, node)
    utils.SSH_exec_script(config["ssh_cert"], config["admin_username"], node, script)

def run_script_on_nodes(script, nodes):
    for node in nodes:
        if verbose:
            print "Running script {0} on node {1}".format(script, node)
        utils.SSH_exec_script(config["ssh_cert"], config["admin_username"], node, script)

# deployment
def deploy_on_nodes(prescript, listOfFiles, postscript, nodes):
    run_script_on_nodes(prescript, nodes)
    copy_list_of_files_to_nodes(listOfFiles, nodes)
    run_script_on_nodes(postscript, nodes)

# addons
def kube_master0_wait():
    get_ETCD_master_nodes(config["clusterId"])
    node = config["kubernetes_master_node"][0]
    exec_rmt_cmd(node, "until curl -q http://127.0.0.1:8080/version/ ; do sleep 5; echo 'waiting for master...'; done")
    return node

def kube_deploy_addons():
    node = kube_master0_wait()
    for addon in config["kube_addons"]:
        exec_rmt_cmd(node, "sudo kubectl create -f "+addon)

# config changes
def kube_deploy_configchanges():
    node = kube_master0_wait()
    for configChange in config["kube_configchanges"]:
        exec_rmt_cmd(node, "sudo kubectl apply -f "+configChange)

def acs_deploy_addons():
    kube_deploy_configchanges()
    kube_deploy_addons()

def acs_label_webui():
    for n in config["kubernetes_master_node"]:
        nodeName = kubernetes_get_node_name(n)
        if verbose:
            print "Label node: "+nodeName
        label_webUI(nodeName)

def acs_untaint_nodes():
    for n in config["kubernetes_master_node"]:
        nodeName = kubernetes_get_node_name(n)
        if verbose:
            print "Untaint node: "+nodeName
        run_kubectl(["taint nodes {0} node-role.kubernetes.io/master-".format(nodeName)])

# other config post deploy -- ACS cluster is complete
# Run prescript, copyfiles, postscript
def acs_post_deploy():
    # set nodes
    get_nodes(config["clusterId"])
    # Label nodes
    acs_label_webui()
    kubernetes_label_nodes("active", [], args.yes)


    # Untaint the master nodes
    acs_untaint_nodes()

    # Copy files, etc.
    gen_configs()
    utils.render_template_directory("./template/kubelet", "./deploy/kubelet", config)
    write_nodelist_yaml()
    # get CNI binary
    get_cni_binary()
    # deploy
    deploy_on_nodes(config["master_predeploy"], config["master_filesdeploy"], config["master_postdeploy"],
                    config["kubernetes_master_node"])
    deploy_on_nodes(config["worker_predeploy"], config["worker_filesdeploy"], config["worker_postdeploy"],
                    config["worker_node"])

# Install needed components including GPU drivers if needed
def acs_prepare_machines():
    nodes = get_nodes(config["clusterId"])
    for node in nodes:
        run_script(node, ["./scripts/prepare_ubuntu.sh"], True)
        # restart kubelet incase GPU installed
        utils.SSH_exec_cmd(config["ssh_cert"], config["admin_username"], node, "sudo systemctl restart kubelet.service")

def acs_get_jobendpt(jobId):
    addr = k8sUtils.GetServiceAddress(jobId)
    acs_tools.acs_set_desired_dns(addr[0]['hostName'])
    ip = config["acs_node_info"]["desiredDns"]
    port = addr[0]['hostPort']
    ret = "http://%s:%s" % (ip, port)
    print ret

def get_jobendpt(jobId):
    k8sconfig["kubelet-path"] = "./deploy/bin/kubectl --server=https://%s:%s --certificate-authority=%s --client-key=%s --client-certificate=%s" % (config["kubernetes_master_node"][0], config["k8sAPIport"], "./deploy/ssl/ca/ca.pem", "./deploy/ssl/kubelet/apiserver-key.pem", "./deploy/ssl/kubelet/apiserver.pem")
    addr = k8sUtils.GetServiceAddress(jobId)
    get_ETCD_master_nodes(config["clusterId"])
    return "http://{0}:{1}".format(config["kubernetes_master_node"][0], addr[0]["hostPort"])

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
                    raise ValueError(errorMsg)
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
            if "curphysicalmountpoint" not in v:
                v["curphysicalmountpoint"] = curphysicalmountpoint
            else:
                curphysicalmountpoint = v["curphysicalmountpoint"]
            bMount = False
            errorMsg = None
            if v["type"] == "azurefileshare":
                if "accountname" in v and "filesharename" in v and "accesskey" in v:
                    allmountpoints[k] = copy.deepcopy( v )
                    bMount = True
                    allmountpoints[k]["url"] = "//" + allmountpoints[k]["accountname"] + ".file.core.windows.net/"+allmountpoints[k]["filesharename"]
                    options = fetch_config(config, ["mountconfig", "azurefileshare", "options"]) % (v["accountname"], v["accesskey"])
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
                    options = fetch_config(config, ["mountconfig", "glusterfs", "options"])
                    allmountpoints[k]["options"] = options
                    fstab += "%s:/%s %s glusterfs %s 0 0\n" % (allmountpoints[k]["node"], v["filesharename"], curphysicalmountpoint, options)
                else:
                    errorMsg = "glusterfs fileshare %s, there is no filesharename parameter" % (k)
            elif v["type"] == "nfs" and "server" in v:
                if "filesharename" in v and "server" in v:
                    allmountpoints[k] = copy.deepcopy( v )
                    bMount = True
                    options = fetch_config(config, ["mountconfig", "nfs", "options"])
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
                options = fetch_config(config, ["mountconfig", "hdfs", "options"])
                allmountpoints[k]["options"] = options
                fstaboptions = fetch_config(config, ["mountconfig", "hdfs", "fstaboptions"])
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
                usefstab =     fstabcontent + fstab
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

def fileshare_install(mount_command_file=''):
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
        if isInstallOnCoreOS():
            for k,v in allmountpoints.iteritems():
                if "curphysicalmountpoint" in v:
                    physicalmountpoint = v["curphysicalmountpoint"]
                    if v["type"] in config["mountsupportedbycoreos"]:
                        ()
                    else:
                        print "Share %s: type %s is not supported in CoreOS, mount failed " % (k, v["type"] )
                        exit(1)
        else:
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
            if mount_command_file == '':
                utils.SSH_exec_cmd(config["ssh_cert"], config["admin_username"], node, remotecmd)
            else:
                with open(mount_command_file, 'w') as wf:
                    wf.write(remotecmd)
                break

def config_fqdn():
    all_nodes = get_nodes(config["clusterId"])
    for node in all_nodes:
        remotecmd = "echo %s | sudo tee /etc/hostname-fqdn; sudo chmod +r /etc/hostname-fqdn" % node
        utils.SSH_exec_cmd(config["ssh_cert"], config["admin_username"], node, remotecmd)

def config_nginx():
    all_nodes = get_nodes(config["clusterId"])
    template_dir = "services/nginx/"
    target_dir = "deploy/services/nginx/"
    utils.render_template_directory(template_dir, target_dir,config)
    for node in all_nodes:
        utils.sudo_scp(config["ssh_cert"],"./deploy/services/nginx/","/etc/nginx/conf.other", config["admin_username"], node )
    # See https://github.com/kubernetes/examples/blob/master/staging/https-nginx/README.md

def mount_fileshares_by_service(perform_mount=True, mount_command_file=''):
    all_nodes = get_nodes(config["clusterId"])
    if perform_mount:
        nodes = all_nodes
        for node in nodes:
            allmountpoints, fstab = get_mount_fileshares(node)
            remotecmd = "sudo mkdir -p %s; " % config["folder_auto_share"] #''
            remotecmd += "sudo mkdir -p %s; " % config["storage-mount-path"]
            remotecmd += "sudo mkdir -p %s; " % config["physical-mount-path"]
            mountconfig = { }
            mountconfig["mountpoints"] = allmountpoints
            mountconfig["storage-mount-path"] = config["storage-mount-path"]
            mountconfig["dltsdata-storage-mount-path"] = config["dltsdata-storage-mount-path"]
            mountconfig["physical-mount-path"] = config["physical-mount-path"]
            for k,v in allmountpoints.iteritems():
                if "curphysicalmountpoint" in v:
                    remotecmd += "sudo mkdir -p %s; " % v["curphysicalmountpoint"]
            utils.render_template_directory("./template/storage/auto_share", "./deploy/storage/auto_share", config)
            with open("./deploy/storage/auto_share/mounting.yaml",'w') as datafile:
                yaml.dump(mountconfig, datafile, default_flow_style=False)
            remotecmd += "sudo systemctl stop auto_share.timer; "
            if len(remotecmd)>0:
                if mount_command_file == '':
                    utils.SSH_exec_cmd(config["ssh_cert"], config["admin_username"], node, remotecmd)
                    remotecmd = ""
            # copy the files & binaries to remote nodes
            utils.sudo_scp( config["ssh_cert"], "./deploy/storage/auto_share/auto_share.timer","/etc/systemd/system/auto_share.timer", config["admin_username"], node )
            utils.sudo_scp( config["ssh_cert"], "./deploy/storage/auto_share/auto_share.target","/etc/systemd/system/auto_share.target", config["admin_username"], node )
            utils.sudo_scp( config["ssh_cert"], "./deploy/storage/auto_share/auto_share.service","/etc/systemd/system/auto_share.service", config["admin_username"], node )
            utils.sudo_scp( config["ssh_cert"], "./deploy/storage/auto_share/logging.yaml",os.path.join(config["folder_auto_share"], "logging.yaml"), config["admin_username"], node )
            utils.sudo_scp( config["ssh_cert"], "./deploy/storage/auto_share/auto_share.py",os.path.join(config["folder_auto_share"], "auto_share.py"), config["admin_username"], node )
            utils.sudo_scp( config["ssh_cert"], "./template/storage/auto_share/glusterfs.mount",os.path.join(config["folder_auto_share"], "glusterfs.mount"), config["admin_username"], node )
            utils.sudo_scp( config["ssh_cert"], "./deploy/storage/auto_share/mounting.yaml",os.path.join(config["folder_auto_share"], "mounting.yaml"), config["admin_username"], node )
            remotecmd += "sudo chmod +x %s; " % os.path.join(config["folder_auto_share"], "auto_share.py")
            if isInstallOnCoreOS():
                # CoreOS, python has to be installed to /opt/bin
                remotecmd += "sudo sed -i 's/\/usr\/bin/\/opt\/bin/g' %s; " % os.path.join(config["folder_auto_share"], "auto_share.py")
            remotecmd += "sudo " + os.path.join(config["folder_auto_share"], "auto_share.py") + "; " # run it once now
            remotecmd += "sudo systemctl daemon-reload; "
            remotecmd += "sudo systemctl enable auto_share.timer; "
            remotecmd += "sudo systemctl restart auto_share.timer; "
            if len(remotecmd)>0:
                if mount_command_file == '':
                    utils.SSH_exec_cmd(config["ssh_cert"], config["admin_username"], node, remotecmd)
                else:
                    with open(mount_command_file, 'w') as wf:
                        wf.write(remotecmd)
                        break
            # We no longer recommend to insert fstabl into /etc/fstab file, instead,
            # we recommend to use service to start auto mount if needed
            # insert_fstab_section( node, "DLWS", fstab )
    for k, v in allmountpoints.iteritems():
        allmountpoints[k].pop("accesskey", None)
    return allmountpoints

def unmount_fileshares_by_service(clean=False):
    all_nodes = get_nodes(config["clusterId"])
    allmountpoints, fstab = get_mount_fileshares()
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
        remotecmd += "sudo mkdir -p %s; " % config["storage-mount-path"]
        exec_rmt_cmd(node, remotecmd)

def link_fileshares(allmountpoints, bForce=False, mount_command_file=''):
    all_nodes = get_nodes(config["clusterId"])
    if True:
        nodes = all_nodes
        firstdirs = {}
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

            if mount_command_file == '':
                output = utils.SSH_exec_cmd_with_output(config["ssh_cert"], config["admin_username"], node, "sudo mount")
            else:
                remotecmd += "sudo mount;"
            for k,v in allmountpoints.iteritems():
                if "mountpoints" in v and v["type"]!="emptyDir":
                    if mount_command_file == '' and output.find(v["curphysicalmountpoint"]) < 0:
                        print "!!!Warning!!! %s has not been mounted at %s " % (k, v["curphysicalmountpoint"])
                    else:
                        for basename in v["mountpoints"]:
                            dirname = os.path.join(v["curphysicalmountpoint"], basename )
                            remotecmd += "sudo mkdir -p %s; " % dirname
                            remotecmd += "sudo chmod ugo+rwx %s; " %dirname
                    for basename in v["mountpoints"]:
                        dirname = os.path.join(v["curphysicalmountpoint"], basename )
                        storage_mount_path = config["storage-mount-path"]

                        if ("vc" in v) and (v["vc"] != ""):
                            storage_mount_path = os.path.join(config["dltsdata-storage-mount-path"], v["vc"])
                            remotecmd += "sudo mkdir -p %s; " % storage_mount_path

                        linkdir = os.path.join(storage_mount_path, basename)
                        remotecmd += "if [ ! -e %s ]; then sudo ln -s %s %s; fi; " % (linkdir, dirname, linkdir)
            # following node need not make the directory
            if len(remotecmd)>0:
                if mount_command_file == '':
                    utils.SSH_exec_cmd(config["ssh_cert"], config["admin_username"], node, remotecmd)
                else:
                    with open(mount_command_file, 'w') as wf:
                        wf.write(remotecmd)
                    break

def deploy_webUI():
    masterIP = config["kubernetes_master_node"][0]
    deploy_restful_API_on_node(masterIP)
    deploy_webUI_on_node(masterIP)


def deploy_nfs_config():
    nfs_nodes = get_nodes_by_roles(["nfs"])
    for node in nfs_nodes:
        utils.clean_rendered_target_directory()
        config["cur_nfs_node"] = node.split(".")[0]
        utils.render_template_directory("./template/StorageManager", "./deploy/StorageManager", config)
        utils.sudo_scp(config["ssh_cert"], "./deploy/StorageManager/config.yaml", "/etc/StorageManager/config.yaml", config["admin_username"], node)
        del config["cur_nfs_node"]


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
    drives = prog.search( output )
    drivesInfo = prog.split( output )
    ndrives = len(drivesInfo)/2

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
        if not (prog.match(drivename) is None):
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
    for i in range(npart):
        if partitionConfig[i] < 0.0:
            if capacity > 0.0:
                partitionSize[i] = min( capacity, -partitionConfig[i])
                capacity -= partitionSize[i]
            else:
                partitionSize[i] = 0.0
        else:
            sumProportion += partitionConfig[i]
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
                removedPartitions.sort(reverse=True)
                for part in removedPartitions:
                    cmd += "sudo parted -s " + deviceinfo["name"] + " rm " + str(part) + "; "
            partitionSize = calculate_partitions( deviceinfo["capacity"], partitionConfig)
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
    regmatch = re.compile(regexp)
    return regmatch

def find_matched_volume( alldeviceinfo, regmatch ):
    deviceList = {}
    for bdevice in alldeviceinfo:
        deviceinfo = alldeviceinfo[bdevice]
        for part in deviceinfo["parted"]:
            bdevicename = deviceinfo["name"] + str(part)
            match = regmatch.search(bdevicename)
            if not ( match is None ):
                deviceList[match.group(0)] = deviceinfo["parted"][part]
    return deviceList

# Form a configuration file for operation of glusterfs
def write_glusterFS_configuration( nodesinfo, glusterFSargs ):
    config_file = fetch_config_and_check( config, ["glusterFS", "glustefs_nodes_yaml" ])
    config_glusterFS = fetch_config_and_check( config, ["glusterFS"] )
    glusterfs_volumes_config = fetch_dictionary( config_glusterFS, ["gluster_volumes"] )
    required_param = fetch_dictionary( config_glusterFS, ["gluster_volumes_required_param"] )
    config_glusterFS["groups"] = {}
    glusterfs_groups = config_glusterFS["groups"]
    for node in nodesinfo:
        node_basename = kubernetes_get_node_name( node )
        node_config = fetch_config( config, ["machine", node_basename ] )
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
        config_template = yaml.load(config_template_file, Loader=yaml.FullLoader)
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
                remotecmd += "sudo %s %s; " % ( fetch_config( config, ["localdisk", "mkfscmd"]), volume)
        hdfsconfig = {}
        for volume in volumes:
            # mount remote volumes.
            mountpoint = config["hdfs"]["datadir"][volume]
            remotecmd += "sudo mkdir -p %s; " % mountpoint
            remotecmd += "sudo mount %s %s; " % ( volume, mountpoint )
        utils.SSH_exec_cmd( config["ssh_cert"], config["admin_username"], node, remotecmd, showCmd=verbose )
        fstabcontent = "%s %s %s" %( volume, mountpoint, fetch_config( config, ["localdisk", "mountoptions"]))
        insert_fstab_section( node, "MOUNTLOCALDISK", fstabcontent )

def unmount_partition_volume( nodes, deviceSelect ):
    nodesinfo = get_partitions(nodes, deviceSelect )
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
    if "hdfs" in config:
        config["hdfs"]["containermounts"] = {}
        if "datadir" in config["hdfs"]:
            for (k,v) in config["hdfs"]["datadir"].iteritems():
                volumename = k[1:].replace("/","-")
                config["hdfs"]["containermounts"][volumename] = v
    else:
        config["hdfs"] = { }
        config["hdfs"]["containermounts"] = { }

def generate_hdfs_config( nodes, deviceSelect):
    generate_hdfs_containermounts()
    hdfsconfig = copy.deepcopy( config["hdfsconfig"] )
    hdfsconfig["hdfs_cluster_name"] = config["hdfs_cluster_name"]
    zknodes = get_node_lists_for_service("zookeeper")
    zknodelist = generate_hdfs_nodelist( zknodes, fetch_config( config, ["hdfsconfig", "zks", "port"]), ",")
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
    journalnodelist = generate_hdfs_nodelist( journalnodes, fetch_config( config, ["hdfsconfig", "journalnode", "port"]), ";")
    hdfsconfig["journalnode"]["nodes"] = journalnodelist
    config["hdfsconfig"]["namenode"] = hdfsconfig["namenode"]
    return hdfsconfig

# Write configuration for each hdfs node.
def hdfs_config( nodes, deviceSelect):
    hdfsconfig = generate_hdfs_config( nodes, deviceSelect )
    if verbose:
        print "HDFS Configuration: %s " % hdfsconfig
    nodesinfo = get_partitions(nodes, deviceSelect )
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
    for node in nodesinfo:
        alldeviceinfo = nodesinfo[node]
        volumes = find_matched_volume( alldeviceinfo, regmatch )
        print "................. Node %s ................." % node
        remotecmd = ""
        remotecmd += "sudo modprobe dm_thin_pool; "
        remotecmd += "sudo apt-get install -y thin-provisioning-tools; "
        capacityGB = 0.0
        for volume in volumes:
            remotecmd += "sudo pvcreate -f "
            dataalignment = fetch_config( config, ["glusterFS", "dataalignment"] )
            if not dataalignment is None:
                remotecmd += " --dataalignment " + dataalignment
            remotecmd += " " + volume + "; "
            capacityGB += volumes[volume]
        if len(volumes)>0:
            remotecmd += "sudo vgcreate "
            physicalextentsize = fetch_config( config, ["glusterFS", "physicalextentsize"] )
            if not physicalextentsize is None:
                remotecmd += " --physicalextentsize " + physicalextentsize;
            volumegroup = fetch_config_and_check( config, ["glusterFS", "volumegroup" ] )
            remotecmd += " " + volumegroup
            for volume in volumes:
                remotecmd += " " + volume;
            remotecmd += "; "
        else:
            # The machine doesn't have any data disk, skip glusterFS setup
            break;
        volumesize = fetch_config_and_check( config, ["glusterFS", "volumesize" ] )
        metasize = fetch_config_and_check(config, ["glusterFS", "metasize" ] )
        metapoolname = fetch_config_and_check(config, ["glusterFS", "metapoolname" ] )
        # create metapool
        remotecmd += "sudo lvcreate -L %s --name %s %s ; " % ( metasize, metapoolname, volumegroup )
        # create datapool
        volumesize = fetch_config_and_check( config, ["glusterFS", "volumesize" ] )
        datapoolname = fetch_config_and_check( config, ["glusterFS", "datapoolname" ] )
        remotecmd += "sudo lvcreate -l %s --name %s %s ; " % ( volumesize, datapoolname, volumegroup )
        chunksize = fetch_config_and_check( config, ["glusterFS", "chunksize" ] )
        remotecmd += "sudo lvconvert -y --chunksize %s --thinpool %s/%s --poolmetadata %s/%s ; " % ( chunksize, volumegroup, datapoolname, volumegroup, metapoolname )
        remotecmd += "sudo lvchange -y --zero n %s/%s; " %( volumegroup, datapoolname )
        volumename = fetch_config_and_check( config, ["glusterFS", "volumename" ] )
        remotecmd += "sudo lvcreate -y -V %dG -T %s/%s -n %s ;" %( int(capacityGB), volumegroup, datapoolname, volumename )
        mkfsoptions = fetch_config_and_check( config, ["glusterFS", "mkfs.xfs.options" ] )
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
            volumegroup = fetch_config_and_check( config, ["glusterFS", "volumegroup" ] )
            datapoolname = fetch_config_and_check( config, ["glusterFS", "datapoolname" ] )
            volumename = fetch_config_and_check( config, ["glusterFS", "volumename" ] )
            remotecmd += "sudo lvremove -y %s/%s ; " % ( volumegroup, volumename )
            remotecmd += "sudo lvremove -y %s/%s ; " % ( volumegroup, datapoolname )
            remotecmd += "sudo vgremove -y %s ; " % volumegroup
        else:
            # The machine doesn't have any data disk, skip glusterFS removal
            break;
        for volume in volumes:
            remotecmd += "sudo pvremove -y %s; " % volume
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

def exec_on_rand_master(args, supressWarning = False):
    nodes = get_ETCD_master_nodes(config["clusterId"])
    master_node = random.choice(nodes)
    exec_on_all_with_output([master_node], args, supressWarning)

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


def run_script_wrapper(arg_tuple):
    node, args, sudo, supressWarning = arg_tuple
    run_script(node, args, sudo, supressWarning)


# run a shell script on all remote nodes
def run_script_on_all(nodes, args, sudo = False, supressWarning = False):
    for node in nodes:
        run_script( node, args, sudo = sudo, supressWarning = supressWarning)

def run_script_on_all_in_parallel(nodes, args, sudo=False, supressWarning=False):
    args_list = [(node, args, sudo, supressWarning) for node in nodes]

    # TODO: Tolerate faults
    from multiprocessing import Pool
    pool = Pool(processes=len(nodes))
    pool.map(run_script_wrapper, args_list)
    pool.close()


def run_script_on_rand_master(nargs, args):
    nodes = get_ETCD_master_nodes(config["clusterId"])
    master_node = random.choice(nodes)
    run_script_on_all([master_node], nargs, sudo = args.sudo )

def copy_to_all(nodes, src, dst):
    for node in nodes:
        rmt_cp(node, src, dst)

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
    return dic

def set_host_names_by_lookup():
    domainEntry = fetch_config( config, ["network", "domain"] )
    machineEntry = fetch_config( config, ["machines"] )
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
                hostname = node.split(".")[0]
                cmd = "sudo hostnamectl set-hostname " + hostname
                print "Set hostname of node " + node + " to " + hostname
                utils.SSH_exec_cmd( config["ssh_cert"], config["admin_username"], node, cmd )
            else:
                usename = namelist[0]
                cmd = "sudo hostnamectl set-hostname " + usename
                print "Set hostname of node " + node + " ... " + usename
                utils.SSH_exec_cmd( config["ssh_cert"], config["admin_username"], node, cmd )

def set_freeflow_router(  ):
    nodes = get_worker_nodes(config["clusterId"], False) + get_ETCD_master_nodes(config["clusterId"])
    for node in nodes:
        set_freeflow_router_on_node(node)



def set_freeflow_router_on_node( node ):
    docker_image = config["dockers"]["container"]["freeflow"]["fullname"]
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

def deploy_ETCD_master(force = False):
        print "Detected previous cluster deployment, cluster ID: %s. \n To clean up the previous deployment, run 'python deploy.py clean' \n" % config["clusterId"]
        print "The current deployment has:\n"

        check_master_ETCD_status()

        if "etcd_node" in config and len(config["etcd_node"]) >= int(config["etcd_node_num"]) and "kubernetes_master_node" in config and len(config["kubernetes_master_node"]) >= 1:
            print "Ready to deploy kubernetes master on %s, etcd cluster on %s.  " % (",".join(config["kubernetes_master_node"]), ",".join(config["etcd_node"]))
            gen_configs()
            response = raw_input_with_default("Clean Up master, and deploy ETCD Nodes (y/n)?")
            if first_char(response) == "y":
                clean_master()
                gen_ETCD_certificates()
                deploy_ETCD()
            response = raw_input_with_default("Deploy Master Nodes (y/n)?")
            if first_char(response) == "y":
                gen_master_certificates()
                deploy_masters(force)
            return True
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
    kube_node_name = ""
    domain = get_domain()
    if len(domain) < 2:
        kube_node_name = node
    elif domain in node:
        kube_node_name = node[:-(len(domain))]
    else:
        kube_node_name = node
    if config["isacs"]:
        acs_tools.acs_set_node_from_dns(kube_node_name)
        kube_node_name = config["acs_node_from_dns"][kube_node_name]
    return kube_node_name

def set_zookeeper_cluster():
    nodes = get_node_lists_for_service("zookeeper")
    config["zookeepernodes"] = ";".join(nodes)
    config["zookeepernumberofnodes"] = str(len(nodes))

def render_service_templates():
    allnodes = get_nodes(config["clusterId"])
    # Additional parameter calculation
    set_zookeeper_cluster()
    generate_hdfs_containermounts()
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
                with open(launch_order_file,'r') as f:
                    allservices = f.readlines()
                    for filename in reversed(allservices):
                        filename = filename.strip()
                        filename = os.path.join(dirname, filename)
                        if os.path.isfile(filename):
                            servicedic[service+"/"+os.path.splitext(os.path.basename(filename))[0]] = filename

            else:
                yamlname = os.path.join(dirname, service + ".yaml")
                if not os.path.isfile(yamlname):
                    yamls = glob.glob("*.yaml")
                    yamlname = yamls[0]
                with open( yamlname ) as f:
                    content = f.read()
                    f.close()
                    if content.find( "Deployment" )>=0 or content.find( "DaemonSet" )>=0 or content.find("ReplicaSet")>=0 or content.find("CronJob")>=0:
                        # Only add service if it is a daemonset.
                        servicedic[service] = yamlname
    return servicedic

def get_service_name(service_config_file):
    f = open(service_config_file)
    try:
        service_config = yaml.load(f, Loader=yaml.FullLoader)
    except:
        return None
    f.close()
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

# Get the list of nodes for a particular service
#
def get_node_lists_for_service(service):
        if "etcd_node" not in config or "worker_node" not in config:
            check_master_ETCD_status()
        labels = fetch_config(config, ["kubelabels"])
        nodetype = labels[service] if service in labels else labels["default"]
        if nodetype == "worker_node":
            nodes = config["worker_node"]
        elif nodetype == "mysqlserver_node":
            nodes = config["mysqlserver_node"]
        elif nodetype == "nfs_node":
            nodes = config["nfs_node"]
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
            machines = fetch_config(config, ["machines"])
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
    print "servicedic\n", servicedic
    get_nodes(config["clusterId"])
    labels = fetch_config(config, ["kubelabels"])
    print "labels\n", labels
    for service, serviceinfo in servicedic.iteritems():
        servicename = get_service_name(servicedic[service])
        if (not service in labels) and (not servicename in labels) and "default" in labels and (not servicename is None):
            print "not in: {},{}\n".format(service, serviceinfo)
            labels[servicename] = labels["default"]
    if len(servicelists)==0:
        servicelists = labels
    else:
        for service in servicelists:
            if (not service in labels) and "default" in labels:
                labels[service] = labels["default"]
    print servicelists
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


# Label kubernete nodes with gpu types.skip for CPU workers
def kubernetes_label_GpuTypes():
    for nodename,nodeInfo in config["machines"].items():
        if nodeInfo["role"] == "worker":
            kubernetes_label_node("--overwrite", nodename, "gpuType="+nodeInfo["gpu-type"])


def populate_machine_sku(machine_info):
    """Potentially adds sku for and returns the modified machine_info.

    Args:
        machine_info: A dictionary containing machine information.

    Returns:
        Modified machine_info
    """
    if "sku" not in machine_info and "node-group" in machine_info:
        machine_info["sku"] = machine_info["node-group"]
    return machine_info


def get_machines_by_roles(roles, cnf):
    """Get machines from cnf that has role in roles.

    Args:
        roles: A comma separated string or a list of roles.
        cnf: Configuration dictionary containing machines.

    Returns:
        A dictionary of machines that has role in roles.
    """
    if roles == "all":
        roles = cnf.get("allroles", [])

    if isinstance(roles, str):
        roles = [role.strip() for role in roles.split(",")]

    machines = cnf.get("machines", {})

    machines_by_roles = {}
    for machine_name, machine_info in machines.items():
        machine_info = populate_machine_sku(machine_info)
        if "role" in machine_info and machine_info["role"] in roles:
            machines_by_roles[machine_name] = machine_info

    return machines_by_roles


def get_sku_meta(cnf):
    """Get SKU meta information from cnf.

    Args:
        cnf: Configuration dictionary containing machines.

    Returns:
        SKU meta dictionary from configuration.
    """
    return cnf.get("sku_meta", {})


def kubernetes_label_cpuworker():
    """Label kubernetes nodes with cpuworker=active."""
    label = "cpuworker=active"
    sku_meta = get_sku_meta(config)
    workers = get_machines_by_roles("worker", config)

    for machine_name, machine_info in workers.items():
        if "sku" in machine_info and machine_info["sku"] in sku_meta:
            sku = machine_info["sku"]
            if "gpu" not in sku_meta[sku]:
                kubernetes_label_node("--overwrite", machine_name, label)


def kubernetes_label_sku():
    """Label kubernetes nodes with sku=<sku_value>"""
    sku_meta = get_sku_meta(config)
    machines = get_machines_by_roles("all", config)

    for machine_name, machine_info in machines.items():
        if "sku" in machine_info and machine_info["sku"] in sku_meta:
            sku = machine_info["sku"]
            kubernetes_label_node("--overwrite", machine_name, "sku=%s" % sku)


def kubernetes_label_vc():
    """Label kubernetes nodes with vc=<vc_value>"""
    machines = get_machines_by_roles("all", config)

    for machine_name, machine_info in machines.items():
        vc = "default"
        if "vc" in machine_info and machine_info["vc"] is not None:
            vc = machine_info["vc"]
        kubernetes_label_node("--overwrite", machine_name, "vc=%s" % vc)


def kubernetes_patch_nodes_provider (provider, scaledOnly):
    nodes = []
    if scaledOnly:
        nodes = get_scaled_nodes(config["clusterId"])
    else:
        nodes = get_nodes(config["clusterId"])
    for node in nodes:
        nodename = kubernetes_get_node_name(node)
        patch = '\'{"spec":{"providerID":"' + provider + '://' + nodename + '"}}\''
        run_kubectl(["patch node %s %s %s" % (nodename, "-p", patch)])

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
        nodeconfig = fetch_config(config, ["machines", nodename])
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
        # use try/except because yaml.load cannot load yaml file with multiple documents.
        try:
            f = open(fname)
            service_yaml = yaml.load(f, Loader=yaml.FullLoader)
            f.close()
            print "Start service: "
            print service_yaml
        except Exception as e:
            pass

    run_kubectl(["create", "-f", fname ])


def stop_one_kube_service(fname):
    run_kubectl( ["delete", "-f", fname ] )

def start_kube_service( servicename ):
    fname = get_service_yaml( servicename )
    dirname = os.path.dirname(fname)
    if os.path.exists(os.path.join(dirname,"launch_order")) and "/" not in servicename:
        with open(os.path.join(dirname,"launch_order"),'r') as f:
            allservices = f.readlines()
            for filename in allservices:
                # If this line is a sleep tag (e.g. SLEEP 10), sleep for given seconds to wait for the previous service to start.
                if filename.startswith("SLEEP"):
                    time.sleep(int(filename.split(" ")[1]))
                else:
                    filename = filename.strip('\n')
                    start_one_kube_service(os.path.join(dirname,filename))
    else:
        start_one_kube_service(fname)

def stop_kube_service( servicename ):
    fname = get_service_yaml( servicename )
    dirname = os.path.dirname(fname)
    if os.path.exists(os.path.join(dirname,"launch_order")) and "/" not in servicename:
        with open(os.path.join(dirname,"launch_order"),'r') as f:
            allservices = f.readlines()
            for filename in reversed(allservices):
                # If this line is a sleep tag, skip this line.
                if not filename.startswith("SLEEP"):
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
    build_dockers("./deploy/docker-images/", config["dockerprefix"], config["dockertag"], nargs, config, verbose, nocache = nocache )

def push_docker_images(nargs):
    render_docker_images()
    if verbose:
        print "Build & push docker images to docker register  ..."
        print "Nocache: {0}".format(nocache)
    push_dockers("./deploy/docker-images/", config["dockerprefix"], config["dockertag"], nargs, config, verbose, nocache = nocache )

def check_buildable_images(nargs):
    for imagename in nargs:
        imagename = imagename.lower()
        if imagename in config["build-docker-via-config"]:
            print "Docker image %s should be built via configuration. " % imagename
            exit()

def run_docker_image( imagename, native = False, sudo = False ):
    dockerConfig = fetch_config( config, ["docker-run", imagename ])
    full_dockerimage_name, local_dockerimage_name = build_docker_fullname( config, imagename )
    matches = find_dockers( full_dockerimage_name )
    if len( matches ) == 0:
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

def gen_dns_config_script():
    utils.render_template("./template/dns/dns.sh.template", "scripts/dns.sh", config)

def gen_pass_secret_script():
    utils.render_template("./template/secret/pass_secret.sh.template", "scripts/pass_secret.sh", config)

def gen_warm_up_cluster_script():
    utils.render_template("./template/warmup/pre_download_images.sh.template", "scripts/pre_download_images.sh", config)

def run_command( args, command, nargs, parser ):
    # If necessary, show parsed arguments.
    global discoverserver
    global homeinserver
    global verbose
    global config

    global ipAddrMetaname
    global nocache

    sshtempfile = ""

    nocache = args.nocache

    discoverserver = args.discoverserver
    homeinserver = args.homeinserver

    if args.verbose:
        verbose = True
        utils.verbose = True
        print "Args = {0}".format(args)

    if command == "restore":
        utils.restore_keys(nargs)
        # Stop parsing additional command
        exit()
    elif command == "restorefromdir":
        utils.restore_keys_from_dir(nargs)
        exit()

    # Cluster Config
    config_cluster = os.path.join(dirpath,"cluster.yaml")
    if os.path.exists(config_cluster):
        merge_config(config, yaml.load(open(config_cluster), Loader=yaml.FullLoader))

    config_file = os.path.join(dirpath,"config.yaml")
    if not os.path.exists(config_file):
        parser.print_help()
        print "ERROR: config.yaml does not exist!"
        exit()

    with open(config_file) as f:
        merge_config(config, yaml.load(f, Loader=yaml.FullLoader))
    if os.path.exists("./deploy/clusterID.yml"):
        with open("./deploy/clusterID.yml") as f:
            tmp = yaml.load(f, Loader=yaml.FullLoader)
            if "clusterId" in tmp:
                config["clusterId"] = tmp["clusterId"]
    if "copy_sshtemp" in config and config["copy_sshtemp"]:
        if "ssh_origfile" not in config:
            config["ssh_origfile"] = config["ssh_cert"]
        sshfile = os.path.join(dirpath,config["ssh_origfile"])
        if os.path.exists(sshfile):
            _, sshtempfile = tempfile.mkstemp(dir='/tmp')
            if verbose:
                print "SSH file is now {0}".format(sshtempfile)
            with open (sshtempfile, 'wb') as output:
                with open (sshfile, 'rb') as input:
                    output.write(input.read())
            config["ssh_cert"] = sshtempfile
        else:
            print "SSH Key {0} not found using original".format(sshfile)

    add_acs_config(command)
    if verbose and config["isacs"]:
        print "Using Azure Container Services"
    if os.path.exists("./deploy/clusterID.yml"):
        update_config()
    else:
        apply_config_mapping(config, default_config_mapping)
        update_docker_image_config()
    # additional glusterfs launch parameter.
    config["launch-glusterfs-opt"] = args.glusterfs;
    get_ssh_config()
    configuration( config, verbose )
    if args.yes:
        global defanswer
        print "Use yes for default answer"
        defanswer = "yes"

    if args.public:
        ipAddrMetaname = "clientIP"


    if verbose:
        print "deploy " + command + " " + (" ".join(nargs))
        print "PlatformScripts = {0}".format(config["platform-scripts"])

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
            role2connect = nargs[0]
            if len(nargs) < 1 or role2connect == "master":
                nodes = config["kubernetes_master_node"]
            elif role2connect in ["etcd", "worker", "nfs", "samba", "mysqlserver"]:
                nodes = config["{}_node".format(role2connect)]
            else:
                parser.print_help()
                print "ERROR: must connect to either master, etcd, nfs or worker nodes"
                exit()
            if len(nodes) == 0:
                parser.print_help()
                print "ERROR: cannot find any node of the type to connect to"
                exit()

            num = 0
            nodename = None
            if len(nargs) >= 2:
                try:
                    num = int(nargs[1])
                    if num < 0 or num >= len(nodes):
                        num = 0
                except ValueError:
                    nodename = get_node_full_name(nargs[1])

            if nodename is None:
                nodename = nodes[num]
            utils.SSH_connect(config["ssh_cert"], config["admin_username"], nodename)
            exit()

    elif command == "deploy" and "clusterId" in config:
        deploy_ETCD_master(force=args.force)
        utils.render_template("./template/kubeconfig/kubeconfig.yaml.template", "deploy/kubeconfig/kubeconfig.yaml", config)

    elif command == "nfs-server":
        if len(nargs) > 0:
            if nargs[0] == "create":
                set_nfs_disk()
            else:
                print "Error: subcommand %s is not recognized for nfs-server. " % nargs[0]
                exit()
        else:
            print "Error: nfs-server need a subcommand (create) " % nargs[0]
            exit()

    elif command == "build":
        configuration( config, verbose )
        if len(nargs) <=0:
            init_deployment()
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

    elif command == "dnssetup":
        os.system("./gene_loc_dns.sh")
        nodes = get_nodes(config["clusterId"])
        run_script_on_all(nodes, "./scripts/dns.sh", sudo = args.sudo )

    elif command == "sshkey":
        if len(nargs) >=1 and nargs[0] == "install":
            install_ssh_key(nargs[1:])
        else:
            parser.print_help()
            print "Error: build target %s is not recognized. " % nargs[0]
            exit()

    elif command == "scan":
        if len(nargs) ==1:
            utils.scan_nodes( config["ssh_cert"], config["admin_username"], nargs[0])
        else:
            parser.print_help()
            print "Error: scan need one parameter with format x.x.x.x/n. "
            exit()

    elif command == "admin":
        if len(nargs) >= 1:
            if nargs[0] == "vc":
                if len(nargs) >= 2:
                    if nargs[1] == "add":
                        url = "http://%s:%s/AddVC?vcName=%s&quota=%s&metadata=%s&userName=Administrator" %  (config["kubernetes_master_node"][0],config["restfulapiport"], nargs[2], nargs[3], nargs[4])
                        response = requests.get(url)
                        print(response)
                    elif nargs[1] == "update":
                        url = "http://%s:%s/UpdateVC?vcName=%s&quota=%s&metadata=%s&userName=Administrator" \
                            %  (config["kubernetes_master_node"][0],config["restfulapiport"], nargs[2], nargs[3], nargs[4])
                        response = requests.get(url)
                        print(response)
                    elif nargs[1] == "delete":
                        url = "http://%s:%s/DeleteVC?vcName=%s&userName=Administrator" %  (config["kubernetes_master_node"][0],config["restfulapiport"], nargs[2])
                        response = requests.get(url)
                        print(response)
                    elif nargs[1] == "list":
                        url = "http://%s:%s/ListVCs?userName=Administrator" %  (config["kubernetes_master_node"][0],config["restfulapiport"])
                        response = requests.get(url)
                        print(response.text)
            elif nargs[0] == "storage":
                if len(nargs) >= 2:
                    if nargs[1] == "add":
                        url = "http://%s:%s/AddStorage?vcName=%s&url=%s&storageType=%s&metadata=%s&defaultMountPath=%s&userName=Administrator" %  (config["kubernetes_master_node"][0],config["restfulapiport"], nargs[2], nargs[3], nargs[4], nargs[5], nargs[6])
                        response = requests.get(url)
                        print(response)
                    elif nargs[1] == "update":
                        url = "http://%s:%s/UpdateStorage?vcName=%s&url=%s&storageType=%s&metadata=%s&defaultMountPath=%s&userName=Administrator" %  (config["kubernetes_master_node"][0],config["restfulapiport"], nargs[2], nargs[3], nargs[4], nargs[5], nargs[6])
                        response = requests.get(url)
                        print(response)
                    elif nargs[1] == "delete":
                        url = "http://%s:%s/DeleteStorage?vcName=%s&url=%s&userName=Administrator" %  (config["kubernetes_master_node"][0],config["restfulapiport"], nargs[2], nargs[3])
                        response = requests.get(url)
                        print(response)
                    elif nargs[1] == "list":
                        url = "http://%s:%s/ListStorages?vcName=%s&userName=Administrator" %  (config["kubernetes_master_node"][0],config["restfulapiport"], nargs[2])
                        response = requests.get(url)
                        print(response.text)
            elif nargs[0] == "acl":
                if len(nargs) >= 2:
                    if nargs[1] == "update":
                        url = "http://%s:%s/UpdateAce?identityName=%s&resourceType=%s&resourceName=%s&permissions=%s&userName=Administrator" %  (config["kubernetes_master_node"][0],config["restfulapiport"], nargs[2], nargs[3], nargs[4], nargs[5])
                        response = requests.get(url)
                        print(response)
                    elif nargs[1] == "list":
                        url = "http://%s:%s/GetACL?userName=Administrator" %  (config["kubernetes_master_node"][0],config["restfulapiport"])
                        response = requests.get(url)
                        print(response.text)
                    elif nargs[1] == "delete":
                        url = "http://%s:%s/DeleteAce?identityName=%s&resourceType=%s&resourceName=%s&userName=Administrator" %  (config["kubernetes_master_node"][0],config["restfulapiport"],nargs[2],nargs[3],nargs[4])
                        response = requests.get(url)
                        print(response.text)
            elif nargs[0] == "job":
                if len(nargs) >= 2:
                    if nargs[1] == "add":
                        url = "http://%s:%s/SubmitJob?jobName=%s&vcName=%s&resourcegpu=%s&gpuType=%s&dataPath=%s&workPath=%s&image=%s&jobType=%s&preemptionAllowed=%s&userName=Administrator" \
                            %  (config["kubernetes_master_node"][0],config["restfulapiport"], nargs[2], nargs[3], nargs[4], nargs[5], nargs[6], nargs[7], nargs[8], nargs[9], nargs[10])
                        response = requests.get(url)
                        print(response.text)
                    elif nargs[1] == "delete":
                        url = "http://%s:%s/KillJob?jobId=%s&userName=Administrator" \
                            %  (config["kubernetes_master_node"][0],config["restfulapiport"], nargs[2])
                        response = requests.get(url)
                        print(response.text)
                    elif nargs[1] == "list":
                        url = "http://%s:%s/ListJobs?vcName=%s&jobOwner=%s&num=%s&userName=Administrator" \
                            %  (config["kubernetes_master_node"][0],config["restfulapiport"], nargs[2], nargs[3], nargs[4])
                        response = requests.get(url)
                        print(response.text)
            elif nargs[0] == "user":
                if len(nargs) >= 2:
                    if nargs[1] == "add":
                        if len(nargs) <= 3:
                            url = "http://%s:%s/AddUser?userName=%s" %  (config["kubernetes_master_node"][0],config["restfulapiport"], nargs[2])
                            response = requests.get(url)
                            print(response)
                        else:
                            url = "http://%s:%s/AddUser?userName=%s&uid=%s&gid=%s&groups=%s" %  (config["kubernetes_master_node"][0],config["restfulapiport"], nargs[2], nargs[3], nargs[4], nargs[5])
                            response = requests.get(url)
                            print(response)

    elif command == "packcloudinit":
        gen_configs()
        render_and_pack_worker_cloud_init_files()

    elif command == "updateworker":
        response = raw_input_with_default("Deploy Worker Nodes (y/n)?")
        if first_char(response) == "y":
            check_master_ETCD_status()
            gen_configs()
            update_worker_nodes( nargs )

    elif command == "updateworkerinparallel":
        response = raw_input_with_default("Deploy Worker Nodes In Parallel (y/n)?")
        if first_char(response) == "y":
            check_master_ETCD_status()
            gen_configs()
            update_worker_nodes_in_parallel(nargs)

    elif command == "updatescaledworker":
        response = raw_input_with_default("Deploy Scaled Worker Nodes (y/n)?")
        if first_char(response) == "y":
            check_master_ETCD_status()
            gen_configs()
            update_scaled_worker_nodes( nargs )

    elif command == "resetworker":
        response = raw_input_with_default("Deploy Worker Nodes (y/n)?")
        if first_char(response) == "y":
            check_master_ETCD_status()
            gen_configs()
            reset_worker_nodes()

    elif command == "updatemysqlserver":
        response = raw_input_with_default("Deploy MySQLServer Node(s) (y/n)?")
        if first_char(response) == "y":
            check_master_ETCD_status()
            gen_configs()
            update_mysqlserver_nodes(nargs)

    elif command == "updatenfs":
        response = raw_input_with_default("Deploy NFS Node(s) (y/n)?")
        if first_char(response) == "y":
            check_master_ETCD_status()
            gen_configs()
            update_nfs_nodes(nargs)

    elif command == "deploynfsconfig":
        deploy_nfs_config()

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
        response = raw_input_with_default("Clean and Stop Worker Nodes (y/n)?")
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
            print("This operation will DELETE all existing partitions and repartition all data drives on the %d nodes to %d partitions of %s" % (len(nodes), len(partsInfo), str(partsInfo)) )
            response = raw_input ("Please type (REPARTITION) in ALL CAPITALS to confirm the operation ---> ")
            if response == "REPARTITION":
                repartition_nodes( nodes, nodesinfo, partsInfo)
            else:
                print "Repartition operation aborted...."
        else:
            parser.print_help()
            exit()

    elif command == "glusterFS_heketi" and len(nargs) >= 1:
        # ToDo: change pending, schedule glusterFS on master & ETCD nodes,
        if nargs[0] == "start" or nargs[0] == "update" or nargs[0] == "stop" or nargs[0] == "clear":
            nodes = get_worker_nodes(config["clusterId"], False)
            nodesinfo = get_partitions(nodes, config["data-disk"] )
            glusterFSargs = fetch_config( config, ["glusterFS", "partitions"] )
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
                start_glusterFS_heketi( masternodes, fetch_config(config, ["ipToHostname"]), nodesinfo, glusterFSargs, flag = gsFlag )


        else:
            parser.print_help()
            exit()

    elif command == "glusterfs" and len(nargs) >= 1:
        allnodes = get_nodes(config["clusterId"])
        # ToDo: change pending, schedule glusterFS on master & ETCD nodes,
        nodes = get_node_lists_for_service("glusterfs")
        glusterFSargs = fetch_config( config, ["glusterFS", "partitions"] )
        if nargs[0] == "display":
            display_glusterFS_volume( nodes, glusterFSargs )
            exit()

        nodesinfo = get_partitions(nodes, glusterFSargs )
        if glusterFSargs is None:
            parser.print_help()
            print "Need to configure partitions which glusterFS will deploy..."
            exit()
        if nargs[0] == "create":
            print("This operation will CREATE new volume over all existing glusterFS partitions, and will erase the data on those partitions "  )
            response = raw_input ("Please type (CREATE) in ALL CAPITALS to confirm the operation ---> ")
            if response == "CREATE":
                create_glusterFS_volume( nodesinfo, glusterFSargs )
        elif nargs[0] == "remove":
            print("This operation will REMOVE volumes over all existing glusterFS partitions, and will erase the data on those partitions "  )
            response = raw_input ("Please type (REMOVE) in ALL CAPITALS to confirm the operation ---> ")
            if response == "REMOVE":
                remove_glusterFS_volume( nodesinfo, glusterFSargs )
        elif nargs[0] == "config":
            write_glusterFS_configuration( nodesinfo, glusterFSargs )
            dockername = fetch_config_and_check(config, ["glusterFS", "glusterfs_docker"])
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
            print("This operation will CREATE new volume over all existing hdfs partitions, and will erase the data on those partitions "  )
            response = raw_input ("Please type (CREATE) in ALL CAPITALS to confirm the operation ---> ")
            if response == "CREATE":
                format_mount_partition_volume( nodes, fetch_config(config, ["hdfs", "partitions"]), True )
        elif nargs[0] == "mount":
            format_mount_partition_volume( nodes, fetch_config(config, ["hdfs", "partitions"]), False )
        elif nargs[0] == "umount":
            unmount_partition_volume( nodes, fetch_config(config, ["hdfs", "partitions"]))
        elif nargs[0] == "config":
            hdfs_config( nodes, fetch_config(config, ["hdfs", "partitions"]))
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

    elif command == "runscriptonallinparallel" and len(nargs)>=1:
        nodes = get_nodes(config["clusterId"])
        run_script_on_all_in_parallel(nodes, nargs, sudo=args.sudo)

    elif command == "runscriptonroles":
        assert len(nargs)>=1
        nodeset, scripts_start = [], 0
        for ni, arg in enumerate(nargs):
            scripts_start = ni
            if arg in config["allroles"]:
                nodeset += arg,
            else:
                break
        nodes = get_nodes_by_roles(nodeset)
        run_script_on_all_in_parallel(nodes, nargs[scripts_start:], sudo = args.sudo )

    elif command == "runscriptonrandmaster" and len(nargs)>=1:
        run_script_on_rand_master(nargs, args)

    elif command == "runscriptonscaleup" and len(nargs)>=1:
        nodes = get_scaled_nodes(config["clusterId"])
        run_script_on_all(nodes, nargs, sudo = args.sudo )

    elif command == "copytoall" and len(nargs)>=1:
        nodes = get_nodes(config["clusterId"])
        print "Copy all from: {0} to: {1}".format(nargs[0], nargs[1])
        copy_to_all(nodes, nargs[0], nargs[1])

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

    elif command == "display" or command == "clusterinfo":
        configuration( config, verbose )
        configuration( config, verbose )
        check_master_ETCD_status()

    elif command == "webui":
        check_master_ETCD_status()
        gen_configs()
        deploy_webUI()

    elif command == "mount":
        if len(nargs)<=0:
            fileshare_install()
            allmountpoints = mount_fileshares_by_service(True)
            if args.force:
                print "forced to re-link fileshares"
                link_fileshares(allmountpoints, args.force)
        elif nargs[0]=="install":
            fileshare_install()
        elif nargs[0]=="start":
            allmountpoints = mount_fileshares_by_service(True)
            link_fileshares(allmountpoints, args.force)
        elif nargs[0]=="stop":
            unmount_fileshares_by_service(False)
        elif nargs[0]=="clean":
            print("This operation will CLEAN local content in the physical mount point, and may erase the data on those locations. "  )
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
        run_script_blocks(args.verbose, scriptblocks["azure"])

    elif command == "acs":
        k8sconfig["kubelet-path"] = "./deploy/bin/kubectl --kubeconfig=./deploy/%s" % (config["acskubeconfig"])
        if (len(nargs) == 0):
            run_script_blocks(args.verbose, scriptblocks["acs"])
        elif (len(nargs) >= 1):
            if nargs[0]=="deploy":
                acs_tools.acs_deploy() # Core K8s cluster deployment
                config = init_config(default_config_parameters) # reset for next round
            elif nargs[0]=="getconfig":
                acs_tools.acs_get_config()
            elif nargs[0]=="getip":
                ip = acs_tools.acs_get_ip_info_nodes(False)
                print ip
            elif nargs[0]=="getallip":
                ip = acs_tools.acs_get_ip_info_nodes(True)
                print ip
            elif nargs[0]=="createip":
                ip = acs_tools.acs_create_node_ips()
                print ip
            elif nargs[0]=="label":
                get_nodes(config["clusterId"])
                acs_label_webui()
            elif nargs[0]=="openports":
                acs_tools.acs_add_nsg_rules({"HTTPAllow" : 80, "RestfulAPIAllow" : 5000, "AllowKubernetesServicePorts" : "30000-32767"})
            elif nargs[0]=="getserviceaddr":
                print "Address: =" + json.dumps(k8sUtils.GetServiceAddress(nargs[1]))
            elif nargs[0]=="storagemount":
                acs_tools.acs_create_storage()
                fileshare_install()
                allmountpoints = mount_fileshares_by_service(True)
                del_fileshare_links()
                link_fileshares(allmountpoints, args.force)
            elif nargs[0]=="prepare":
                acs_prepare_machines()
            elif nargs[0]=="addons":
                # deploy addons / config changes (i.e. weave.yaml)
                acs_deploy_addons()
            elif nargs[0]=="freeflow":
                if ("freeflow" in config) and (config["freeflow"]):
                    kube_deploy_configchanges() # starte weave.yaml
                    run_script_blocks(args.verbose, ["kubernetes start freeflow"])
            elif nargs[0]=="jobendpt":
                acs_get_jobendpt(nargs[1])
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

    elif command == "jobendpt":
        print get_jobendpt(nargs[0])

    elif command == "update" and len(nargs)>=1:
        if nargs[0] == "config":
            update_config_nodes()

    elif command == "kubectl":
        run_kubectl(nargs)

    elif command == "kubernetes":
        configuration( config, verbose )
        if len(nargs) >= 1:
            if len(nargs)>=2:
                servicenames = nargs[1:]
            else:
                allservices = get_all_services()
                servicenames = []
                for service in allservices:
                    servicenames.append(service)
            generate_hdfs_containermounts()
            configuration(config, verbose)
            if nargs[0] == "start":
                if args.force and "hdfsformat" in servicenames:
                    print("This operation will WIPEOUT HDFS namenode, and erase all data on the HDFS cluster,  "  )
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
                    print "Error: kubernetes labels expect a verb which is either active, inactive or remove, but get: %s" % nargs[1]
            elif nargs[0] == "patchprovider":
                # TODO(harry): read a tag to decide which tools we are using, so we don't need nargs[1]
                if len(nargs)>=2 and ( nargs[1] == "aztools" or nargs[1] == "gstools" or nargs[1] == "awstools" ):
                    if len(nargs)==3:
                        kubernetes_patch_nodes_provider(nargs[1], nargs[2])
                    else:
                        kubernetes_patch_nodes_provider(nargs[1], False)
                else:
                    print "Error: kubernetes patchprovider expect a verb which is either aztools, gstools or awstools."
            elif nargs[0] == "mark":
                kubernetes_mark_nodes( nargs[1:], True)
            elif nargs[0] == "unmark":
                kubernetes_mark_nodes( nargs[1:], False)
            elif nargs[0] == "cordon" or nargs[0] == "uncordon":
                run_kube_command_on_nodes(nargs)
            elif nargs[0] == "labelvc":
                kubernetes_label_vc(True)
            else:
                parser.print_help()
                print "Error: Unknown kubernetes subcommand " + nargs[0]
        else:
            parser.print_help()
            print "Error: kubernetes need a subcommand."
            exit()

    elif command == "gpulabel":
        kubernetes_label_GpuTypes()

    elif command == "labelcpuworker":
        kubernetes_label_cpuworker()

    elif command == "labelsku":
        kubernetes_label_sku()

    elif command == "labelvc":
        kubernetes_label_vc()

    elif command == "genscripts":
        gen_platform_wise_config()
        gen_dns_config_script()
        gen_pass_secret_script()
        gen_warm_up_cluster_script()

    elif command == "setconfigmap":
        os.system('./deploy/bin/kubectl create configmap dlws-scripts --from-file=../Jobs_Templete -o yaml --dry-run | ./deploy.py kubectl apply -f -')

    elif command == "download":
        if len(nargs)>=1:
            if nargs[0] == "kubectl" or nargs[0] == "kubelet":
                os.system( "rm ./deploy/bin/*")
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

    elif command == "backuptodir":
        utils.backup_keys_to_dir(nargs)

    elif command == "nginx":
        if len(nargs)>=1:
            configuration( config, verbose )
            if nargs[0] == "config":
                config_nginx()
            if nargs[0] == "fqdn":
                config_fqdn()

    elif command == "docker":
        if len(nargs)>=1:
            configuration( config, verbose )
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
        configuration( config, verbose )
        template_file = nargs[0]
        target_file = nargs[1]
        utils.render_template(template_file, target_file,config)
    elif command == "upgrade_masters":
        gen_configs()
        upgrade_masters()
    elif command == "upgrade_workers":
        gen_configs()
        upgrade_workers(nargs)
    elif command == "upgrade":
        gen_configs()
        upgrade_masters()
        upgrade_workers(nargs)
    elif command in scriptblocks:
        run_script_blocks(args.verbose, scriptblocks[command])
    else:
        parser.print_help()
        print "Error: Unknown command " + command

    if os.path.exists(sshtempfile):
        print "Removing temp SSH file {0}".format(sshtempfile)
        os.remove(sshtempfile)

def run_script_blocks( verbose, script_collection ):
    if verbose:
        print "Run script blocks %s " % script_collection
    for script in script_collection:
        print "parse script %s" % ( script)
        args = parser.parse_args( script.split(" "))
        command = args.command
        nargs = args.nargs
        print "Run command %s, args %s" % (command, nargs )
        args.verbose = verbose
        run_command( args, command, nargs, parser )

def upgrade_worker_node(nodeIP):
    print "==============================================="
    print "upgrading worker node: %s ..."  % nodeIP

    worker_ssh_user = config["admin_username"]
    utils.SSH_exec_script(config["ssh_cert"],worker_ssh_user, nodeIP, "./deploy/kubelet/pre-worker-upgrade.sh")

    with open("./deploy/kubelet/upgrade.list", "r") as f:
        deploy_files = [s.split(",") for s in f.readlines() if len(s.split(",")) == 2]
    for (source, target) in deploy_files:
        if (os.path.isfile(source.strip()) or os.path.exists(source.strip())):
            utils.sudo_scp(config["ssh_cert"],source.strip(),target.strip(),worker_ssh_user, nodeIP)

    utils.SSH_exec_script(config["ssh_cert"],worker_ssh_user, nodeIP, "./deploy/kubelet/post-worker-upgrade.sh")

def upgrade_workers(nargs, hypekube_url="gcr.io/google-containers/hyperkube:v1.15.2"):
    config["dockers"]["external"]["hyperkube"]["fullname"] = hypekube_url
    config["dockers"]["container"]["hyperkube"]["fullname"] = hypekube_url

    utils.render_template_directory("./template/kubelet", "./deploy/kubelet", config)
    write_nodelist_yaml()

    os.system('sed "s/##etcd_endpoints##/%s/" "./deploy/kubelet/options.env.template" > "./deploy/kubelet/options.env"' % config["etcd_endpoints"].replace("/","\\/"))
    os.system('sed "s/##api_servers##/%s/" ./deploy/kubelet/kubelet.service.template > ./deploy/kubelet/kubelet.service' % config["api_servers"].replace("/","\\/"))
    os.system('sed "s/##api_servers##/%s/" ./deploy/kubelet/worker-kubeconfig.yaml.template > ./deploy/kubelet/worker-kubeconfig.yaml' % config["api_servers"].replace("/","\\/"))

    get_hyperkube_docker()

    workerNodes = get_worker_nodes(config["clusterId"], False)
    workerNodes = limit_nodes(workerNodes)
    for node in workerNodes:
        if in_list(node, nargs):
            upgrade_worker_node(node)

    os.system("rm ./deploy/kubelet/options.env")
    os.system("rm ./deploy/kubelet/kubelet.service")
    os.system("rm ./deploy/kubelet/worker-kubeconfig.yaml")

def upgrade_master(kubernetes_master):
    print "==============================================="
    kubernetes_master_user = config["kubernetes_master_ssh_user"]
    print "starting kubernetes master on %s..." % kubernetes_master

    assert config["priority"] in ["regular", "low"]
    if config["priority"] == "regular":
        config["master_ip"] = utils.getIP(kubernetes_master)
    else:
        config["master_ip"] = config["machines"][kubernetes_master.split(".")[0]]["private-ip"]
    utils.render_template("./template/master/kube-apiserver.yaml","./deploy/master/kube-apiserver.yaml",config)
    utils.render_template("./template/master/dns-kubeconfig.yaml","./deploy/master/dns-kubeconfig.yaml",config)
    utils.render_template("./template/master/kubelet.service","./deploy/master/kubelet.service",config)
    utils.render_template("./template/master/pre-upgrade.sh", "./deploy/master/pre-upgrade.sh", config)
    utils.render_template("./template/master/post-upgrade.sh", "./deploy/master/post-upgrade.sh", config)

    utils.SSH_exec_script(config["ssh_cert"],kubernetes_master_user, kubernetes_master, "./deploy/master/pre-upgrade.sh")

    with open("./deploy/master/upgrade.list", "r") as f:
        deploy_files = [s.split(",") for s in f.readlines() if len(s.split(",")) == 2]

    for (source, target) in deploy_files:
        if (os.path.isfile(source.strip()) or os.path.exists(source.strip())):
            utils.sudo_scp(config["ssh_cert"],source.strip(),target.strip(),kubernetes_master_user,kubernetes_master, verbose=verbose)

    utils.SSH_exec_script(config["ssh_cert"],kubernetes_master_user, kubernetes_master, "./deploy/master/post-upgrade.sh")

def upgrade_masters(hypekube_url="gcr.io/google-containers/hyperkube:v1.15.2"):
    config["dockers"]["external"]["hyperkube"]["fullname"] = hypekube_url
    config["dockers"]["container"]["hyperkube"]["fullname"] = hypekube_url

    kubernetes_masters = config["kubernetes_master_node"]
    kubernetes_master_user = config["kubernetes_master_ssh_user"]

    get_kubectl_binary(force=True)

    utils.render_template_directory("./template/master", "./deploy/master",config)
    utils.render_template_directory("./template/kube-addons", "./deploy/kube-addons",config)

    for kubernetes_master in kubernetes_masters:
        upgrade_master(kubernetes_master)
    deploy_cmd = """
        until curl -q http://127.0.0.1:8080/version/ ; do
            sleep 5;
            echo 'waiting for master kubernetes service...';
        done;

        until sudo /opt/bin/kubectl apply -f /opt/addons/kube-addons/weave.yaml --validate=false ; do
            sleep 5;
            echo 'waiting for master kube-addons weave...';
        done ;

        until sudo /opt/bin/kubectl apply -f /opt/addons/kube-addons/dashboard.yaml --validate=false ; do
            sleep 5;
            echo 'waiting for master kube-addons dashboard...';
        done ;

        until sudo /opt/bin/kubectl apply -f /opt/addons/kube-addons/dns-addon.yml --validate=false ;  do
            sleep 5;
            echo 'waiting for master kube-addons dns-addon...';
        done ;

        until sudo /opt/bin/kubectl apply -f /opt/addons/kube-addons/kube-proxy.json --validate=false ;  do
            sleep 5;
            echo 'waiting for master kube-addons kube-proxy...';
        done ;

        until sudo /opt/bin/kubectl apply -f /etc/kubernetes/clusterroles/ ;  do
            sleep 5;
            echo 'waiting for master kubernetes clusterroles...';
        done ;
    """
    utils.SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_masters[0], deploy_cmd , False)

if __name__ == '__main__':
    # the program always run at the current directory.
    dirpath = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
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
  nfs-server create: Create NFS-server.
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
  backuptodir    [pname] Backup configuration to a directory pname. Directory will be created
                 if absent, and symlinked to ./deploy_backup/backup.
  restore   [fname] [key] Decrypt & restore configuration, fname is the backup file with surfix.
            If the backup file is encrypted, a key needs to be provided to decrypt the configuration.
  restorefromdir [pname] Restore configuration from a directory pname. The directory will be symlinked
                 to ./deploy_backup/backup for restoration.
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
  nginx     [args] manage nginx reverse proxy
            config: config nginx node, mainly install file that specify how to direct traffic
            fqdn: config nginx node, install FQDN for each node
  execonall [cmd ... ] Execute the command on all nodes and print the output.
  doonall [cmd ... ] Execute the command on all nodes.
  runscriptonall [script] Execute the shell/python script on all nodes.
  listmac   display mac address of the cluster notes
  checkconfig   display config items
  rendertemplate template_file target_file
  upgrade_masters Upgrade the master nodes.
  upgrade_workers [nodes] Upgrade the worker nodes. If no additional node is specified, all nodes will be updated.
  upgrade [nodes] Upgrade the cluster and nodes. If no additional node is specified, all nodes will be updated.
  labelcpuworker Label CPU nodes with "worker" role with cpuworker=active if their SKU is defined in sku_meta.
  labelsku       Label nodes with "sku=<sku_value>" if their SKU is defined in sku_meta. In order to run distributed
                 CPU jobs, ./deploy.py labelcpuworker must be executed as well.
  labelvc        Label nodes with "vc=<vc_value>" if vc is defined in machine's property in machines sections in config.
                 Default to "vc=default".
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

    if not os.path.exists("./deploy"):
        os.system("mkdir -p ./deploy")
    config = init_config(default_config_parameters)

    if command == "scriptblocks":
        if nargs[0] in scriptblocks:
            run_script_blocks( args.verbose, scriptblocks[nargs[0]])
        else:
            parser.print_help()
            print "Error: Unknown scriptblocks " + nargs[0]
    else:
        run_command( args, command, nargs, parser)
