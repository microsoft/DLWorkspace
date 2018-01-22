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
import json
from jinja2 import Environment, FileSystemLoader, Template
import base64
import tempfile
import urlparse

from shutil import copyfile, copytree
import urllib
import socket
sys.path.append("utils")
sys.path.append("../utils")
import utils
from apiclient.discovery import *
from six.moves import input
from gs_params import *
from az_params import *
from ConfigUtils import *

verbose = False

def init_config():
    config = default_config_parameters
    # print "Config ===== %s" % config
    # print "GS config == %s" % default_gs_parameters 
    merge_config(config, default_gs_parameters )
    return config

def get_location_string( location ):
    if location in config["gs_cluster"]["location_mapping"]:
        return config["gs_cluster"]["location_mapping"][location]
    else:
        return None

def get_sku( sku ):
    if sku in config["gs_cluster"]["sku_mapping"]:
        return config["gs_cluster"]["sku_mapping"][sku]
    else:
        return "regional"

# resource_group_name is cluster_name + ResGrp
def update_config(config, genSSH=True):
    return config

def create_group():
    # fails for unable to access credential created by gsutils
    crm = build("cloudresourcemanager", "v1") # http=creds.authorize(httplib2.Http()))
    body = {
        "project_id": config["gs_cluster"]["project"]["id"], 
        "name": config["gs_cluster"]["project"]["name"], 
    }
    print "Body = %s" % body

    operation = crm.projects().create(body = body).execute()
    output = utils.exec_cmd_local(cmd)
    print (output)

def create_storage_account(name, sku, location):
    actual_location = get_location_string(location)
    actual_sku = get_sku( sku )
    if actual_location is not None:
        print "name == %s, sku == %s, location == %s" %( name, actual_sku, actual_location)
        cmd = """
        gsutil mb -c %s \
                 -l %s \
                 gs://%s """ \
            % ( actual_sku, actual_location, name)
        if verbose:
            print(cmd)
        output = utils.exec_cmd_local(cmd)
        print (output)            

def delete_storage_account(name, sku, location):
    actual_location = get_location_string(location)
    actual_sku = get_sku( sku )
    if actual_location is not None:
        print "name == %s, sku == %s, location == %s" %( name, actual_sku, actual_location)
        cmd = """
        gsutil rm -r gs://%s """ % ( name)
        if verbose:
            print(cmd)
        output = utils.exec_cmd_local(cmd)
        print (output)            


def create_storage_with_config( configGrp, location ):
    storagename = configGrp["name"] + location
    output = create_storage_account( storagename, configGrp["sku"], location)
    if verbose: 
        print ( "Storage account %s" % output )
    if False:
        configGrp[location] = json.loads( output )
        configGrp[location]["fullname"] = storagename
        output = get_storage_keys( configGrp, location )
        if verbose: 
            print ( "Storage keys %s" % output )   
        keyConfig = json.loads( output )
        configGrp[location]["keys"] = keyConfig
        create_storage_containers( configGrp, location )
        if "cors" in configGrp and configGrp["cors"]: 
            add_cors(configGrp, location)    

def delete_storage_with_config( configGrp, location ):
    storagename = configGrp["name"] + location
    output = delete_storage_account( storagename, configGrp["sku"], location)

def create_storage_group( locations, configGrp, docreate = True ):
    locations = utils.tolist( config["azure_cluster"]["azure_location"])
    # print "locations == %s" % locations
    for location in locations:
        create_storage_with_config( configGrp, location )

def delete_storage_group( locations, configGrp, docreate = True ):
    locations = utils.tolist( config["azure_cluster"]["azure_location"])
    for location in locations:
        delete_storage_with_config( configGrp, location )

def create_storage( docreate = True ):
    locations = utils.tolist( config["azure_cluster"]["azure_location"])
    storages = utils.tolist( config["azure_cluster"]["storages"] ) 
    for grp in storages:
        configGrp = config["azure_cluster"][grp]
        create_storage_group( locations, configGrp, docreate )
    with open("gs_cluster_file.yaml", "w") as outfile:
        yaml.safe_dump( config, outfile, default_flow_style=False)

def delete_storage( docreate = True ):
    locations = utils.tolist( config["azure_cluster"]["azure_location"])
    storages = utils.tolist( config["azure_cluster"]["storages"] ) 
    for grp in storages:
        configGrp = config["azure_cluster"][grp]
        delete_storage_group( locations, configGrp, docreate )
    os.remove("gs_cluster_file.yaml")

def run_command( args, command, nargs, parser ):
    bExecute = False
    if command =="group" and len(nargs) >= 1:
        if nargs[0] == "create":
            print "At this moment, please create project from console. "

        elif nargs[0] == "delete":
            print "At this moment, please delete project from console. "
        ()

    if command == "storage":
        if nargs[0] == "create":
            create_storage()
            bExecute = True
        elif nargs[0] == "delete":
            delete_storage()
            bExecute = True

    elif command == "genconfig":
        () # gen_cluster_config("cluster.yaml")


if __name__ == '__main__':
    # the program always run at the current directory. 
    dirpath = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
    # print "Directory: " + dirpath
    os.chdir(dirpath)
    parser = argparse.ArgumentParser( prog='gs_tools.py',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent('''\
Create and manage GCP cluster.

Command:
    storage manage gcp storage bucket
        create: create GCP Stroage
        delete: delete GCP Storage
    genconfig Generate configuration files for Azure VM cluster. 
  ''') )

    parser.add_argument("--verbose", "-v", 
        help = "Enable verbose output during script execution", 
        action = "store_true"
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
        verbose = args.verbose
    config = init_config()
    # Cluster Config
    config_cluster = os.path.join(dirpath,"gs_cluster_config.yaml")
    if os.path.exists(config_cluster):
        tmpconfig = yaml.load(open(config_cluster)) 
        if tmpconfig is not None:
            merge_config(config, tmpconfig, verbose)

    config_file = os.path.join(dirpath,"config.yaml")
    if os.path.exists(config_file):
        tmpconfig = yaml.load(open(config_file)) 
        if tmpconfig is not None and "cluster_name" in tmpconfig:
            config["gs_cluster"]["cluster_name"] = tmpconfig["cluster_name"]
        if tmpconfig is not None and "gs_cluster" in tmpconfig:
            merge_config( config["gs_cluster"], tmpconfig["gs_cluster"][config["gs_cluster"]["cluster_name"]], verbose )
            
        
    config = update_config(config)
    print (config)

#   with open(config_cluster, 'w') as outfile:
#     yaml.dump(config, outfile, default_flow_style=False)

    run_command( args, command, nargs, parser)


