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
    if "resource_group_name" not in config["azure_cluster"]:
        config["azure_cluster"]["resource_group_name"] = config[
            "azure_cluster"]["cluster_name"] + "ResGrp"

    config["azure_cluster"]["vnet_name"] = config[
        "azure_cluster"]["cluster_name"] + "-VNet"
    config["azure_cluster"]["storage_account_name"] = config[
        "azure_cluster"]["cluster_name"] + "storage"
    config["azure_cluster"]["nsg_name"] = config[
        "azure_cluster"]["cluster_name"] + "-nsg"

    config["azure_cluster"]["nfs_nsg_name"] = config["azure_cluster"]["cluster_name"] + [
            "","-nfs"][int(int(config["azure_cluster"]["nfs_node_num"]) > 0)] + "-nsg"
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

def create_vm(vmname, vm_ip, role, vm_size, pwd, vmcnf):
    vmname = vmname.lower()
    if pwd is not None:
        auth = """--authentication-type password --admin-password '%s' """ % pwd
    else:
        auth = """--generate-ssh-keys --authentication-type ssh --ssh-key-value '%s' """ % config["azure_cluster"]["sshkey"]

    priv_IP = "--private-ip-address %s " % vm_ip if not role in ["worker","nfs"] else ""
    nsg = "nfs_nsg_name" if role == "nfs" else "nsg_name"
    
    availability_set = ""
    if role == "worker" and "availability_set" in config["azure_cluster"]:
        availability_set = "--availability-set '%s'" % config["azure_cluster"]["availability_set"]
    if role in ["infra", "worker"]:		
        storage = "--storage-sku {} --data-disk-sizes-gb {} ".format(config["azure_cluster"]["vm_local_storage_sku"],
                config["azure_cluster"]["%s_local_storage_sz" % role])
        # corner case: NFS on infra
        if role == "infra" and config["azure_cluster"]["nfs_node_num"] <= 0:
            storage += " " + " ".join([str(config["azure_cluster"]["nfs_data_disk_sz"])]*config["azure_cluster"]["nfs_data_disk_num"])
    elif role == 'nfs':
        if vmcnf is None:
            nfs_dd_sz, nfs_dd_num = config["azure_cluster"]["nfs_data_disk_sz"], config["azure_cluster"]["nfs_data_disk_num"]
            nfs_sku = config["azure_cluster"]["nfs_data_disk_sku"]
        else:
            nfs_dd_sz, nfs_dd_num, nfs_sku = vmcnf["data_disk_sz_gb"], vmcnf["data_disk_num"], vmcnf["data_disk_sku"]
            vm_size = vmcnf["vm_size"] if "vm_size" in vmcnf else vm_size
        storage = "--storage-sku {} --data-disk-sizes-gb {} ".format(nfs_sku,
                " " + " ".join([str(nfs_dd_sz)]*nfs_dd_num))

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
                 %s \
                 %s \
                 %s \
                 
        """ % (config["azure_cluster"]["resource_group_name"],
               vmname,
               config["azure_cluster"]["vm_image"],
               priv_IP,
               vmname,
               config["azure_cluster"]["azure_location"],
               vm_size,
               config["azure_cluster"]["vnet_name"],
               config["azure_cluster"][nsg],
               config["cloud_config"]["default_admin_username"],
               storage,
               auth,
               availability_set)

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
               config["azure_cluster"]["vm_local_storage_sku"],
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
    if int(config["azure_cluster"]["nfs_node_num"]) > 0:
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
            --priority 1200 \
            --destination-port-ranges %s \
            --source-address-prefixes %s \
            --access allow
        """ % ( config["azure_cluster"]["resource_group_name"],
                config["azure_cluster"]["nfs_nsg_name"],
                config["cloud_config"]["nfs_ssh"]["port"],
                " ".join(list(set(config["cloud_config"]["nfs_ssh"]["source_ips"] + source_addresses_prefixes))),
                )
    if not no_execution:
        output = utils.exec_cmd_local(cmd)
        print(output)

    cmd = """
        az network nsg rule create \
            --resource-group %s \
            --nsg-name %s \
            --name allow_share \
            --priority 1300 \
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


def create_cluster(arm_vm_password=None, parallelism=1):
    bSQLOnly = (config["azure_cluster"]["infra_node_num"] <= 0)
    assert int(config["azure_cluster"]["nfs_node_num"]) >= len(config["azure_cluster"]["nfs_vm"])
    assert "mysql_password" in config
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

    if config["priority"] == "regular":
        print("entering")
        if parallelism > 1:
            # TODO: Tolerate faults
            from multiprocessing import Pool
            args_list = [(i, "worker", config["azure_cluster"]["worker_vm_size"], arm_vm_password is not None, arm_vm_password)
                         for i in range(int(config["azure_cluster"]["worker_node_num"]))]
            pool = Pool(processes=parallelism)
            pool.map(create_vm_param_wrapper, args_list)
            pool.close()
        else:
            for i in range(int(config["azure_cluster"]["worker_node_num"])):
                create_vm_param(i, "worker", config["azure_cluster"]["worker_vm_size"],
                                arm_vm_password is not None, arm_vm_password)
    elif config["priority"] == "low":
        utils.render_template("./template/vmss/vmss.sh.template", "scripts/vmss.sh",config)
        utils.exec_cmd_local("chmod +x scripts/vmss.sh;./scripts/vmss.sh")

    # create nfs server if specified.
    for i in range(int(config["azure_cluster"]["nfs_node_num"])):
            create_vm_param(i, "nfs", config["azure_cluster"]["nfs_vm_size"], False,
               arm_vm_password, config["azure_cluster"]["nfs_vm"][i] if i < len(config["azure_cluster"]["nfs_vm"]) else None )

def create_vm_param_wrapper(arg_tuple):
    i, role, vm_size, no_az, arm_vm_password = arg_tuple
    return create_vm_param(i, role, vm_size, no_az, arm_vm_password)

def create_vm_param(i, role, vm_size, no_az=False, arm_vm_password=None, vmcnf = None):
    assert role in config["allroles"] and "invalid machine role, please select from {}".format(' '.join(config["allroles"]))
    if not vmcnf is None and "suffix" in vmcnf:
        vmname = "{}-{}-".format(config["azure_cluster"]["cluster_name"], role) + vmcnf["suffix"]
    elif role in ["worker","nfs"]:
        vmname = "{}-{}".format(config["azure_cluster"]["cluster_name"], role) + ("{:02d}".format(i+1) if no_az else '-'+random_str(6))
    elif role == "infra":
        vmname = "%s-infra%02d" % (config["azure_cluster"]
                                   ["cluster_name"], i + 1)
    elif role == "dev":
        vmname = "%s-dev" % (config["azure_cluster"]["cluster_name"])

    print "creating VM %s..." % vmname
    vm_ip = get_vm_ip(i, role)
    create_vm(vmname, vm_ip, role, vm_size, arm_vm_password, vmcnf)
    return vmname

def create_vm_role_suffix(i, role, vm_size, suffix, arm_vm_password=None, vmcnf = None):
    assert role in config["allroles"] and "invalid machine role, please select from {}".format(' '.join(config["allroles"]))
    
    print "creating VM %s..." % vmname
    vm_ip = get_vm_ip(i, role)
    create_vm(vmname, vm_ip, role, vm_size, arm_vm_password, vmcnf)
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
                vmname = create_vm_param(i, True, False, vmSize)
                nodeGroup["last_scaled_up_nodes"].append(vmname)
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
    if config["priority"] == "low":
        utils.render_template("./template/dns/cname_and_private_ips.sh.template", "scripts/cname_and_ips.sh", config)    
        utils.exec_cmd_local("chmod +x scripts/cname_and_ips.sh")
        print "\nPlease copy the commands in dns_add_commands and register the DNS records on http://servicebook/dns/self-service.html\n"
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
    domain_mapping = {"regular":"%s.cloudapp.azure.com" % config["azure_cluster"]["azure_location"], "low": config["domain_name"]}
    if not bSQLOnly:
        cc["network"] = {"domain": domain_mapping[config["priority"]]}

    cc["machines"] = {}
    for i in range(int(config["azure_cluster"]["infra_node_num"])):
        vmname = "%s-infra%02d" % (config["azure_cluster"]
                                   ["cluster_name"].lower(), i + 1)
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

    worker_machines = []
    if config["priority"] == "low":
        with open("hostname_fqdn_map","r") as rf:
            for l in rf:
                worker_machines += l.split()[0],
        for vmname in worker_machines:
            cc["machines"][vmname] = {"role": "worker","node-group": config["azure_cluster"]["worker_vm_size"],
                                        "gpu-type":sku_mapping[config["azure_cluster"]["worker_vm_size"]]["gpu-type"]}
    elif config["priority"] == "regular":
        for vm in vm_list:
            vmname = vm["name"]
            if "-worker" in vmname:
                worker_machines += vmname,
        for vmname in worker_machines:          
            if isNewlyScaledMachine(vmname):
                cc["machines"][vmname] = {
                    "role": "worker", "scaled": True,
                    "node-group": vm["vmSize"],"gpu-type":sku_mapping.get(vm["vmSize"],sku_mapping["default"])["gpu-type"]}
            else:
                cc["machines"][vmname] = {
                    "role": "worker",
                    "node-group": vm["vmSize"],"gpu-type":sku_mapping.get(vm["vmSize"],sku_mapping["default"])["gpu-type"]}
    nfs_nodes = []
    for vm in vm_list:
        vmname = vm["name"]
        if "-nfs" in vmname:
            cc["machines"][vmname] = {
                "role": "nfs",
                "node-group": vm["vmSize"]}

    # Dilemma : Before the servers got created, you don't know their name, cannot specify which server does a mountpoint config group belongs to
    if int(config["azure_cluster"]["nfs_node_num"]) > 0:
        nfs_names2ip = {rec['name']:rec['privateIP'][0] for rec in vm_ip_names if "-nfs" in rec['name']}
    else:
        nfs_names2ip = {rec['name']:rec['privateIP'][0] for rec in vm_ip_names if "infra" in rec['name']}
    if not bSQLOnly:
        cc["nfs_disk_mnt"] = {}
        suffixed_name_2path = {"{}-nfs-{}".format(config["cluster_name"], vm["suffix"]):vm["data_disk_mnt_path"] for vm in config["azure_cluster"]["nfs_vm"] if "suffix" in vm}
        for svr_name, svr_ip in nfs_names2ip.items():
            pth = suffixed_name_2path.get(svr_name, config["azure_cluster"]["nfs_data_disk_path"])
            role = "nfs" if "-nfs" in svr_name else "infra"
            cc["nfs_disk_mnt"][svr_name] = {"path": pth, "role": role, "ip": svr_ip, "fileshares":[]}
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
            nfs_vm_suffixes2dpath = {vm["suffix"]:vm["data_disk_mnt_path"] for vm in config["azure_cluster"]["nfs_vm"] if "suffix" in vm}
            used_nfs_suffix = set([nfs_cnf["server_suffix"] for nfs_cnf in config["nfs_mnt_setup"] if "server_suffix" in nfs_cnf])
            assert (used_nfs_suffix - set(nfs_vm_suffixes2dpath.keys())) == set() and "suffix not in nfs_suffixes list!"
            assert len(nfs_names2ip) >= len(config["azure_cluster"]["nfs_vm"]) and "More NFS config items than #. of NFS server"
            suffix2used_nfs = {suffix: "{}-nfs-{}".format(config["cluster_name"], suffix).lower() for suffix in used_nfs_suffix}
            # unused, either node without name suffix or those with suffix but not specified in any nfs_svr_setup item
            unused_nfs = sorted([s for s in nfs_names2ip.keys() if s not in suffix2used_nfs.values()])
            unused_ID_cnt = 0
            for nfs_cnf in config["nfs_mnt_setup"]:
                if "server_suffix" in nfs_cnf:
                    server_name = suffix2used_nfs[nfs_cnf["server_suffix"]]
                    mnt_parent_path = nfs_vm_suffixes2dpath[nfs_cnf["server_suffix"]]
                else:
                    server_name = unused_nfs[unused_ID_cnt]
                    unused_ID_cnt += 1
                    mnt_parent_path = config["azure_cluster"]["nfs_data_disk_path"]
                server_ip = nfs_names2ip[server_name]
                for mntname, mntcnf in nfs_cnf["mnt_point"].items():
                    if not mntcnf["filesharename"].startswith(mnt_parent_path):
                        print "Error: Wrong filesharename {}! Mount path is {} !".format(mntcnf["filesharename"], mnt_parent_path)
                        raise ValueError
                    if mntname in cc["mountpoints"]:
                        print("Warning, duplicated mountpoints item name {}, skipping".format(mntname))
                        continue
                    cc["nfs_disk_mnt"][server_name]["fileshares"] += mntcnf["filesharename"],
                    cc["mountpoints"][mntname] = mntcnf
                    cc["mountpoints"][mntname]["type"] = "nfs"
                    cc["mountpoints"][mntname]["server"] = server_ip
                    cc["mountpoints"][mntname]["servername"] = server_name
    
    if output_file:
        print yaml.dump(cc, default_flow_style=False)
        with open(output_file_name, 'w') as outfile:
            yaml.dump(cc, outfile, default_flow_style=False)

    return cc

def isNewlyScaledMachine(vmname):
    scaler_config_file = os.path.join(dirpath, "deploy/scaler.yaml")
    if os.path.exists(scaler_config_file):
        scaler_config = yaml.load(open(scaler_config_file))
        for vmSize, nodeGroup in scaler_config["node_groups"].items():
            for nodeName in nodeGroup["last_scaled_up_nodes"]:
                if nodeName == vmname:
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

def check_subscription():
    chkcmd ="az account list | grep -A5 -B5 '\"isDefault\": true'"
    output = utils.exec_cmd_local(chkcmd)
    if not config["azure_cluster"]["subscription"] in output:
        setcmd = "az account set --subscription \"{}\"".format(config["azure_cluster"]["subscription"])
        setout = utils.exec_cmd_local(setcmd)
        print "Set your subscription to {}, please login.\nIf you want to specify another subscription, please configure azure_cluster.subscription".format(config["azure_cluster"]["subscription"])
        utils.exec_cmd_local("az login")
    assert config["azure_cluster"]["subscription"] in utils.exec_cmd_local(chkcmd)

def run_command(args, command, nargs, parser):
    if command == "genconfig":
        gen_cluster_config("cluster.yaml", no_az=args.noaz)
    else:
        check_subscription()
    if command == "create":
        # print config["azure_cluster"]["infra_vm_size"]
        create_cluster(args.arm_password, args.parallelism)
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

    parser.add_argument("--vm_local_storage_sku",
                        help="Specify the azure storage sku, default = " +
                        config["azure_cluster"]["vm_local_storage_sku"],
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
    parser.add_argument("--parallelism", "-p",
                        help="Number of processes to create worker VMs. Default is 1.",
                        type=int,
                        default=1)

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
        if tmpconfig is not None and "datasource" in tmpconfig:
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
    if (args.vm_local_storage_sku is not None):
        config["azure_cluster"]["vm_local_storage_sku"] = args.vm_local_storage_sku
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
