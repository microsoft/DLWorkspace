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
from aws_params import *
from az_params import *
from ConfigUtils import *

verbose = False

def init_config():
    config = default_config_parameters
    # print "Config ===== %s" % config
    # print "GS config == %s" % default_gs_parameters 
    merge_config(config, copy.deepcopy(default_aws_parameters) )
    # print config
    return config

def get_location_string( location ):
    if location in config["aws_cluster"]["location_mapping"]:
        return config["aws_cluster"]["location_mapping"][location]
    else:
        return None

def get_region_string( location ):
    if location in config["aws_cluster"]["region_mapping"]:
        return config["aws_cluster"]["region_mapping"][location]
    else:
        return None

def get_sku( sku ):
    if sku in config["aws_cluster"]["sku_mapping"]:
        return config["aws_cluster"]["sku_mapping"][sku]
    else:
        return "regional"

def get_num_infra_nodes(location):
    return config["aws_cluster"]["infra_node_num"]

def get_num_worker_nodes(location):
    return config["aws_cluster"]["worker_node_num"]

def get_aws_ssh_key_v1(location):
    cmd1 = "cd ./deploy/sshkey/; ssh-keygen -f id_rsa.pub -e -m pem > id_rsa.pubk"
    utils.exec_cmd_local(cmd1)

def get_aws_ssh_key_v0(location):
    cmd1 = "cd ./deploy/sshkey/; ssh-keygen -f id_rsa.pub -e -m pem"
    keyinfo = utils.exec_cmd_local(cmd1)
    print keyinfo
    keylines = keyinfo.splitlines()
    sshkey = "".join(keylines[1:-1])
    return sshkey

# resource_group_name is cluster_name + ResGrp
def update_config(config, genSSH=True):
    return config

def get_locations():
    if "azure_cluster" in config and "azure_location" in config["azure_cluster"]:
        return utils.tolist( config["azure_cluster"]["azure_location"])
    elif "aws_cluster" in config and "aws_location" in config["aws_cluster"]:
        return utils.tolist( config["aws_cluster"]["aws_location"])
    else:
        return []

def get_vm_locations():
    if "aws_cluster" in config and "aws_location" in config["aws_cluster"]:
        return utils.tolist( config["aws_cluster"]["aws_location"])
    elif "azure_cluster" in config and "azure_location" in config["azure_cluster"]:
        return utils.tolist( config["azure_cluster"]["azure_location"])
    else:
        return []    

def save_config():
    # find all new entries 
    configSave = diff_config( config["aws_cluster"], default_aws_parameters["aws_cluster"])
    with open("aws_cluster_file.yaml", "w") as outfile:
        yaml.safe_dump( configSave, outfile, default_flow_style=False)


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

def import_key_pair(location):
    cmd = """
        aws ec2 import-key-pair --key-name publickey-%s \
                --public-key-material file://./deploy/sshkey/id_rsa.pub \
                """ \
            % ( location )
    output = utils.exec_cmd_local(cmd)
    print output

def delete_key_pair(location):
    cmd = """
        aws ec2 delete-key-pair --key-name publickey-%s """ \
            % ( location )
    output = utils.exec_cmd_local(cmd)
    print output

def get_security_group_name( cluster_name, location):
    group_name = "deployenv-"+cluster_name
    return group_name

def create_security_group(config, cluster_name, location):
    group_name = get_security_group_name(cluster_name, location)
    cmd = """
        aws ec2 create-security-group --group-name %s --description "security group for cluster %s"
        aws ec2 authorize-security-group-ingress --group-name %s --protocol tcp --port 0-65535 --cidr 0.0.0.0/0
                """ \
            % ( group_name, cluster_name, group_name )
    output = utils.exec_cmd_local(cmd)
    output1 = utils.exec_cmd_local("aws ec2 describe-security-groups --group-name %s " % group_name ) 
    if location not in config["aws_cluster"]:
        config["aws_cluster"][location] = {}
    merge_config( config["aws_cluster"][location], json.loads(output1))
    print config["aws_cluster"][location]["SecurityGroups"]
    
def delete_security_group(cluster_name, location):
    group_name = get_security_group_name(cluster_name, location)
    cmd = """
        aws ec2 delete-security-group --group-name %s
                """ \
            % ( group_name )
    output = utils.exec_cmd_local(cmd)
    print group_name

def hasVM(vmname, location):
    # print config["aws_cluster"][location]
    return vmname in config["aws_cluster"][location] and config["aws_cluster"][location][vmname] is not None
    

def create_aws_vm( vmname, addrname, vmsize, location, configCluster, docreate):
    if not hasVM(vmname, location):
        print "creating VM %s, size %s ..." % ( vmname, vmsize)
        uselocation = get_location_string(location)
        sgid = config["aws_cluster"][location]["SecurityGroups"][0]["GroupId"]
        # print configCluster
        cmd = """
            aws ec2 run-instances --image-id %s --count 1 \
                    --security-group-ids %s \
                    --key-name publickey-%s \
                    --region %s \
                    --instance-type  %s \
                    --associate-public-ip-address %s 
                    """ \
                % ( configCluster["vm_image"], sgid, location, location, vmsize, configCluster["vm_storage_sku"] )
        # print cmd
        output = utils.exec_cmd_local(cmd)
        outputjson = json.loads(output)
        config["aws_cluster"][location][vmname] = outputjson["Instances"][0]
        # print output
        # print config["aws_cluster"][location][vmname] 

def get_public_dns( vmname, location):
    configVm = config["aws_cluster"][location][vmname]
    publicDNS = configVm["PublicDnsName"]
    idx = publicDNS.find(".")
    if idx >= 0:
        return publicDNS[:idx], publicDNS[idx+1:]
    else:
        return publicDNS, None

def delete_aws_vm( vmname, vmsize, location, configCluster, docreate):
    if vmname in config["aws_cluster"][location]:
        print "delete VM %s" % ( vmname)
        instanceid = config["aws_cluster"][location][vmname]["InstanceId"]
        cmd = """
            aws ec2 terminate-instances --instance-ids %s \
                    """ \
                % ( instanceid )
        output = utils.exec_cmd_local(cmd)
        print (output)  
        del config["aws_cluster"][location][vmname]
       

def create_vm_cluster(location, configCluster, docreate):
    # print "configCluster = %s " % configCluster
    # print "location = %s" % location
    infra_node_num = configCluster["infra_node_num"]
    worker_node_num = configCluster["worker_node_num"]
    cluster_name = config["aws_cluster"]["cluster_name"]
    import_key_pair(location)
    create_security_group(config, cluster_name, location)
    if "machines" not in config:
        config["machines"] = {}
    for i in range(infra_node_num):
        vmname = "%s-infra%02d" % (cluster_name, i+1)
        addrname = get_infra_address(location, i)
        create_aws_vm(vmname, addrname, configCluster["infra_vm_size"], location, configCluster, docreate )
        config["machines"][vmname] = { "role": "infrastructure"}
    for i in range(worker_node_num):
        vmname = "%s-worker%02d" % (cluster_name, i+1)
        create_aws_vm(vmname, None, configCluster["worker_vm_size"], location, configCluster, docreate )
        config["machines"][vmname] = { "role": "worker"}      

def delete_vm_cluster(location, configCluster, docreate):
    # print "configCluster = %s " % configCluster
    infra_node_num = configCluster["infra_node_num"]
    worker_node_num = configCluster["worker_node_num"]
    cluster_name = config["aws_cluster"]["cluster_name"]
    for i in range(infra_node_num):
        vmname = "%s-infra%02d" % (cluster_name, i+1)
        delete_aws_vm(vmname, configCluster["infra_vm_size"], location, configCluster, docreate )
    for i in range(worker_node_num):
        vmname = "%s-worker%02d" % (cluster_name, i+1)
        delete_aws_vm(vmname, configCluster["worker_vm_size"], location, configCluster, docreate )        
    delete_key_pair(location)
    delete_security_group(cluster_name, location)

def find_vm_description( jsonvms, instanceid ):
    for reservation in jsonvms["Reservations"]:
        instances = reservation["Instances"]
        for onevm in instances:
            if onevm["InstanceId"] == instanceid:
                return onevm
    return None

def update_vm_config( jsonvms, location, vmname):
    if hasVM(vmname, location):
        instanceid = config["aws_cluster"][location][vmname]["InstanceId"]
        vmconfig = find_vm_description( jsonvms, instanceid )
        print "Find VM of ... %s ==> %s " % ( instanceid, vmconfig)
        if vmconfig is not None:
            config["aws_cluster"][location][vmname] = vmconfig
            # print vmconfig
            publicDns, domain = get_public_dns(vmname, location)
            if domain is not None:
                print "VM %s ==== %s.%s" %( vmname, publicDns, domain)
            else:
                print "VM %s ==== public DNS not available"

def describe_vm_cluster(location, configCluster, docreate):
    output = utils.exec_cmd_local("aws ec2 describe-instances")
    jsonvms = json.loads(output)
    # print "configCluster = %s " % configCluster
    infra_node_num = configCluster["infra_node_num"]
    worker_node_num = configCluster["worker_node_num"]
    cluster_name = config["aws_cluster"]["cluster_name"]
    for i in range(infra_node_num):
        vmname = "%s-infra%02d" % (cluster_name, i+1)
        update_vm_config( jsonvms, location, vmname)
    for i in range(worker_node_num):
        vmname = "%s-worker%02d" % (cluster_name, i+1)
        update_vm_config( jsonvms, location, vmname)

def get_address_name( location):
    cluster_name = config["aws_cluster"]["cluster_name"]
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
    locations = get_vm_locations()
    for location in locations:
        configCluster = config["aws_cluster"]
        # print "Location = %s, config = %s" %( location, configCluster )
        create_vm_cluster( location, configCluster, docreate)
    save_config()

def describe_vm( docreate = True):
    locations = get_vm_locations()
    for location in locations:
        configCluster = config["aws_cluster"]
        # print "Location = %s, config = %s" %( location, configCluster )
        describe_vm_cluster( location, configCluster, docreate)
    save_config()    

def delete_vm( docreate = True):
    locations = get_vm_locations()
    for location in locations:
        configCluster = config["aws_cluster"]
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
    cc["etcd_node_num"] = config["aws_cluster"]["infra_node_num"]
    cc["useclusterfile"] = True
    cc["deploydockerETCD"] = False
    cc["platform-scripts"] = "ubuntu"
    cc["basic_auth"] = "%s,admin,1000" % uuid.uuid4().hex[:12]
    cc["machines"] = {}
    cc["network"] = {}
    location = get_vm_locations()[0]
    for i in range(int(config["aws_cluster"]["infra_node_num"])):
        vmname = "%s-infra%02d" % (config["aws_cluster"]["cluster_name"], i+1)
        dnsname, domain = get_public_dns(vmname, location)
        cc["network"]["domain"] = domain
        cc["machines"][dnsname]= {"role": "infrastructure"}
    for i in range(int(config["aws_cluster"]["worker_node_num"])):
        vmname = "%s-worker%02d" % (config["aws_cluster"]["cluster_name"], i+1)
        dnsname, domain = get_public_dns(vmname, location)
        cc["network"]["domain"] = domain
        cc["machines"][dnsname]= {"role": "worker"}
    cc["admin_username"] = config["aws_cluster"]["default_admin_username"]

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
        elif nargs[0] == "describe":
            describe_vm()
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
    parser = argparse.ArgumentParser( prog='aws_tools.py',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent('''\
Create and manage AWS cluster.

Command:
    storage [create|delete] manage gcp storage bucket
    vm [create|delete|describe] manage gcp VM resource
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
    config_cluster = os.path.join(dirpath,"aws_cluster_file.yaml")
    if os.path.exists(config_cluster):
        tmpconfig = yaml.load(open(config_cluster)) 
        if tmpconfig is not None:
            merge_config(config["aws_cluster"], tmpconfig)

    config_file = os.path.join(dirpath,"config.yaml")
    if os.path.exists(config_file):
        tmpconfig = yaml.load(open(config_file)) 
        if tmpconfig is not None and "cluster_name" in tmpconfig:
            config["aws_cluster"]["cluster_name"] = tmpconfig["cluster_name"]
        if tmpconfig is not None and "aws_cluster" in tmpconfig:
            merge_config( config["aws_cluster"], tmpconfig["aws_cluster"] )
            
    # print config
    config = update_config(config)
    # print (config)

#   with open(config_cluster, 'w') as outfile:
#     yaml.dump(config, outfile, default_flow_style=False)

    run_command( args, command, nargs, parser)


