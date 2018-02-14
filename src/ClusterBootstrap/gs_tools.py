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
# from params import *
from gs_params import *
from az_params import *
from ConfigUtils import *

verbose = False

def init_config():
    config = default_config_parameters
    # print "Config ===== %s" % config
    # print "GS config == %s" % default_gs_parameters 
    merge_config(config, default_gs_parameters )
    # print config
    return config

def get_location_string( location ):
    if location in config["gs_cluster"]["location_mapping"]:
        return config["gs_cluster"]["location_mapping"][location]
    else:
        return None

def get_region_string( location ):
    if location in config["gs_cluster"]["region_mapping"]:
        return config["gs_cluster"]["region_mapping"][location]
    else:
        return None

def get_sku( sku ):
    if sku in config["gs_cluster"]["sku_mapping"]:
        return config["gs_cluster"]["sku_mapping"][sku]
    else:
        return "regional"

def get_num_infra_nodes(location):
    return config["gs_cluster"]["infra_node_num"]

def get_num_worker_nodes(location):
    return config["gs_cluster"]["worker_node_num"]

def setup_gce_ssh_key(location):
    filename = "./deploy/sshkey/id_rsa.gcloud.pub"
    if not os.path.exists(filename):
        with open("./deploy/sshkey/id_rsa.pub","r" ) as f:
            keyinfo = f.read().split()
            admin_username = config["gs_cluster"]["default_admin_username"]
            with open( filename, "w") as wf:
                wf.write(admin_username + ":" + keyinfo[0] + " "+ keyinfo[1]+ " "+admin_username )
    return filename

# resource_group_name is cluster_name + ResGrp
def update_config(config, genSSH=True):
    return config

def get_locations():
    if "azure_cluster" in config and "azure_location" in config["azure_cluster"]:
        return utils.tolist( config["azure_cluster"]["azure_location"])
    elif "gs_cluster" in config and "gs_location" in config["gs_cluster"]:
        return utils.tolist( config["gs_cluster"]["gs_location"])
    else:
        return []

def save_config():
    with open("gs_cluster_file.yaml", "w") as outfile:
        yaml.safe_dump( config["gs_cluster"], outfile, default_flow_style=False)


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
    actual_location = get_region_string(location)
    actual_sku = get_sku( sku )
    print "name == %s, sku == %s, location == %s" %( name, actual_sku, actual_location)   
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
        cmd2 = """ 
            gcloud compute backend-buckets create %s-bucket --gcs-bucket-name %s --enable-cdn \
            """ % (name, name)
        output2 = utils.exec_cmd_local(cmd2)
        print (output2)
    return name
        
        # cmd3 = """gcloud compute url-maps add-path-matcher %s-public-rule --default-service web-map-backend-service \
        #    --path-matcher-name bucket-matcher \
        #    --backend-bucket-path-rules="/public/*=%s-bucket" """ % (name, name)
        #output3 = utils.exec_cmd_local(cmd3)            
        # print( output3)
        

def delete_storage_account(name, sku, location):
    actual_location = get_region_string(location)
    actual_sku = get_sku( sku )
    if actual_location is not None:
        print "name == %s, sku == %s, location == %s" %( name, actual_sku, actual_location)
        cmd = """
        gsutil rm -r gs://%s """ % ( name)
        if verbose:
            print(cmd)
        output = utils.exec_cmd_local(cmd)
        print (output)          
        cmd2 = """ 
            gcloud compute backend-buckets delete %s-bucket \
            """ % (name)
        output2 = utils.exec_cmd_local(cmd2)
        print (output2)
        # cmd3 = """ 
        #    gcloud compute url-maps remove-path-matcher %s-public-rule \
        #    """ % (name)
        # output3 = utils.exec_cmd_local(cmd3)
        
def config_app_with_google( configApp, provider ):
    locations = get_locations()
    storages = utils.tolist( config["azure_cluster"]["storages"] ) 
    if not ("Services" in configApp):
        configApp["Services"] = {}
    for location in locations:
        actual_location = get_region_string(location)
        if actual_location is not None:
            for grp in ["cdn"]:
                configGrp = config["azure_cluster"][grp]
                storagename = configGrp["name"] + location
                if not (location in configApp["Services"]):
                    configApp["Services"][location] = {}
                configAppGrp = configApp["Services"][location]
                if not ("cdns" in configAppGrp):
                    configAppGrp["cdns"] = {}
                if provider not in configAppGrp["cdns"]:
                    configAppGrp["cdns"][provider] = []
                endpoint = "https://storage.googleapis.com/%s/" % storagename
                configAppGrp["cdns"][provider].append ( endpoint )
    

def open_all_port( vmname, location):
    ()

def all_sshkey(vmname, location):
    ()

def create_gc_vm( vmname, addrname, vmsize, location, configCluster, docreate):
    print "creating VM %s, size %s ..." % ( vmname, vmsize)
    uselocation = get_location_string(location)
    cmd = """
        gcloud compute instances create %s \
                --zone %s \
                --machine-type %s \
                %s """ \
            % ( vmname, uselocation, vmsize, configCluster["vm_image"])
    if addrname is not None:
        cmd += " --address=%s " % addrname
    if True: # verbose:
        print(cmd)
    output = utils.exec_cmd_local(cmd)
    print (output) 
    sshkeyfile = setup_gce_ssh_key(location)
    cmd2 = """
        gcloud compute instances add-metadata %s \
                --zone %s \
                --metadata-from-file \
                ssh-keys=%s
                """ \
            % ( vmname, uselocation, sshkeyfile )
    output = utils.exec_cmd_local(cmd2)  
    return output

def describe_gc_vm( vmname, location, configCluster):
    print "describing VM %s" % ( vmname)
    cmd = """
        gcloud compute instances describe %s \
                --zone %s \
                """ \
            % ( vmname, location)
    if verbose: # verbose:
        print(cmd)
    output = utils.exec_cmd_local(cmd)    
    return output

def delete_gc_vm( vmname, vmsize, location, configCluster, docreate):
    print "delete VM %s" % ( vmname)
    uselocation = get_location_string(location)
    cmd = """
        gcloud compute instances delete %s \
                --zone %s \
                --delete-disks=all
                """ \
            % ( vmname, uselocation)
    if True: # verbose:
        print(cmd)
    output = utils.exec_cmd_local(cmd)
    print (output)  
    return output
       

def create_vm_cluster(location, configCluster, docreate):
    # print "configCluster = %s " % configCluster
    infra_node_num = configCluster["infra_node_num"]
    worker_node_num = configCluster["worker_node_num"]
    cluster_name = config["gs_cluster"]["cluster_name"]
    if "machines" not in config:
        config["machines"] = {}
    for i in range(infra_node_num):
        vmname = "%s-infra%02d" % (cluster_name, i+1)
        addrname = get_infra_address(location, i)
        create_gc_vm(vmname, addrname, configCluster["infra_vm_size"], location, configCluster, docreate )
        config["machines"][vmname] = { "role": "infrastructure"}
    for i in range(worker_node_num):
        vmname = "%s-worker%02d" % (cluster_name, i+1)
        create_gc_vm(vmname, None, configCluster["worker_vm_size"], location, configCluster, docreate )
        config["machines"][vmname] = { "role": "worker"}

def delete_vm_cluster(location, configCluster, docreate):
    # print "configCluster = %s " % configCluster
    infra_node_num = configCluster["infra_node_num"]
    worker_node_num = configCluster["worker_node_num"]
    cluster_name = config["gs_cluster"]["cluster_name"]
    for i in range(infra_node_num):
        vmname = "%s-infra%02d" % (cluster_name, i+1)
        delete_gc_vm(vmname, configCluster["infra_vm_size"], location, configCluster, docreate )
    for i in range(worker_node_num):
        vmname = "%s-worker%02d" % (cluster_name, i+1)
        delete_gc_vm(vmname, configCluster["worker_vm_size"], location, configCluster, docreate )        

def get_address_name( location):
    cluster_name = config["gs_cluster"]["cluster_name"]
    addrname = cluster_name + "-" + location
    return addrname

def get_infra_address( location, cnt):
    addrname = get_address_name(location)
    addrcur = addrname + ("-infra%02d" % (cnt+1) )
    return addrcur

def create_address_location(location):
    useloc = get_region_string(location)
    addrname = get_address_name(location)
    infra_node_num = get_num_infra_nodes(location)
    for cnt in range(infra_node_num):
        addrcur = get_infra_address(location, cnt)
        cmd = """
            gcloud compute addresses create %s \
                    --region %s
                    """ \
                % ( addrcur, useloc)
        utils.exec_cmd_local(cmd)
        cmd1 = """
            gcloud compute addresses describe %s \
            --region %s --format json""" % (addrcur, useloc)
        output = utils.exec_cmd_local(cmd1)
        addr_info = json.loads( output)
        if "addresses" not in config["gs_cluster"]:
            config["gs_cluster"]["addresses"] = {}
        if location not in config["gs_cluster"]["addresses"]:
            config["gs_cluster"]["addresses"][location] = {}
        config["gs_cluster"]["addresses"][location][cnt+1] = addr_info
    # print (config["gs_cluster"])
    save_config()

def delete_address_location(location):
    useloc = get_region_string(location)
    addrname = get_address_name(location)
    infra_node_num = get_num_infra_nodes(location)
    for cnt in range(infra_node_num):
        addrcur = get_infra_address(location, cnt)
        cmd = """
            gcloud compute addresses delete %s \
                    --region %s \
                    """ \
                % ( addrcur, useloc)
        utils.exec_cmd_local(cmd)
    if "addresses" not in config["gs_cluster"]:
        config["gs_cluster"]["addresses"] = {}
    config["gs_cluster"]["addresses"][location] = None
    # print (config["gs_cluster"])
    save_config()


def create_address():
    locations = get_locations()
    for location in locations:
        create_address_location(location)
    save_config()

def delete_address():
    locations = get_locations()
    for location in locations:
        delete_address_location(location)
    save_config()


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
    locations = get_locations()
    print "locations == %s" % locations
    for location in locations:
        create_storage_with_config( configGrp, location )

def delete_storage_group( locations, configGrp, docreate = True ):
    locations = get_locations()
    for location in locations:
        delete_storage_with_config( configGrp, location )

def create_storage( docreate = True ):
    locations = get_locations()
    storages = utils.tolist( config["azure_cluster"]["storages"] ) 
    for grp in storages:
        configGrp = config["azure_cluster"][grp]
        create_storage_group( locations, configGrp, docreate )
    save_config()

def add_storage_config( gsConfig ):
    locations = get_locations()
    storages = utils.tolist( config["azure_cluster"]["storages"] ) 
    gsConfig["storage"] = {}
    for grp in storages:
        configGrp = config["azure_cluster"][grp]
        for location in locations:
            actual_location = get_region_string(location)
            if actual_location is not None:
                if grp not in gsConfig["storage"]:
                    gsConfig["storage"][grp] = {}
                storagename = configGrp["name"] + location
                gsConfig["storage"][grp][location] = storagename

def delete_storage( docreate = True ):
    locations = get_locations()
    storages = utils.tolist( config["azure_cluster"]["storages"] ) 
    for grp in storages:
        configGrp = config["azure_cluster"][grp]
        delete_storage_group( locations, configGrp, docreate )
    os.remove("gs_cluster_file.yaml")

def create_service_accounts():
    projectid = config["gs_cluster"]["project"]["id"]
    output1 = utils.exec_cmd_local("gcloud iam service-accounts create administrator")
    admin_account = "administrator@%s.iam.gserviceaccount.com" % projectid
    print output1
    output2 = utils.exec_cmd_local("""gcloud projects add-iam-policy-binding %s \
        --member serviceAccount:%s \
        --role roles/storage.admin """ % (projectid, admin_account))
    print output2
    output3 = utils.exec_cmd_local("""mkdir -p ./deploy/storage
    gcloud iam service-accounts keys create ./deploy/storage/google_administrator.json \
    --iam-account %s """ % (admin_account))
    print output3

    output5 = utils.exec_cmd_local("gcloud iam service-accounts create reader")
    reader_account = "reader@%s.iam.gserviceaccount.com" % projectid
    print output5
    output6 = utils.exec_cmd_local("""gcloud projects add-iam-policy-binding %s \
        --member serviceAccount:%s \
        --role roles/storage.objectViewer """ % (projectid, reader_account) )
    print output6
    output7 = utils.exec_cmd_local("""gcloud iam service-accounts keys create ./deploy/storage/google_reader.json \
    --iam-account %s """ % (reader_account))
    print output7


def delete_service_accounts():
    projectid = config["gs_cluster"]["project"]["id"]
    admin_account = "administrator@%s.iam.gserviceaccount.com" % projectid
    output1 = utils.exec_cmd_local("gcloud iam service-accounts delete %s" % admin_account )
    print output1
    reader_account = "reader@%s.iam.gserviceaccount.com" % projectid
    output2 = utils.exec_cmd_local("gcloud iam service-accounts delete %s" % reader_account )
    print output2

def create_vm( docreate = True):
    locations = get_locations()
    for location in locations:
        configCluster = config["gs_cluster"]
        print "Location = %s, config = %s" %( location, configCluster )
        create_vm_cluster( location, configCluster, docreate)
    save_config()

def delete_vm( docreate = True):
    locations = get_locations()
    for location in locations:
        configCluster = config["gs_cluster"]
        print "Location = %s, config = %s" %( location, configCluster )
        delete_vm_cluster( location, configCluster, docreate)
    save_config() 

def prepare_vm(docreate = True):
    create_firewall(docreate)
    cmd1 = "./deploy.py --verbose --sudo runscriptonall ./scripts/platform/gce/configure-vm.sh"
    output1 = utils.exec_cmd_local(cmd1)
    print output1
    cmd2 = "./deploy.py --verbose --sudo runscriptonall ./scripts/prepare_vm_disk.sh"
    output2 = utils.exec_cmd_local(cmd2)
    print output2

def create_firewall(docreate = True):
    cmd = """
        gcloud compute firewall-rules create tcp80 \
                --allow tcp:80\
                """ 
    output = utils.exec_cmd_local(cmd)
    print output
    cmd1 = """
        gcloud compute firewall-rules create allow-all \
                --allow tcp:0-65535\
                """ 
    output1 = utils.exec_cmd_local(cmd1)
    print output1

def delete_firewall(docreate = True):
    cmd = """
        gcloud compute firewall-rules delete tcp80 \
                """ 
    output = utils.exec_cmd_local(cmd)
    print output
    cmd1 = """
        gcloud compute firewall-rules delete allow-all \
                """ 
    output1 = utils.exec_cmd_local(cmd1)
    print output1


def gen_cluster_config(output_file_name, output_file=True):
    cc = {}
    cc["etcd_node_num"] = config["gs_cluster"]["infra_node_num"]
    cc["useclusterfile"] = True
    cc["deploydockerETCD"] = False
    cc["platform-scripts"] = "ubuntu"
    cc["basic_auth"] = "%s,admin,1000" % uuid.uuid4().hex[:12]
    cc["machines"] = {}
    for i in range(int(config["gs_cluster"]["infra_node_num"])):
        vmname = "%s-infra%02d" % (config["gs_cluster"]["cluster_name"], i+1)
        cc["machines"][vmname]= {"role": "infrastructure"}
    for i in range(int(config["gs_cluster"]["worker_node_num"])):
        vmname = "%s-worker%02d" % (config["gs_cluster"]["cluster_name"], i+1)
        cc["machines"][vmname]= {"role": "worker"}
    cc["admin_username"] = config["gs_cluster"]["default_admin_username"]

    if output_file:
        print yaml.dump(cc, default_flow_style=False)
        with open(output_file_name, 'w') as outfile:
            yaml.dump(cc, outfile, default_flow_style=False)

    return cc       

def run_command( args, command, nargs, parser ):
    bExecute = True
    if command =="group" and len(nargs) >= 1:
        if nargs[0] == "create":
            print "At this moment, please create project from console. "

        elif nargs[0] == "delete":
            print "At this moment, please delete project from console. "
        ()

    if command == "storage":
        if nargs[0] == "create":
            create_storage()
        elif nargs[0] == "delete":
            delete_storage()
        else:
            bExecute = False
    
    elif command == "service-accounts":
        if nargs[0] == "create":
            create_service_accounts()
        elif nargs[0] == "delete":
            delete_service_accounts()
        else:
            bExecute = False

    elif command == "vm":
        if nargs[0] == "create":
            create_vm()
        elif nargs[0] == "delete":
            delete_vm()
        elif nargs[0] == "prepare":
            prepare_vm()
        else:
            bExecute = False

    elif command == "address":
        if nargs[0] == "create":
            create_address()
        elif nargs[0] == "delete":
            delete_address()
        else:
            bExecute = False

    elif command == "firewall":
        if nargs[0] == "create":
            create_firewall()
        elif nargs[0] == "delete":
            delete_firewall()
        else:
            bExecute = False


    elif command == "genconfig":
        gen_cluster_config("cluster.yaml")

    elif command == "delete":
        # print "!!! WARNING !!! You are deleting the entire cluster %s " % config["gs_cluster"]["cluster_name"]
        response = raw_input ("!!! WARNING !!! You are performing a dangerous operation that will permanently delete the entire cluster. Please type (DELETE) in ALL CAPITALS to confirm the operation ---> ")
        if response == "DELETE":
            delete_vm()
            delete_storage()
            delete_firewall()

    else:
        bExecute = False
    
    if not bExecute:
        parser.print_help()

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
    storage [create|delete] manage gcp storage bucket
    vm [create|delete] manage gcp VM resource
    address [create|delete] create/delete external static address for infrastructure VM
    firewall [create|delete] create/delete firewall rules that attach to each VM
    service-accounts [create|delete] create/delete service accounts to access storage
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
        utils.verbose = args.verbose
    config = init_config()
    # Cluster Config
    config_cluster = os.path.join(dirpath,"gs_cluster_config.yaml")
    if os.path.exists(config_cluster):
        tmpconfig = yaml.load(open(config_cluster)) 
        if tmpconfig is not None:
            merge_config(config["gs_cluster"], tmpconfig, verbose)

    config_file = os.path.join(dirpath,"config.yaml")
    if os.path.exists(config_file):
        tmpconfig = yaml.load(open(config_file)) 
        if tmpconfig is not None and "cluster_name" in tmpconfig:
            config["gs_cluster"]["cluster_name"] = tmpconfig["cluster_name"]
        if tmpconfig is not None and "gs_cluster" in tmpconfig:
            merge_config( config["gs_cluster"], tmpconfig["gs_cluster"] )
            
    # print config
    config = update_config(config)
    # print (config)

#   with open(config_cluster, 'w') as outfile:
#     yaml.dump(config, outfile, default_flow_style=False)

    run_command( args, command, nargs, parser)


