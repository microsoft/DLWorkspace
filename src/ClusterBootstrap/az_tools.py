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
import string

from os.path import expanduser

import yaml
from jinja2 import Environment, FileSystemLoader, Template
import base64
import tempfile

from shutil import copyfile, copytree
import urllib
import socket
import utils
from az_params import *
from params import *

verbose = False
no_execution = False

# These are the default configuration parameter


def init_config():
    config = {}
    for k, v in default_config_parameters.iteritems():
        config[k] = v
    for k, v in default_az_parameters.iteritems():
        config[k] = v
    # print config
    # exit()
    return config


def merge_config(config1, config2, verbose):
    for entry in config2:
        if entry in config1:
            if isinstance(config1[entry], dict):
                if verbose:
                    print("Merge entry %s " % entry)
                merge_config(config1[entry], config2[entry], verbose)
            else:
                if verbose:
                    print("Entry %s == %s " % (entry, config2[entry]))
                config1[entry] = config2[entry]
        else:
            if verbose:
                print("Entry %s == %s " % (entry, config2[entry]))
            config1[entry] = config2[entry]


def update_config(config, genSSH=True):
    config["azure_cluster"]["resource_group_name"] = config[
        "azure_cluster"]["cluster_name"] + "ResGrp"
    config["azure_cluster"]["vnet_name"] = config[
        "azure_cluster"]["cluster_name"] + "-VNet"
    config["azure_cluster"]["storage_account_name"] = config[
        "azure_cluster"]["cluster_name"] + "storage"
    config["azure_cluster"]["nsg_name"] = config[
        "azure_cluster"]["cluster_name"] + "-nsg"

    if int(config["azure_cluster"]["nfs_node_num"]) > 0:
        config["azure_cluster"]["nfs_nsg_name"] = config[
        "azure_cluster"]["cluster_name"] + "-nfs-nsg"
    config["azure_cluster"]["sql_server_name"] = config[
        "azure_cluster"]["cluster_name"] + "sqlserver"
    config["azure_cluster"]["sql_admin_name"] = config[
        "azure_cluster"]["cluster_name"] + "sqladmin"
    config["azure_cluster"]["sql_database_name"] = config[
        "azure_cluster"]["cluster_name"] + "sqldb"

    if "sql_admin_password" not in config["azure_cluster"]:
        config["azure_cluster"]["sql_admin_password"] = uuid.uuid4().hex + \
            "12!AB"

    if (genSSH):
        if (os.path.exists('./deploy/sshkey/id_rsa.pub')):
            f = open('./deploy/sshkey/id_rsa.pub')
            config["azure_cluster"]["sshkey"] = f.read()
            f.close()
        else:
            os.system("mkdir -p ./deploy/sshkey")
            if not os.path.exists("./deploy/sshkey/azure_id_rsa"):
                os.system(
                    "ssh-keygen -t rsa -b 4096 -f ./deploy/sshkey/azure_id_rsa -P ''")
            f = open('./deploy/sshkey/azure_id_rsa.pub')
            config["azure_cluster"]["sshkey"] = f.read()
            f.close()

    return config

def create_vm_pwd(vmname, vm_ip, vm_size, use_private_ip, pwd):
    auth = ""
    if pwd is not None:
        auth = """--authentication-type password --admin-password '%s' """ % pwd
    else:
        auth = """--authentication-type ssh --ssh-key-value "%s" """ % config["azure_cluster"]["sshkey"]
    privateip = ""
    if use_private_ip:
        privateip = """--private-ip-address %s""" % vm_ip
    cmd = """
        az vm create --resource-group %s \
                    --name %s \
                    --image %s \
                    %s \
                    --public-ip-address-dns-name %s \
                    --location %s \
                    --size %s \
                    --vnet-name %s \
                    --subnet mySubnet \
                    --nsg %s \
                    --admin-username %s \
                    --storage-sku %s \
                    --data-disk-sizes-gb 2047 \
                    %s \
        """ % (config["azure_cluster"]["resource_group_name"],
                vmname,
                config["azure_cluster"]["vm_image"],
                privateip,
                vmname,
                config["azure_cluster"]["azure_location"],
                vm_size,
                config["azure_cluster"]["vnet_name"],
                config["azure_cluster"]["nsg_name"],
                config["cloud_config"]["default_admin_username"],
                config["azure_cluster"]["vm_storage_sku"],
                auth)

    if verbose:
        print(cmd)
    if not no_execution:
        output = utils.exec_cmd_local(cmd)
        print(output)

def create_vm(vmname, vm_ip, role, vm_size):
    specify_priv_IP = role in ["worker","nfs"]
    nsg = "nfs_nsg_name" if role == "nfs" else "nsg_name"
    cmd = """
        az vm create --resource-group %s \
                 --name %s \
                 --image %s \
                 --generate-ssh-keys  \
                 --private-ip-address %s \
                 --public-ip-address-dns-name %s \
                 --location %s \
                 --size %s \
                 --vnet-name %s \
                 --subnet mySubnet \
                 --nsg %s \
                 --admin-username %s \
                 --storage-sku %s \
                 --data-disk-sizes-gb 2047 \
                 --ssh-key-value "%s"
        """ % (config["azure_cluster"]["resource_group_name"],
               vmname,
               config["azure_cluster"]["vm_image"],
               vm_ip,
               vmname,
               config["azure_cluster"]["azure_location"],
               vm_size,
               config["azure_cluster"]["vnet_name"],
               config["azure_cluster"][nsg],
               config["cloud_config"]["default_admin_username"],
               config["azure_cluster"]["vm_storage_sku"],
               config["azure_cluster"]["sshkey"]) if not specify_priv_IP else """
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
                 --admin-username %s \
                 --storage-sku %s \
                 --data-disk-sizes-gb 2047 \
                 --ssh-key-value "%s"
        """ % (config["azure_cluster"]["resource_group_name"],
               vmname,
               config["azure_cluster"]["vm_image"],
               vmname,
               config["azure_cluster"]["azure_location"],
               vm_size,
               config["azure_cluster"]["vnet_name"],
               config["azure_cluster"][nsg],
               config["cloud_config"]["default_admin_username"],
               config["azure_cluster"]["vm_storage_sku"],
               config["azure_cluster"]["sshkey"])
    # Try remove static IP
    #                 --public-ip-address-allocation static \
    if verbose:
        print(cmd)
    if not no_execution:
        output = utils.exec_cmd_local(cmd)
        print(output)


def create_group():
    cmd = """
        az group create --name %s --location %s
        """ % (config["azure_cluster"]["resource_group_name"], config["azure_cluster"]["azure_location"])
    if verbose:
        print(cmd)
    if not no_execution:
        output = utils.exec_cmd_local(cmd)
        print(output)


def create_sql():
    cmd = """
        az sql server create --resource-group %s \
                 --location %s \
                 --name %s \
                 -u %s \
                 -p %s
        """ % (config["azure_cluster"]["resource_group_name"],
               config["azure_cluster"]["azure_location"],
               config["azure_cluster"]["sql_server_name"],
               config["azure_cluster"]["sql_admin_name"],
               config["azure_cluster"]["sql_admin_password"])
    if verbose:
        print(cmd)
    if not no_execution:
        output = utils.exec_cmd_local(cmd)
        print(output)

    cmd = """
        az sql server firewall-rule create --resource-group %s \
                 --server %s \
                 --name All \
                 --start-ip-address 0.0.0.0 \
                 --end-ip-address 255.255.255.255
        """ % (config["azure_cluster"]["resource_group_name"],
               config["azure_cluster"]["sql_server_name"])
    if verbose:
        print(cmd)
    if not no_execution:
        output = utils.exec_cmd_local(cmd)
        print(output)


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
    if verbose:
        print(cmd)
    if not no_execution:
        output = utils.exec_cmd_local(cmd)
        print(output)


def create_file_share():
    cmd = """
        az storage account show-connection-string \
            -n %s \
            -g %s \
            --query 'connectionString' \
            -o tsv
        """ % (config["azure_cluster"]["storage_account_name"], config["azure_cluster"]["resource_group_name"])
    if not no_execution:
        output = utils.exec_cmd_local(cmd)
        print(output)

    cmd = """
        az storage share create \
            --name %s \
            --quota 2048 \
            --connection-string '%s'
        """ % (config["azure_cluster"]["file_share_name"], output)
    if verbose:
        print(cmd)
    if not no_execution:
        output = utils.exec_cmd_local(cmd)
        print(output)


def create_vnet():
    cmd = """
        az network vnet create \
            --resource-group %s \
            --name %s \
            --address-prefix %s \
            --subnet-name mySubnet \
            --subnet-prefix %s
        """ % ( config["azure_cluster"]["resource_group_name"],
                config["azure_cluster"]["vnet_name"],
                config["cloud_config"]["vnet_range"],
                config["cloud_config"]["vnet_range"])
    if verbose:
        print(cmd)
    if not no_execution:
        output = utils.exec_cmd_local(cmd)
        print(output)


def create_nsg():
    if "source_addresses_prefixes" in config["cloud_config"]["dev_network"]:
        source_addresses_prefixes = config["cloud_config"][
            "dev_network"]["source_addresses_prefixes"]
        if isinstance(source_addresses_prefixes, list):
            source_addresses_prefixes = " ".join(source_addresses_prefixes)
    else:
        print "Please setup source_addresses_prefixes in config.yaml, otherwise, your cluster cannot be accessed"
        exit()
    cmd = """
        az network nsg create \
            --resource-group %s \
            --name %s
        """ % ( config["azure_cluster"]["resource_group_name"],
                config["azure_cluster"]["nsg_name"])
    if verbose:
        print(cmd)
    if not no_execution:
        output = utils.exec_cmd_local(cmd)
        print(output)

    if "tcp_port_ranges" in config["cloud_config"]:
        cmd = """
            az network nsg rule create \
                --resource-group %s \
                --nsg-name %s \
                --name allowalltcp \
                --protocol tcp \
                --priority 1000 \
                --destination-port-ranges %s \
                --access allow
            """ % ( config["azure_cluster"]["resource_group_name"],
                    config["azure_cluster"]["nsg_name"],
                    config["cloud_config"]["tcp_port_ranges"]
                    )
        if not no_execution:
            output = utils.exec_cmd_local(cmd)
            print(output)

    if "udp_port_ranges" in config["cloud_config"]:
        cmd = """
            az network nsg rule create \
                --resource-group %s \
                --nsg-name %s \
                --name allowalludp \
                --protocol udp \
                --priority 1010 \
                --destination-port-ranges %s \
                --access allow
            """ % ( config["azure_cluster"]["resource_group_name"],
                    config["azure_cluster"]["nsg_name"],
                    config["cloud_config"]["udp_port_ranges"]
                    )
        if not no_execution:
            output = utils.exec_cmd_local(cmd)
            print(output)

    cmd = """
        az network nsg rule create \
            --resource-group %s \
            --nsg-name %s \
            --name allowdevtcp \
            --protocol tcp \
            --priority 900 \
            --destination-port-ranges %s \
            --source-address-prefixes %s \
            --access allow
        """ % ( config["azure_cluster"]["resource_group_name"],
                config["azure_cluster"]["nsg_name"],
                config["cloud_config"]["dev_network"]["tcp_port_ranges"],
                source_addresses_prefixes
                )
    if not no_execution:
        output = utils.exec_cmd_local(cmd)
        print(output)

def create_nfs_nsg():
    if "source_addresses_prefixes" in config["cloud_config"]["dev_network"]:
        source_addresses_prefixes = config["cloud_config"][
            "dev_network"]["source_addresses_prefixes"]
    else:
        print "Please setup source_addresses_prefixes in config.yaml, otherwise, your cluster cannot be accessed"
        exit()
    cmd = """
        az network nsg create \
            --resource-group %s \
            --name %s
        """ % ( config["azure_cluster"]["resource_group_name"],
                config["azure_cluster"]["nfs_nsg_name"])
    if verbose:
        print(cmd)
    if not no_execution:
        output = utils.exec_cmd_local(cmd)
        print(output)

    print type(config["cloud_config"]["nfs_ssh"]["source_ips"]), config["cloud_config"]["nfs_ssh"]["source_ips"],type(source_addresses_prefixes), source_addresses_prefixes
    cmd = """
        az network nsg rule create \
            --resource-group %s \
            --nsg-name %s \
            --name allow_ssh\
            --priority 900 \
            --destination-port-ranges %s \
            --source-address-prefixes %s \
            --access allow
        """ % ( config["azure_cluster"]["resource_group_name"],
                config["azure_cluster"]["nfs_nsg_name"],
                config["cloud_config"]["nfs_ssh"]["port"],
                " ".join(config["cloud_config"]["nfs_ssh"]["source_ips"] + source_addresses_prefixes),
                )
    if not no_execution:
        output = utils.exec_cmd_local(cmd)
        print(output)

    cmd = """
        az network nsg rule create \
            --resource-group %s \
            --nsg-name %s \
            --name allow_share \
            --priority 1000 \
            --source-address-prefixes %s \
            --destination-port-ranges \'*\' \
            --access allow
        """ % ( config["azure_cluster"]["resource_group_name"],
                config["azure_cluster"]["nfs_nsg_name"],
                " ".join(config["cloud_config"]["nfs_share"]["source_ips"]),
                )
    if not no_execution:
        output = utils.exec_cmd_local(cmd)
        print(output)


def delete_group():
    cmd = """
        az group delete -y --name %s
        """ % (config["azure_cluster"]["resource_group_name"])
    if verbose:
        print(cmd)
    if not no_execution:
        output = utils.exec_cmd_local(cmd)
        print(output)


def get_vm_ip(i, role):
    vnet_range = config["cloud_config"]["vnet_range"]
    vnet_ip = vnet_range.split("/")[0]
    vnet_ips = vnet_ip.split(".")
    if role in ["worker", "nfs"]:
        return vnet_ips[0] + "." + vnet_ips[1] + "." + "1" + "." + str(i + 1)
    elif role == "dev":
        return vnet_ips[0] + "." + vnet_ips[1] + "." + "255" + "." + str(int(config["azure_cluster"]["infra_node_num"]) + 1)
    else:
        # 192.168.0 is reserved.
        return vnet_ips[0] + "." + vnet_ips[1] + "." + "255" + "." + str(i + 1)


def create_cluster(arm_vm_password=None):
    bSQLOnly = (config["azure_cluster"]["infra_node_num"] <= 0)
    assert int(config["azure_cluster"]["nfs_node_num"]) >= len(config["cloud_config"]["nfs_suffixes"])
    print "creating resource group..."
    create_group()
    if not bSQLOnly:
        if "file_share" in config["azure_cluster"]:
            print "creating storage account..."
            create_storage_account()
            print "creating file share..."
            create_file_share()
        print "creating vnet..."
        create_vnet()
        print "creating network security group..."
        create_nsg()
        if int(config["azure_cluster"]["nfs_node_num"]) > 0:
            create_nfs_nsg()
    if useSqlAzure():
        print "creating sql server and database..."
        create_sql()

    if arm_vm_password is not None:
        # dev box, used in extreme condition when there's only one public IP available, then would use dev in cluster to bridge-connect all of them
        create_vm_param(0, "dev", config["azure_cluster"]["infra_vm_size"],
                        True, arm_vm_password)
    for i in range(int(config["azure_cluster"]["infra_node_num"])):
        create_vm_param(i, "infra", config["azure_cluster"]["infra_vm_size"],
                        arm_vm_password is not None, arm_vm_password)
    for i in range(int(config["azure_cluster"]["worker_node_num"])):
        create_vm_param(i, "worker", config["azure_cluster"]["worker_vm_size"],
                        arm_vm_password is not None, arm_vm_password)
    # create nfs server if specified.
    for i in range(int(config["azure_cluster"]["nfs_node_num"])):
        if i < len(config["azure_cluster"]["nfs_suffixes"]):
            create_vm_role_suffix(i, "nfs", config["azure_cluster"]["nfs_vm_size"], 
                config["azure_cluster"]["nfs_suffixes"][i], arm_vm_password)
        else:
            create_vm_param(i, "nfs", config["azure_cluster"]["nfs_vm_size"],
                        arm_vm_password is not None, arm_vm_password)

def create_vm_param(i, role, vm_size, no_az=False, arm_vm_password=None):
    if role in ["worker","nfs"]:
        vmname = "{}-{}".format(config["azure_cluster"]["cluster_name"], role) + ("{:02d}".format(i+1) if no_az else '-'+random_str(6))
    elif role == "infra":
        vmname = "%s-infra%02d" % (config["azure_cluster"]
                                   ["cluster_name"], i + 1)
    elif role == "dev":
        vmname = "%s-dev" % (config["azure_cluster"]["cluster_name"])
    print "creating VM %s..." % vmname
    vm_ip = get_vm_ip(i, role)
    if arm_vm_password is not None:
        create_vm_pwd(vmname, vm_ip, vm_size, not role in ["worker","nfs"], arm_vm_password)
    else:
        create_vm(vmname, vm_ip, role, vm_size)
    return vmname

def create_vm_role_suffix(i, role, vm_size, suffix, arm_vm_password=None):
    vmname = "{}-{}-".format(config["azure_cluster"]["cluster_name"], role) + suffix
    print "creating VM %s..." % vmname
    vm_ip = get_vm_ip(i, role)
    if arm_vm_password is not None:
        create_vm_pwd(vmname, vm_ip, vm_size, not role in ["worker","nfs"], arm_vm_password)
    else:
        create_vm(vmname, vm_ip, role, vm_size)
    return vmname

def useSqlAzure():
    if "datasource" in config["azure_cluster"]:
        if config["azure_cluster"]["datasource"] == "MySQL":
            return False
        else:
            return True
    else:
        return True


def useAzureFileshare():
    return ("file_share_name" in config["azure_cluster"]) or ("isacs" in config and config["isacs"])


def scale_up_vm(groupName, delta):
    with open("deploy/scaler.yaml") as f:
        scaler_config = yaml.load(f)

    for vmSize, nodeGroup in scaler_config["node_groups"].items():
        if vmSize == groupName:
            # Only checkpoint newly scaled up nodes.
            nodeGroup["last_scaled_up_nodes"] = []
            for i in range(delta):
                vmName = create_vm_param(i, True, False, vmSize)
                nodeGroup["last_scaled_up_nodes"].append(vmName)
            break

    with open("deploy/scaler.yaml", "w") as f:
        yaml.dump(scaler_config, f)


def list_vm(bShow=True):
    cmd = """
        az vm list --resource-group %s
        """ % (config["azure_cluster"]["resource_group_name"] )
    if verbose:
        print(cmd)
    output = utils.exec_cmd_local(cmd)
    allvm = json.loads(output)
    vminfo = {}
    for onevm in allvm:
        vmname = onevm["name"]
        print "VM ... %s" % vmname
        cmd1 = """ az vm show -d -g %s -n %s""" % (
            config["azure_cluster"]["resource_group_name"], vmname)
        output1 = utils.exec_cmd_local(cmd1)
        json1 = json.loads(output1)
        vminfo[vmname] = json1
        if bShow:
            print json1
    return vminfo


def vm_interconnects():
    vminfo = list_vm(False)
    ports = []
    for name, onevm in vminfo.iteritems():
        ports.append(onevm["publicIps"] + "/32")
    portinfo = " ".join(ports)
    cmd = """
        az network nsg rule create \
            --resource-group %s \
            --nsg-name %s \
            --name tcpinterconnect \
            --protocol tcp \
            --priority 850 \
            --destination-port-ranges %s \
            --source-address-prefixes %s \
            --access allow
        """ % ( config["azure_cluster"]["resource_group_name"],
                config["azure_cluster"]["nsg_name"],
                config["cloud_config"]["inter_connect"]["tcp_port_ranges"],
                portinfo
                )
    if verbose:
        print cmd
    output = utils.exec_cmd_local(cmd)
    print(output)


def delete_vm(vmname):
    cmd = """
        az vm delete --resource-group %s \
                 --name %s \
                 --yes
        """ % (config["azure_cluster"]["resource_group_name"],
               vmname)

    if verbose:
        print(cmd)
    output = utils.exec_cmd_local(cmd)
    print(output)


def delete_nic(nicname):
    cmd = """
        az network nic delete --resource-group %s \
                --name %s \
        """ % (config["azure_cluster"]["resource_group_name"],
               nicname)
    if verbose:
        print(cmd)
    output = utils.exec_cmd_local(cmd)
    print(output)


def delete_public_ip(ip):
    cmd = """
        az network public-ip delete --resource-group %s \
                 --name %s \
        """ % (config["azure_cluster"]["resource_group_name"],
               ip)

    if verbose:
        print(cmd)
    output = utils.exec_cmd_local(cmd)
    print(output)


def delete_disk(diskID):
    cmd = """
        az disk delete --resource-group %s \
                 --name %s \
                 --yes \
        """ % (config["azure_cluster"]["resource_group_name"],
               diskID)

    if verbose:
        print(cmd)
    output = utils.exec_cmd_local(cmd)
    print(output)


def get_disk_from_vm(vmname):
    cmd = """
        az vm show -g %s -n %s --query "storageProfile.osDisk.managedDisk.id" -o tsv \
        """ % (config["azure_cluster"]["resource_group_name"],
               vmname)

    if verbose:
        print(cmd)
    output = utils.exec_cmd_local(cmd)

    return output.split("/")[-1].strip('\n')

def gen_cluster_config(output_file_name, output_file=True, no_az=False):
    bSQLOnly = (config["azure_cluster"]["infra_node_num"] <= 0)
    if useAzureFileshare() and not no_az:
        # theoretically it could be supported, but would require storage account to be created first in nested template and then
        # https://docs.microsoft.com/en-us/azure/azure-resource-manager/resource-group-template-functions-resource#listkeys
        # could be used to access storage keys - these could be assigned as variable which gets passed into main deployment template
        raise Exception("Azure file share not currently supported with no_az")
    if useAzureFileshare():
        cmd = """
            az storage account show-connection-string \
                -n %s \
                -g %s \
                --query 'connectionString' \
                -o tsv
            """ % (config["azure_cluster"]["storage_account_name"], config["azure_cluster"]["resource_group_name"])
        output = utils.exec_cmd_local(cmd)
        reoutput = re.search('AccountKey\=.*$', output)
        file_share_key = None
        if reoutput is not None:
            file_share_key = reoutput.group(0).replace("AccountKey=", "")

        reoutput = re.search('AccountName\=.*;', output)
        file_share_account_name = None
        if reoutput is not None:
            file_share_account_name = reoutput.group(
                0).replace("AccountName=", "")[:-1]

    cc = {}
    cc["cluster_name"] = config["azure_cluster"]["cluster_name"]
    if not bSQLOnly:
        cc["etcd_node_num"] = config["azure_cluster"]["infra_node_num"]

    if useSqlAzure():
        cc["sqlserver-hostname"] = "tcp:%s.database.windows.net" % config[
            "azure_cluster"]["sql_server_name"]
        cc["sqlserver-username"] = config["azure_cluster"]["sql_admin_name"]
        cc["sqlserver-password"] = config["azure_cluster"]["sql_admin_password"]
        cc["sqlserver-database"] = config["azure_cluster"]["sql_database_name"]
    if not bSQLOnly:
        cc["admin_username"] = config["cloud_config"]["default_admin_username"]
        if useAzureFileshare():
            cc["workFolderAccessPoint"] = "file://%s.file.core.windows.net/%s/work/" % (
                config["azure_cluster"]["storage_account_name"], config["azure_cluster"]["file_share_name"])
            cc["dataFolderAccessPoint"] = "file://%s.file.core.windows.net/%s/storage/" % (
                config["azure_cluster"]["storage_account_name"], config["azure_cluster"]["file_share_name"])
            cc["smbUsername"] = file_share_account_name
            cc["smbUserPassword"] = file_share_key
    cc["useclusterfile"] = True
    cc["deploydockerETCD"] = False
    cc["platform-scripts"] = "ubuntu"
    cc["basic_auth"] = "%s,admin,1000" % uuid.uuid4().hex[:16]
    if not bSQLOnly:
        cc["network"] = {"domain": "%s.cloudapp.azure.com" %
                         config["azure_cluster"]["azure_location"]}
    cc["machines"] = {}
    for i in range(int(config["azure_cluster"]["infra_node_num"])):
        vmname = "%s-infra%02d" % (config["azure_cluster"]
                                   ["cluster_name"], i + 1)
        cc["machines"][vmname] = {"role": "infrastructure", "private-ip": get_vm_ip(i, "infra")}

    # Generate the workers in machines.
    vm_list = []
    if not no_az:
        vm_list = get_vm_list_by_grp()
    else:
        vm_list = get_vm_list_by_enum()

    vm_ip_names = get_vm_private_ip()
    vm_ip_names = sorted(vm_ip_names, key = lambda x:x['name'])
    
    sku_mapping = config["sku_mapping"]

    for vm in vm_list:
        vmname = vm["name"]
        if "-worker" in vmname:
            if isNewlyScaledMachine(vmname):
                cc["machines"][vmname] = {
                    "role": "worker", "scaled": True,
                    "node-group": vm["vmSize"],"gpu-type":sku_mapping[vm["vmSize"]]["gpu-type"]}
            else:
                cc["machines"][vmname] = {
                    "role": "worker",
                    "node-group": vm["vmSize"],"gpu-type":sku_mapping[vm["vmSize"]]["gpu-type"]}
    nfs_nodes = []
    for vm in vm_list:
        vmname = vm["name"]
        if "-nfs" in vmname:
            cc["machines"][vmname] = {
                "role": "nfs",
                "node-group": vm["vmSize"]}
    
    # Dilemma : Before the servers got created, you don't know there name, cannot specify which server does a mountpoint config group belongs to
    if int(config["azure_cluster"]["nfs_node_num"]) > 0:
        nfs_names2ip = {rec['name']:rec['privateIP'][0] for rec in vm_ip_names if "-nfs" in rec['name']}
    else:
        nfs_names2ip = {rec['name']:rec['privateIP'][0] for rec in vm_ip_names if "infra" in rec['name']}
    if not bSQLOnly:
        # Require explicit authorization setting.
        # cc["WinbindServers"] = []
        # cc["WebUIauthorizedGroups"] = ['MicrosoftUsers']
        cc["mountpoints"] = {}
        if useAzureFileshare():
            cc["mountpoints"]["rootshare"]["type"] = "azurefileshare"
            cc["mountpoints"]["rootshare"]["accountname"] = config[
                "azure_cluster"]["storage_account_name"]
            cc["mountpoints"]["rootshare"]["filesharename"] = config[
                "azure_cluster"]["file_share_name"]
            cc["mountpoints"]["rootshare"]["mountpoints"] = ""
            if file_share_key is not None:
                cc["mountpoints"]["rootshare"]["accesskey"] = file_share_key
        else:
            named_nfs_suffix = set(config["azure_cluster"]["nfs_suffixes"] if "nfs_suffixes" in config["azure_cluster"] else [])
            used_nfs_suffix = set([nfs_cnf["server_suffix"] for nfs_cnf in config["cloud_config"]["nfs_svr_setup"] if "server_suffix" in nfs_cnf])
            assert (used_nfs_suffix - named_nfs_suffix) == set() and "suffix not in nfs_suffixes list!"
            assert len(nfs_names2ip) >= len(config["cloud_config"]["nfs_svr_setup"]) and "More NFS config items than #. of NFS server"
            suffix2used_nfs = {suffix: "{}-nfs-{}".format(config["cluster_name"], suffix) for suffix in used_nfs_suffix}
            # unused, either node without name suffix or those with suffix but not specified in any nfs_svr_setup item
            unused_nfs = sorted([s for s in nfs_names2ip.keys() if s not in suffix2used_nfs.values()])
            unused_ID_cnt = 0
            for nfs_cnf in config["cloud_config"]["nfs_svr_setup"]:
                if "server_suffix" in nfs_cnf:
                    server_name = suffix2used_nfs[nfs_cnf["server_suffix"]]
                else:
                    server_name = unused_nfs[unused_ID_cnt]
                    unused_ID_cnt += 1
                server_ip = nfs_names2ip[server_name]
                for mntname, mntcnf in nfs_cnf["mnt_point"].items():
                    if mntname in cc["mountpoints"]:
                        print("Warning, duplicated mountpoints item name {}, skipping".format(mntname))
                        continue
                    cc["mountpoints"][mntname] = mntcnf
                    cc["mountpoints"][mntname]["type"] = "nfs"
                    cc["mountpoints"][mntname]["server"] = server_ip
                    cc["mountpoints"][mntname]["servername"] = server_name
    if output_file:
        print yaml.dump(cc, default_flow_style=False)
        with open(output_file_name, 'w') as outfile:
            yaml.dump(cc, outfile, default_flow_style=False)

    return cc

def isNewlyScaledMachine(vmName):
    scaler_config_file = os.path.join(dirpath, "deploy/scaler.yaml")
    if os.path.exists(scaler_config_file):
        scaler_config = yaml.load(open(scaler_config_file))
        for vmSize, nodeGroup in scaler_config["node_groups"].items():
            for nodeName in nodeGroup["last_scaled_up_nodes"]:
                if nodeName == vmName:
                    return True
    # If scaler.yaml is not found, then it should never be a scaled node.
    return False


def get_vm_list_by_grp():
    cmd = """
        az vm list --output json -g %s --query '[].{name:name, vmSize:hardwareProfile.vmSize}'

        """ % (config["azure_cluster"]["resource_group_name"])

    if verbose:
        print(cmd)
    output = utils.exec_cmd_local(cmd)

    return utils.json_loads_byteified(output)

def get_vm_private_ip():
    cmd = """
        az vm list-ip-addresses -g %s --output json --query '[].{name:virtualMachine.name, privateIP:virtualMachine.network.privateIpAddresses}'

        """ % (config["azure_cluster"]["resource_group_name"])
    if verbose:
        print(cmd)
    output = utils.exec_cmd_local(cmd)
    return utils.json_loads_byteified(output)

# simply enumerate to get vm list
def get_vm_list_by_enum():
    vm_list = []
    for role in ["worker","nfs"]:
        for i in range(int(config["azure_cluster"]["{}_node_num".format(role)])):
            vminfo = {}
            vminfo["name"] = "{}-{}{:02d}".format(config["azure_cluster"]["cluster_name"], role, i + 1)
            vminfo["vmSize"] = config["azure_cluster"]["{}_vm_size".format(role)]
            vm_list.append(vminfo)
    return vm_list

def random_str(length):
    return ''.join(random.choice(string.lowercase) for x in range(length))


def delete_cluster():
    print "!!! WARNING !!! Resource group {0} will be deleted".format(config["azure_cluster"]["resource_group_name"])
    response = raw_input(
        "!!! WARNING !!! You are performing a dangerous operation that will permanently delete the entire Azure DL Workspace cluster. Please type (DELETE) in ALL CAPITALS to confirm the operation ---> ")
    if response == "DELETE":
        delete_group()


def run_command(args, command, nargs, parser):
    if command == "create":
        # print config["azure_cluster"]["infra_vm_size"]
        create_cluster(args.arm_password)
        vm_interconnects()

    elif command == "list":
        list_vm()

    elif command == "interconnect":
        vm_interconnects()

    elif command == "scaleup":
        scale_up_vm(nargs[0], int(nargs[1]))
        vm_interconnects()

    elif command == "scaledown":
        with open("deploy/scaler.yaml") as f:
            scaler_config = yaml.load(f)

        print scaler_config

        groupName = nargs[0]
        for vmSize, nodeGroup in scaler_config["node_groups"].items():
            if vmSize == groupName:
                # The newly scaled up nodes should be empty.
                nodeGroup["last_scaled_up_nodes"] = []

        with open("deploy/scaler.yaml", "w") as f:
            yaml.dump(scaler_config, f)

        vmname = nargs[1]
        diskID = get_disk_from_vm(vmname)
        delete_vm(vmname)
        delete_nic(vmname + "VMNic")
        delete_public_ip(vmname + "PublicIP")
        if not diskID:
            delete_disk(diskID)
        vm_interconnects()

    elif command == "delete":
        delete_cluster()

    elif command == "genconfig":
        gen_cluster_config("cluster.yaml", no_az=args.noaz)

if __name__ == '__main__':
    # the program always run at the current directory.
    dirpath = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
    # print "Directory: " + dirpath
    os.chdir(dirpath)
    config = init_config()
    parser = argparse.ArgumentParser(prog='az_utils.py',
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=textwrap.dedent('''\
Create and manage a Azure VM cluster.

Prerequest:
* Create config.yaml according to instruction in docs/deployment/azure/configure.md.

Command:
  create Create an Azure VM cluster based on the parameters in config file.
  delete Delete the Azure VM cluster.
  scaleup Scale up operation.
  scaledown shutdown a particular VM.
  list list VMs.
  interconnect create network links among VMs
  genconfig Generate configuration files for Azure VM cluster.
  ''') )
    parser.add_argument("--cluster_name",
                        help="Specify a cluster name",
                        action="store",
                        default=None)

    parser.add_argument("--infra_node_num",
                        help="Specify the number of infra nodes, default = " +
                        str(config["azure_cluster"]["infra_node_num"]),
                        action="store",
                        default=None)

    parser.add_argument("--azure_location",
                        help="Specify azure location, default = " +
                        str(config["azure_cluster"]["azure_location"]),
                        action="store",
                        default=None)

    parser.add_argument("--infra_vm_size",
                        help="Specify the azure virtual machine sku size for infrastructure node, default = " +
                        config["azure_cluster"]["infra_vm_size"],
                        action="store",
                        default=None)

    parser.add_argument("--worker_vm_size",
                        help="Specify the azure virtual machine sku size for worker node, default = " +
                        config["azure_cluster"]["worker_vm_size"],
                        action="store",
                        default=None)

    parser.add_argument("--vm_image",
                        help="Specify the azure virtual machine image, default = " +
                        config["azure_cluster"]["vm_image"],
                        action="store",
                        default=None)

    parser.add_argument("--vm_storage_sku",
                        help="Specify the azure storage sku, default = " +
                        config["azure_cluster"]["vm_storage_sku"],
                        action="store",
                        default=None)

    parser.add_argument("--vnet_range",
                        help="Specify the azure virtual network range, default = " +
                        config["cloud_config"]["vnet_range"],
                        action="store",
                        default=None)

    parser.add_argument("--default_admin_username",
                        help="Specify the default admin username of azure virtual machine, default = " +
                        config["cloud_config"]["default_admin_username"],
                        action="store",
                        default=None)

    file_share_name = config["azure_cluster"][
        "file_share_name"] if "file_share_name" in config["azure_cluster"] else "<None>"
    parser.add_argument("--file_share_name",
                        help="Specify the default samba share name on azure stroage, default = " + file_share_name,
                        action="store",
                        default=None)

    parser.add_argument("--verbose", "-v",
                        help="Enable verbose output during script execution",
                        action="store_true"
                        )

    parser.add_argument("--noaz",
                        help="Dev node does not have access to azure portal, e.g. ARM template deployment",
                        action="store_true",
                        default=False,
                        )

    parser.add_argument("--arm_password",
                        help="Password for VMs to simulate ARM template deployment",
                        action="store",
                        default=None
                        )

    parser.add_argument("command",
                        help="See above for the list of valid command")
    parser.add_argument('nargs', nargs=argparse.REMAINDER,
                        help="Additional command argument",
                        )
    args = parser.parse_args()
    command = args.command
    nargs = args.nargs

    if args.verbose:
        verbose = args.verbose
        print "{0}".format(args)

    # Cluster Config
    config_cluster = os.path.join(dirpath, "azure_cluster_config.yaml")
    if os.path.exists(config_cluster):
        tmpconfig = yaml.load(open(config_cluster))
        if tmpconfig is not None:
            merge_config(config, tmpconfig, verbose)

    config_file = os.path.join(dirpath, "config.yaml")
    if os.path.exists(config_file):
        with open(config_file) as cf:
            tmpconfig = yaml.load(cf)
            assert tmpconfig["cluster_name"] in tmpconfig["azure_cluster"]
        merge_config(config, tmpconfig, verbose)
        if tmpconfig is not None and "cluster_name" in tmpconfig:
            config["azure_cluster"]["cluster_name"] = tmpconfig["cluster_name"]
            config["azure_cluster"]["datasource"] = tmpconfig["datasource"]
    if tmpconfig is not None and "azure_cluster" in tmpconfig and config["azure_cluster"]["cluster_name"] in tmpconfig["azure_cluster"]:
        merge_config(config["azure_cluster"], tmpconfig["azure_cluster"][
                     config["azure_cluster"]["cluster_name"]], verbose)
    if (args.cluster_name is not None):
        config["azure_cluster"]["cluster_name"] = args.cluster_name

    if (args.infra_node_num is not None):
        config["azure_cluster"]["infra_node_num"] = args.infra_node_num

    if (args.azure_location is not None):
        config["azure_cluster"]["azure_location"] = args.azure_location
    if (args.infra_vm_size is not None):
        config["azure_cluster"]["infra_vm_size"] = args.infra_vm_size
    if (args.worker_vm_size is not None):
        config["azure_cluster"]["worker_vm_size"] = args.worker_vm_size
    if (args.vm_image is not None):
        config["azure_cluster"]["vm_image"] = args.vm_image
    if (args.vm_storage_sku is not None):
        config["azure_cluster"]["vm_storage_sku"] = args.vm_storage_sku
    if (args.vnet_range is not None):
        config["azure_cluster"]["vnet_range"] = args.vnet_range
    if (args.default_admin_username is not None):
        config["cloud_config"][
            "default_admin_username"] = args.default_admin_username
    if (args.file_share_name is not None):
        config["azure_cluster"]["file_share_name"] = args.file_share_name

    config = update_config(config)
    # print (config)

    with open(config_cluster, 'w') as outfile:
        yaml.dump(config, outfile, default_flow_style=False)

    if "cluster_name" not in config["azure_cluster"] or config["azure_cluster"]["cluster_name"] is None:
        print("Cluster Name cannot be empty")
        exit()
    run_command(args, command, nargs, parser)
