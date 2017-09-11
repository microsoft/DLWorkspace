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
    return config


def create_vm(vmname, config):
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

def create_group(config):
    cmd = """
        az group create --name %s --location %s 
        """ % (config["azure_cluster"]["resource_group_name"],config["azure_cluster"]["azure_location"])
    output = utils.exec_cmd_local(cmd)
    print (output)


def create_storage_account(config):
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


def create_vnet(config):
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

def create_nsg(config):
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

def delete_group(config):
    cmd = """
        az group delete -y --name %s 
        """ % (config["azure_cluster"]["resource_group_name"])
    output = utils.exec_cmd_local(cmd)
    print (output)

def create_cluster(config):
    print "creating resource group..."
    create_group(config)
    print "creating vnet..."
    create_vnet(config)
    print "creating network security group..."
    create_nsg(config)
    print "creating VMs"
    for i in range(int(config["azure_cluster"]["infra_node_num"])):
        vmname = "%s-infra%02d" % (config["azure_cluster"]["cluster_name"], i+1)
        print "creating VM %s..." % vmname
        create_vm(vmname,config)
    for i in range(int(config["azure_cluster"]["worker_node_num"])):
        vmname = "%s-worker%02d" % (config["azure_cluster"]["cluster_name"], i+1)
        print "creating VM %s..." % vmname
        create_vm(vmname,config)


def run_command( args, command, nargs, parser ):
    if command =="create":
        create_cluster(config)

    elif command == "delete":
        delete_group(config)


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
        azureconfig = yaml.load(open(config_cluster))    
        merge_config(config, azureconfig)
    if (args.cluster_name is not None):
        config["azure_cluster"]["cluster_name"] = args.cluster_name
    config = update_config(config)
    print (config)
    if "cluster_name" not in config["azure_cluster"] or config["azure_cluster"]["cluster_name"] is None:
        print ("Cluster Name cannot be empty")
        exit()
    run_command( args, command, nargs, parser)
