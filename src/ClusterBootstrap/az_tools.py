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
import utils

# These are the default configuration parameter
default_config_parameters = {
    "azure_cluster" : { 
        "infra_node_num": 1, 
        "worker_node_num": 2, 
        "azure_location": "westus2",
        "vm_size" : "Standard_D1_v2",
        "vm_image" : "UbuntuLTS",
        "vm_storage_sku" : "Standard_LRS",        
        "vnet_range" : "192.168.0.0/16",        
        "default_admin_username" : "dlwsadmin",        
        "file_share_name" : "files",        
        },
    }

def init_config():
    config = {}
    for k,v in default_config_parameters.iteritems():
        config[ k ] = v
    return config

def merge_config( config1, config2 ):
    for entry in config2:
        if entry in config1:
            if isinstance( config1[entry], dict): 
                merge_config( config1[entry], config2[entry] )
            else:
                config1[entry] = config2[entry]
        else:
            config1[entry] = config2[entry]

def update_config(config):
    config["azure_cluster"]["resource_group_name"] = config["azure_cluster"]["cluster_name"]+"ResGrp"
    config["azure_cluster"]["vnet_name"] = config["azure_cluster"]["cluster_name"]+"-VNet"
    config["azure_cluster"]["storage_account_name"] = config["azure_cluster"]["cluster_name"]+"storage"
    config["azure_cluster"]["nsg_name"] = config["azure_cluster"]["cluster_name"]+"-nsg"
    config["azure_cluster"]["storage_account_name"] = config["azure_cluster"]["cluster_name"]+"storage"

    config["azure_cluster"]["sql_server_name"] = config["azure_cluster"]["cluster_name"]+"sqlserver"
    config["azure_cluster"]["sql_admin_name"] = config["azure_cluster"]["cluster_name"]+"sqladmin"
    config["azure_cluster"]["sql_database_name"] = config["azure_cluster"]["cluster_name"]+"sqldb"

    if "sql_admin_password" not in config["azure_cluster"]:
        config["azure_cluster"]["sql_admin_password"] = uuid.uuid4().hex+"12#$AB"

    if (os.path.exists('./deploy/sshkey/id_rsa.pub')):
        f = open('./deploy/sshkey/id_rsa.pub')
        config["azure_cluster"]["sshkey"] = f.read()
        f.close()
    else:
        os.system("mkdir -p ./deploy/sshkey")
        if not os.path.exists("./deploy/sshkey/azure_id_rsa"):
            os.system("ssh-keygen -t rsa -b 4096 -f ./deploy/sshkey/azure_id_rsa -P ''")
        f = open('./deploy/sshkey/azure_id_rsa.pub')
        config["azure_cluster"]["sshkey"] = f.read()
        f.close()
    return config


def create_vm(vmname):
    cmd = """
        az vm create --resource-group %s \
                 --name %s \
                 --image %s \
                 --generate-ssh-keys  \
                 --public-ip-address-dns-name %s \
                 --location %s \
                 --size %s \
                 --vnet-name %s \
                 --subnet mySubnet \
                 --nsg %s \
                 --public-ip-address-allocation static \
                 --os-type linux \
                 --admin-username %s \
                 --storage-sku %s \
                 --ssh-key-value "%s" 
        """ % (config["azure_cluster"]["resource_group_name"],
               vmname,
               config["azure_cluster"]["vm_image"],
               vmname,
               config["azure_cluster"]["azure_location"],
               config["azure_cluster"]["vm_size"],
               config["azure_cluster"]["vnet_name"],
               config["azure_cluster"]["nsg_name"],
               config["azure_cluster"]["default_admin_username"],
               config["azure_cluster"]["vm_storage_sku"],
               config["azure_cluster"]["sshkey"])
    output = utils.exec_cmd_local(cmd)
    print (output)

def create_group():
    cmd = """
        az group create --name %s --location %s 
        """ % (config["azure_cluster"]["resource_group_name"],config["azure_cluster"]["azure_location"])
    output = utils.exec_cmd_local(cmd)
    print (output)


def create_sql():
    cmd = """
        az sql server create --resource-group %s \
                 --location %s \
                 --name %s \
                 --administrator-login %s \
                 --administrator-login-password %s
        """ % (config["azure_cluster"]["resource_group_name"],
               config["azure_cluster"]["azure_location"],
               config["azure_cluster"]["sql_server_name"],
               config["azure_cluster"]["sql_admin_name"],
               config["azure_cluster"]["sql_admin_password"])
    output = utils.exec_cmd_local(cmd)
    print (output)



    cmd = """
        az sql server firewall create --resource-group %s \
                 --server %s \
                 --name All \
                 --start-ip-address 0.0.0.0 \
                 --end-ip-address 255.255.255.255
        """ % (config["azure_cluster"]["resource_group_name"],
               config["azure_cluster"]["sql_server_name"])
    output = utils.exec_cmd_local(cmd)
    print (output)


    cmd = """
        az sql db create --resource-group %s \
                 --location %s \
                 --server %s \
                 --name  %s
        """ % (config["azure_cluster"]["resource_group_name"],
               config["azure_cluster"]["azure_location"],
               config["azure_cluster"]["sql_server_name"],
               config["azure_cluster"]["sql_database_name"])
    output = utils.exec_cmd_local(cmd)
    print (output)


def create_storage_account():
    cmd = """
        az storage account create \
            --name %s \
            --sku %s \
            --resource-group %s \
            --location %s 
        """ % (config["azure_cluster"]["storage_account_name"],
               config["azure_cluster"]["vm_storage_sku"],
               config["azure_cluster"]["resource_group_name"],
               config["azure_cluster"]["azure_location"])
    output = utils.exec_cmd_local(cmd)
    print (output)

def create_file_share():
    cmd = """
        az storage account show-connection-string \
            -n %s \
            -g %s \
            --query 'connectionString' \
            -o tsv
        """ % (config["azure_cluster"]["storage_account_name"],config["azure_cluster"]["resource_group_name"])
    output = utils.exec_cmd_local(cmd)
    print (output)

    cmd = """
        az storage share create \
            --name %s \
            --quota 2048 \
            --connection-string '%s'
        """ % (config["azure_cluster"]["file_share_name"],output)
    output = utils.exec_cmd_local(cmd)
    print (output)


def create_vnet():
    cmd = """
        az network vnet create \
            --resource-group %s \
            --name %s \
            --address-prefix %s \
            --subnet-name mySubnet \
            --subnet-prefix %s
        """ %( config["azure_cluster"]["resource_group_name"],
               config["azure_cluster"]["vnet_name"],
               config["azure_cluster"]["vnet_range"],
               config["azure_cluster"]["vnet_range"])
    output = utils.exec_cmd_local(cmd)
    print (output)

def create_nsg():
    cmd = """
        az network nsg create \
            --resource-group %s \
            --name %s
        """ %( config["azure_cluster"]["resource_group_name"],
               config["azure_cluster"]["nsg_name"])
    output = utils.exec_cmd_local(cmd)
    print (output)

    cmd = """
        az network nsg rule create \
            --resource-group %s \
            --nsg-name %s \
            --name allowall \
            --protocol tcp \
            --priority 1000 \
            --destination-port-range 0-65535 \
            --access allow
        """ %( config["azure_cluster"]["resource_group_name"],
               config["azure_cluster"]["nsg_name"])
    output = utils.exec_cmd_local(cmd)
    print (output)

def delete_group():
    cmd = """
        az group delete -y --name %s 
        """ % (config["azure_cluster"]["resource_group_name"])
    output = utils.exec_cmd_local(cmd)
    print (output)

def create_cluster():
    print "creating resource group..."
    create_group()
    print "creating storage account..."
    create_storage_account()
    print "creating file share..."
    create_file_share()
    print "creating vnet..."
    create_vnet()
    print "creating network security group..."
    create_nsg()
    print "creating sql server and database..."
    create_sql()
    print "creating VMs"
    for i in range(int(config["azure_cluster"]["infra_node_num"])):
        vmname = "%s-infra%02d" % (config["azure_cluster"]["cluster_name"], i+1)
        print "creating VM %s..." % vmname
        create_vm(vmname)
    for i in range(int(config["azure_cluster"]["worker_node_num"])):
        vmname = "%s-worker%02d" % (config["azure_cluster"]["cluster_name"], i+1)
        print "creating VM %s..." % vmname
        create_vm(vmname)

def gen_cluster_config(output_file_name):

    cmd = """
        az storage account show-connection-string \
            -n %s \
            -g %s \
            --query 'connectionString' \
            -o tsv
        """ % (config["azure_cluster"]["storage_account_name"],config["azure_cluster"]["resource_group_name"])
    output = utils.exec_cmd_local(cmd)
    reoutput = re.search('AccountKey\=.*$', output)
    file_share_key = None
    if reoutput is not None:
        file_share_key = reoutput.group(0).replace("AccountKey=","")

    cc = {}
    cc["cluster_name"] = config["azure_cluster"]["cluster_name"]
    cc["etcd_node_num"] = config["azure_cluster"]["infra_node_num"]

    cc["sqlserver-hostname"] = "tcp:%s.database.windows.net" % config["azure_cluster"]["sql_server_name"]
    cc["sqlserver-username"] = config["azure_cluster"]["sql_admin_name"]
    cc["sqlserver-password"] = config["azure_cluster"]["sql_admin_password"]
    cc["sqlserver-database"] = config["azure_cluster"]["sql_database_name"]
    cc["admin_username"] = config["azure_cluster"]["default_admin_username"]


    cc["useclusterfile"] = True
    cc["deploydockerETCD"] = False
    cc["platform-scripts"] = "ubuntu"
    cc["network"] = {"domain":"%s.cloudapp.azure.com" % config["azure_cluster"]["azure_location"]}
    cc["machines"] = {}
    for i in range(int(config["azure_cluster"]["infra_node_num"])):
        vmname = "%s-infra%02d" % (config["azure_cluster"]["cluster_name"], i+1)
        cc["machines"][vmname]= {"role": "infrastructure"}
    for i in range(int(config["azure_cluster"]["worker_node_num"])):
        vmname = "%s-worker%02d" % (config["azure_cluster"]["cluster_name"], i+1)
        cc["machines"][vmname]= {"role": "worker"}
    cc["WinbindServers"] = []
    cc["WebUIauthorizedGroups"] = ['MicrosoftUsers']
    cc["mountpoints"] = {"rootshare":{}}
    cc["mountpoints"]["rootshare"]["type"] = "azurefileshare"
    cc["mountpoints"]["rootshare"]["accountname"] = config["azure_cluster"]["storage_account_name"]
    cc["mountpoints"]["rootshare"]["filesharename"] = config["azure_cluster"]["file_share_name"]
    cc["mountpoints"]["rootshare"]["mountpoints"] = ""
    if file_share_key is not None:
        cc["mountpoints"]["rootshare"]["accesskey"] = file_share_key

    print yaml.dump(cc, default_flow_style=False)
    with open(output_file_name, 'w') as outfile:
        yaml.dump(cc, outfile, default_flow_style=False)

def run_command( args, command, nargs, parser ):
    if command =="create":
        create_cluster()

    elif command == "delete":
        delete_group()

    elif command == "genconfig":
        gen_cluster_config(nargs[0])

if __name__ == '__main__':
    # the program always run at the current directory. 
    dirpath = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
    # print "Directory: " + dirpath
    os.chdir(dirpath)
    parser = argparse.ArgumentParser( prog='az_utils.py',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent('''\
Create and manage a Azure VM cluster.

Prerequest:
* Create azure_cluster_config.yaml according to instruction in docs/deployment/Configuration.md.

Command:
  create Create an Azure VM cluster based on the parameters in config file. 
  delete Delete the Azure VM cluster. 
  ''') )
    parser.add_argument("--cluster_name", 
        help = "Specify a cluster name", 
        action="store", 
        default=None)        

    parser.add_argument("--infra_node_num", 
        help = "Specify the number of infra nodes, default = " + str(default_config_parameters["azure_cluster"]["infra_node_num"]), 
        action="store", 
        default=default_config_parameters["azure_cluster"]["infra_node_num"])



    parser.add_argument("--worker_node_num", 
        help = "Specify the number of worker nodes, default = " + str(default_config_parameters["azure_cluster"]["worker_node_num"]), 
        action="store", 
        default=default_config_parameters["azure_cluster"]["worker_node_num"])

    parser.add_argument("--azure_location", 
        help = "Specify azure location, default = " + default_config_parameters["azure_cluster"]["azure_location"], 
        action="store", 
        default=default_config_parameters["azure_cluster"]["azure_location"])

    parser.add_argument("--vm_size", 
        help = "Specify the azure virtual machine sku size, default = " + default_config_parameters["azure_cluster"]["vm_size"], 
        action="store", 
        default=default_config_parameters["azure_cluster"]["vm_size"])


    parser.add_argument("--vm_image", 
        help = "Specify the azure virtual machine image, default = " + default_config_parameters["azure_cluster"]["vm_image"], 
        action="store", 
        default=default_config_parameters["azure_cluster"]["vm_image"])


    parser.add_argument("--vm_storage_sku", 
        help = "Specify the azure storage sku, default = " + default_config_parameters["azure_cluster"]["vm_storage_sku"], 
        action="store", 
        default=default_config_parameters["azure_cluster"]["vm_storage_sku"])


    parser.add_argument("--vnet_range", 
        help = "Specify the azure virtual network range, default = " + default_config_parameters["azure_cluster"]["vnet_range"], 
        action="store", 
        default=default_config_parameters["azure_cluster"]["vnet_range"])

    parser.add_argument("--default_admin_username", 
        help = "Specify the default admin username of azure virtual machine, default = " + default_config_parameters["azure_cluster"]["default_admin_username"], 
        action="store", 
        default=default_config_parameters["azure_cluster"]["default_admin_username"])

    parser.add_argument("--file_share_name", 
        help = "Specify the default samba share name on azure stroage, default = " + default_config_parameters["azure_cluster"]["file_share_name"], 
        action="store", 
        default=default_config_parameters["azure_cluster"]["file_share_name"])





    parser.add_argument("command", 
        help = "See above for the list of valid command" )
    parser.add_argument('nargs', nargs=argparse.REMAINDER, 
        help="Additional command argument", 
        )
    args = parser.parse_args()
    command = args.command
    nargs = args.nargs
    config = init_config()
    # Cluster Config
    config_cluster = os.path.join(dirpath,"azure_cluster_config.yaml")
    if os.path.exists(config_cluster):
        tmpconfig = yaml.load(open(config_cluster)) 
        if tmpconfig is not None:
            merge_config(config, tmpconfig)

    config_file = os.path.join(dirpath,"config.yaml")
    if os.path.exists(config_file):
        tmpconfig = yaml.load(open(config_file)) 
        if tmpconfig is not None and "cluster_name" in tmpconfig:
            config["azure_cluster"]["cluster_name"] = tmpconfig["cluster_name"]

    if (args.cluster_name is not None):
        config["azure_cluster"]["cluster_name"] = args.cluster_name

    if (args.infra_node_num is not None):
        config["azure_cluster"]["infra_node_num"] = args.infra_node_num

    if (args.worker_node_num is not None):
        config["azure_cluster"]["worker_node_num"] = args.worker_node_num
    if (args.azure_location is not None):
        config["azure_cluster"]["azure_location"] = args.azure_location
    if (args.vm_size is not None):
        config["azure_cluster"]["vm_size"] = args.vm_size
    if (args.vm_image is not None):
        config["azure_cluster"]["vm_image"] = args.vm_image
    if (args.vm_storage_sku is not None):
        config["azure_cluster"]["vm_storage_sku"] = args.vm_storage_sku
    if (args.vnet_range is not None):
        config["azure_cluster"]["vnet_range"] = args.vnet_range
    if (args.default_admin_username is not None):
        config["azure_cluster"]["default_admin_username"] = args.default_admin_username
    if (args.file_share_name is not None):
        config["azure_cluster"]["file_share_name"] = args.file_share_name

        
    config = update_config(config)
    print (config)

    with open(config_cluster, 'w') as outfile:
        yaml.dump(config, outfile, default_flow_style=False)

    if "cluster_name" not in config["azure_cluster"] or config["azure_cluster"]["cluster_name"] is None:
        print ("Cluster Name cannot be empty")
        exit()
    config = run_command( args, command, nargs, parser)

    with open(config_cluster, 'w') as outfile:
        yaml.dump(config, outfile, default_flow_style=False)