#!/usr/bin/env python3

import json
import os
import argparse
import uuid
import textwrap
import re
import random
import string
import yaml

import utils
from az_params import *
from params import *
from az_utils import \
    add_nsg_rule_whitelist, \
    remove_nsg_rule_whitelist, \
    delete_nsg_rule_whitelist, \
    create_nsg_rules_with_service_tags, \
    delete_nsg_rules_with_service_tags, \
    create_logging_storage_account, \
    create_logging_container, \
    delete_logging_storage_account, \
    get_connection_string_for_logging_storage_account

verbose = False
no_execution = False

# These are the default configuration parameter


def init_config():
    config = {}
    for k, v in default_config_parameters.items():
        config[k] = v
    for k, v in default_az_parameters.items():
        config[k] = v
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
    if "resource_group" not in config["azure_cluster"]:
        config["azure_cluster"]["resource_group"] = config[
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

    priv_IP = "--private-ip-address %s " % vm_ip if not role in ["worker", "mysqlserver", "elasticsearch", "nfs"] else ""
    nsg = "nfs_nsg_name" if role == "nfs" else "nsg_name"

    availability_set = ""
    if role == "worker" and "availability_set" in config["azure_cluster"]:
        availability_set = "--availability-set '%s'" % config["azure_cluster"]["availability_set"]
    cloud_init = ""
    if "cloud_init_%s" % role in config:
        # if not os.path.exists("scripts/cloud_init_%s.sh" % role):
        assert os.path.exists(config["cloud_init_%s" % role])
        cloud_init = "--custom-data {}".format(config["cloud_init_%s" % role])

    if role in ["infra", "worker", "mysqlserver", "elasticsearch"]:
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
                 %s \

        """ % (config["azure_cluster"]["resource_group"],
               vmname,
               config["azure_cluster"]["vm_image"],
               priv_IP,
               vmname,
               config["azure_cluster"]["azure_location"],
               vm_size,
               config["azure_cluster"]["vnet_name"],
               config["azure_cluster"][nsg],
               config["cloud_config_nsg_rules"]["default_admin_username"],
               cloud_init,
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
        """ % (config["azure_cluster"]["resource_group"], config["azure_cluster"]["azure_location"])
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
        """ % (config["azure_cluster"]["resource_group"],
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
        """ % (config["azure_cluster"]["resource_group"],
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
               config["azure_cluster"]["resource_group"],
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
        """ % (config["azure_cluster"]["storage_account_name"], config["azure_cluster"]["resource_group"])
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
        """ % ( config["azure_cluster"]["resource_group"],
                config["azure_cluster"]["vnet_name"],
                config["cloud_config_nsg_rules"]["vnet_range"],
                config["cloud_config_nsg_rules"]["vnet_range"])
    if verbose:
        print(cmd)
    if not no_execution:
        output = utils.exec_cmd_local(cmd)
        print(output)


def create_nsg():
    if "source_addresses_prefixes" in config["cloud_config_nsg_rules"]["dev_network"]:
        source_addresses_prefixes = config["cloud_config_nsg_rules"][
            "dev_network"]["source_addresses_prefixes"]
        if isinstance(source_addresses_prefixes, list):
            source_addresses_prefixes = " ".join(list(set(source_addresses_prefixes)))
    else:
        print("Please setup source_addresses_prefixes in config.yaml, otherwise, your cluster cannot be accessed")
        exit()

    restricted_source_address_prefixes = "'*'"
    if "restricted_source_address_prefixes" in config["cloud_config_nsg_rules"]:
        restricted_source_address_prefixes = config["cloud_config_nsg_rules"]["restricted_source_address_prefixes"]
        if isinstance(restricted_source_address_prefixes, list):
            restricted_source_address_prefixes = " ".join(list(set(restricted_source_address_prefixes)))

    cmd = """
        az network nsg create \
            --resource-group %s \
            --name %s
        """ % ( config["azure_cluster"]["resource_group"],
                config["azure_cluster"]["nsg_name"])
    if verbose:
        print(cmd)
    if not no_execution:
        output = utils.exec_cmd_local(cmd)
        print(output)

    create_nsg_rules_with_service_tags(config, args)

    if "tcp_port_ranges" in config["cloud_config_nsg_rules"]:
        cmd = """
            az network nsg rule create \
                --resource-group %s \
                --nsg-name %s \
                --name allowalltcp \
                --protocol tcp \
                --priority 1000 \
                --destination-port-ranges %s \
                --source-address-prefixes %s \
                --access allow
            """ % ( config["azure_cluster"]["resource_group"],
                    config["azure_cluster"]["nsg_name"],
                    config["cloud_config_nsg_rules"]["tcp_port_ranges"],
                    restricted_source_address_prefixes
                    )
        if not no_execution:
            output = utils.exec_cmd_local(cmd)
            print(output)

    if "udp_port_ranges" in config["cloud_config_nsg_rules"]:
        cmd = """
            az network nsg rule create \
                --resource-group %s \
                --nsg-name %s \
                --name allowalludp \
                --protocol udp \
                --priority 1010 \
                --destination-port-ranges %s \
                --source-address-prefixes %s \
                --access allow
            """ % ( config["azure_cluster"]["resource_group"],
                    config["azure_cluster"]["nsg_name"],
                    config["cloud_config_nsg_rules"]["udp_port_ranges"],
                    restricted_source_address_prefixes
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
        """ % ( config["azure_cluster"]["resource_group"],
                config["azure_cluster"]["nsg_name"],
                config["cloud_config_nsg_rules"]["dev_network"]["tcp_port_ranges"],
                source_addresses_prefixes
                )
    if not no_execution:
        output = utils.exec_cmd_local(cmd)
        print(output)

def create_nfs_nsg():
    if "source_addresses_prefixes" in config["cloud_config_nsg_rules"]["dev_network"]:
        source_addresses_prefixes = config["cloud_config_nsg_rules"][
            "dev_network"]["source_addresses_prefixes"]
    else:
        print("Please setup source_addresses_prefixes in config.yaml, otherwise, your cluster cannot be accessed")
        exit()
    if int(config["azure_cluster"]["nfs_node_num"]) > 0:
        cmd = """
            az network nsg create \
                --resource-group %s \
                --name %s
            """ % ( config["azure_cluster"]["resource_group"],
                    config["azure_cluster"]["nfs_nsg_name"])
        if verbose:
            print(cmd)
        if not no_execution:
            output = utils.exec_cmd_local(cmd)
            print(output)

    print(type(config["cloud_config_nsg_rules"]["nfs_ssh"]["source_ips"]), config["cloud_config_nsg_rules"]["nfs_ssh"]["source_ips"],type(source_addresses_prefixes), source_addresses_prefixes)
    merged_ip = utils.keep_widest_subnet(config["cloud_config_nsg_rules"]["nfs_ssh"]["source_ips"] + source_addresses_prefixes)
    cmd = """
        az network nsg rule create \
            --resource-group %s \
            --nsg-name %s \
            --name allow_ssh\
            --priority 1200 \
            --destination-port-ranges %s \
            --source-address-prefixes %s \
            --access allow
        """ % ( config["azure_cluster"]["resource_group"],
                config["azure_cluster"]["nfs_nsg_name"],
                config["cloud_config_nsg_rules"]["nfs_ssh"]["port"],
                " ".join(merged_ip),
                )
    if verbose:
        print(cmd)
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
        """ % ( config["azure_cluster"]["resource_group"],
                config["azure_cluster"]["nfs_nsg_name"],
                " ".join(config["cloud_config_nsg_rules"]["nfs_share"]["source_ips"]),
                )
    if not no_execution:
        output = utils.exec_cmd_local(cmd)
        print(output)


def delete_group():
    cmd = """
        az group delete -y --name %s
        """ % (config["azure_cluster"]["resource_group"])
    if verbose:
        print(cmd)
    if not no_execution:
        output = utils.exec_cmd_local(cmd)
        print(output)


def get_vm_ip(i, role):
    """the ip generated for worker / nfs not used for vm creation TODO delete?"""
    vnet_range = config["cloud_config_nsg_rules"]["vnet_range"]
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
    print("creating resource group...")
    create_group()
    if not bSQLOnly:
        if "file_share" in config["azure_cluster"]:
            print("creating storage account...")
            create_storage_account()
            print("creating file share...")
            create_file_share()
        print("creating vnet...")
        create_vnet()
        print("creating network security group...")
        create_nsg()
        create_nfs_nsg()
    if useSqlAzure():
        print("creating sql server and database...")
        create_sql()

    if arm_vm_password is not None:
        # dev box, used in extreme condition when there's only one public IP available, then would use dev in cluster to bridge-connect all of them
        create_vm_param(0, "dev", config["azure_cluster"]["infra_vm_size"],
                        True, arm_vm_password)
    for i in range(int(config["azure_cluster"]["infra_node_num"])):
        create_vm_param(i, "infra", config["azure_cluster"]["infra_vm_size"],
                        arm_vm_password is not None, arm_vm_password)

    add_workers(arm_vm_password, parallelism)

    # create mysqlserver if specified
    for i in range(int(config["azure_cluster"]["mysqlserver_node_num"])):
        create_vm_param(i, "mysqlserver", config["azure_cluster"]["mysqlserver_vm_size"],
                        arm_vm_password is not None, arm_vm_password)

    # create elasticsearch server if specified.
    for i in range(int(config["azure_cluster"]["elasticsearch_node_num"])):
            create_vm_param(i, "elasticsearch", config["azure_cluster"]["elasticsearch_vm_size"],
                            arm_vm_password is not None, arm_vm_password)

    # create nfs server if specified.
    for i in range(int(config["azure_cluster"]["nfs_node_num"])):
            create_vm_param(i, "nfs", config["azure_cluster"]["nfs_vm_size"], False,
               arm_vm_password, config["azure_cluster"]["nfs_vm"][i] if i < len(config["azure_cluster"]["nfs_vm"]) else None )

def add_workers(arm_vm_password=None, parallelism=1):
    if config["priority"] == "regular":
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
        utils.exec_cmd_local("chmod +x scripts/vmss.sh; ./scripts/vmss.sh")

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
    elif role == "mysqlserver":
        vmname = "%s-mysqlserver%02d" % (config["azure_cluster"]["cluster_name"], i + 1)
    elif role == "elasticsearch":
        vmname = "%s-elasticsearch%02d" % (config["azure_cluster"]
                                           ["cluster_name"], i + 1)
    elif role == "dev":
        vmname = "%s-dev" % (config["azure_cluster"]["cluster_name"])

    print("creating VM %s..." % vmname)
    vm_ip = get_vm_ip(i, role)
    create_vm(vmname, vm_ip, role, vm_size, arm_vm_password, vmcnf)
    return vmname

def create_vm_role_suffix(i, role, vm_size, suffix, arm_vm_password=None, vmcnf = None):
    assert role in config["allroles"] and "invalid machine role, please select from {}".format(' '.join(config["allroles"]))

    print("creating VM %s..." % vmname)
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

    for vmSize, nodeGroup in list(scaler_config["node_groups"].items()):
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
        """ % (config["azure_cluster"]["resource_group"] )
    if verbose:
        print(cmd)
    output = utils.exec_cmd_local(cmd)
    allvm = json.loads(output)
    vminfo = {}
    for onevm in allvm:
        vmname = onevm["name"]
        print("VM ... %s" % vmname)
        cmd1 = """ az vm show -d -g %s -n %s""" % (
            config["azure_cluster"]["resource_group"], vmname)
        output1 = utils.exec_cmd_local(cmd1)
        json1 = json.loads(output1)
        vminfo[vmname] = json1
        if bShow:
            print(json1)
    return vminfo


def vm_interconnects():
    vminfo = list_vm(False)
    ports = []
    infra_ip_list = []
    for name, onevm in vminfo.items():
        ports.append(onevm["publicIps"] + "/32")
        if 'infra' in name:
            infra_ip_list.append(onevm["publicIps"] + "/32")
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
        """ % ( config["azure_cluster"]["resource_group"],
                config["azure_cluster"]["nsg_name"],
                config["cloud_config_nsg_rules"]["inter_connect"]["tcp_port_ranges"],
                portinfo
                )
    if verbose:
        print(cmd)
    output = utils.exec_cmd_local(cmd)
    print(output)

    restricted_source_address_prefixes = "'*'"
    if "restricted_source_address_prefixes" in config["cloud_config_nsg_rules"]:
        restricted_source_address_prefixes = config["cloud_config_nsg_rules"]["restricted_source_address_prefixes"]
        if isinstance(restricted_source_address_prefixes, list):
            restricted_source_address_prefixes = " ".join(
                utils.keep_widest_subnet(infra_ip_list + list(set(restricted_source_address_prefixes))))

    cmd = """
        ; az network nsg rule update \
            --resource-group %s \
            --nsg-name %s \
            --name allowalltcp \
            --source-address-prefixes %s \
            --access allow
        """ % (config["azure_cluster"]["resource_group_name"],
               config["azure_cluster"]["nsg_name"],
               restricted_source_address_prefixes
               )
    output = utils.exec_cmd_local(cmd)
    print(output)



def nfs_allow_master():
    vminfo = list_vm(False)
    source_address_prefixes = []
    for name, onevm in vminfo.items():
        if "-infra" in name:
            source_address_prefixes.append(onevm["publicIps"] + "/32")
    source_address_prefixes = " ".join(source_address_prefixes)

    nsg_names = [config["azure_cluster"]["nfs_nsg_name"]]
    if "custom_nfs_nsg_names" in config["azure_cluster"]:
        if isinstance(config["azure_cluster"]["custom_nfs_nsg_names"], list):
            for nsg_name in config["azure_cluster"]["custom_nfs_nsg_names"]:
                nsg_names.append(nsg_name)

    for nsg_name in nsg_names:
        cmd = """
                az network nsg rule create \
                    --resource-group %s \
                    --nsg-name %s \
                    --name nfs_allow_master \
                    --protocol tcp \
                    --priority 1400 \
                    --destination-port-ranges %s \
                    --source-address-prefixes %s \
                    --access allow
                """ % (config["azure_cluster"]["resource_group"],
                       nsg_name,
                       config["cloud_config_nsg_rules"]["nfs_allow_master"]["tcp_port_ranges"],
                       source_address_prefixes)
        if verbose:
            print(cmd)
        output = utils.exec_cmd_local(cmd)
        print(output)


def delete_vm(vmname):
    cmd = """
        az vm delete --resource-group %s \
                 --name %s \
                 --yes
        """ % (config["azure_cluster"]["resource_group"],
               vmname)

    if verbose:
        print(cmd)
    output = utils.exec_cmd_local(cmd)
    print(output)


def delete_nic(nicname):
    cmd = """
        az network nic delete --resource-group %s \
                --name %s \
        """ % (config["azure_cluster"]["resource_group"],
               nicname)
    if verbose:
        print(cmd)
    output = utils.exec_cmd_local(cmd)
    print(output)


def delete_public_ip(ip):
    cmd = """
        az network public-ip delete --resource-group %s \
                 --name %s \
        """ % (config["azure_cluster"]["resource_group"],
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
        """ % (config["azure_cluster"]["resource_group"],
               diskID)

    if verbose:
        print(cmd)
    output = utils.exec_cmd_local(cmd)
    print(output)


def get_disk_from_vm(vmname):
    cmd = """
        az vm show -g %s -n %s --query "storageProfile.osDisk.managedDisk.id" -o tsv \
        """ % (config["azure_cluster"]["resource_group"],
               vmname)

    if verbose:
        print(cmd)
    output = utils.exec_cmd_local(cmd)

    return output.split("/")[-1].strip('\n')

def gen_cluster_config(output_file_name, output_file=True, no_az=False):
    if config["priority"] == "low":
        utils.render_template("./template/dns/cname_and_private_ips.sh.template", "scripts/cname_and_ips.sh", config)
        utils.exec_cmd_local("chmod +x scripts/cname_and_ips.sh; bash scripts/cname_and_ips.sh")
        print("\nPlease copy the commands in dns_add_commands and register the DNS records \n")
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
            """ % (config["azure_cluster"]["storage_account_name"], config["azure_cluster"]["resource_group"])
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
        cc["admin_username"] = config["cloud_config_nsg_rules"]["default_admin_username"]
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
    domain_mapping = {
        "regular":"%s.cloudapp.azure.com" % config["azure_cluster"]["azure_location"],
        "low": config.get("network_domain",config["azure_cluster"]["default_low_priority_domain"])}
    if not bSQLOnly:
        cc["network"] = {"domain": domain_mapping[config["priority"]]}

    cc["machines"] = {}
    for i in range(int(config["azure_cluster"]["infra_node_num"])):
        vmname = "{}-infra{:02d}".format(config["azure_cluster"]["cluster_name"], i + 1).lower()
        cc["machines"][vmname] = {"role": "infrastructure", "private-ip": get_vm_ip(i, "infra")}

    # Generate the workers in machines.
    vm_list = []

    if not no_az:
        vm_list = get_vm_list_by_grp()
    else:
        vm_list = get_vm_list_by_enum()

    vm_ip_names = get_vm_private_ip()
    # 2 to 3
    vm_list = [{k.decode():v.decode() for k,v in itm.items()} for itm in vm_list]
    vm_ip_names = [{k.decode():[vi.decode() for vi in v] if isinstance(v, list) else v.decode() for k,v in itm.items()} for itm in vm_ip_names]
    vm_ip_names = sorted(vm_ip_names, key = lambda x:x['name'])
    sku_mapping = config["sku_mapping"]

    worker_machines = []
    if config["priority"] == "low":
        with open("hostname_fqdn_map","r") as rf:
            for l in rf:
                worker_machines += l.split()[0],
        for vmname in worker_machines:
            cc["machines"][vmname.lower()] = {"role": "worker","node-group": config["azure_cluster"]["worker_vm_size"]}
    elif config["priority"] == "regular":
        for vm in vm_list:
            vmname = vm["name"]
            if "-worker" in vmname:
                worker_machines.append(vm),
        for vm in worker_machines:
            vmname = vm["name"]
            if isNewlyScaledMachine(vmname):
                cc["machines"][vmname.lower()] = {
                    "role": "worker", "scaled": True, "node-group": vm["vmSize"]}
            else:
                cc["machines"][vmname.lower()] = {
                    "role": "worker", "node-group": vm["vmSize"]}

    # Add mysqlserver nodes
    for vm in vm_list:
        vmname = vm["name"]
        if "-mysqlserver" in vmname:
            cc["machines"][vmname.lower()] = {
                "role": "mysqlserver",
                "node-group": vm["vmSize"]}

    # Add elasticsearch nodes
    for vm in vm_list:
        vmname = vm["name"]
        if "-elasticsearch" in vmname:
            cc["machines"][vmname.lower()] = {
                "role": "elasticsearch",
                "node-group": vm["vmSize"]}

    nfs_nodes = []
    for vm in vm_list:
        vmname = vm["name"]
        if "-nfs" in vmname:
            cc["machines"][vmname.lower()] = {
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
        for svr_name, svr_ip in list(nfs_names2ip.items()):
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
            fullynamed_nfs = set([nfs_cnf["server_name"] for nfs_cnf in config["nfs_mnt_setup"] if "server_name" in nfs_cnf])

            # add private IP for fully named NFS to nfs_names2ip map
            for nfs_vm in fullynamed_nfs:
                nfs_vm_ip = None
                for vm_ip_name in vm_ip_names:
                    if vm_ip_name["name"] == nfs_vm:
                        nfs_vm_ip = vm_ip_name["privateIP"][0]
                        break
                assert nfs_vm_ip is not None, "Fully named NFS %s doesn't exist!" % nfs_vm
                nfs_names2ip[nfs_vm] = nfs_vm_ip

            # unused, either node without name suffix or those with suffix but not specified in any nfs_svr_setup item
            unused_nfs = sorted([s for s in list(nfs_names2ip.keys()) if s not in list(suffix2used_nfs.values()) and s not in fullynamed_nfs])
            unused_ID_cnt = 0
            for nfs_cnf in config["nfs_mnt_setup"]:
                if "server_name" in nfs_cnf:
                    server_name = nfs_cnf["server_name"]
                    mnt_parent_path = None
                elif "server_suffix" in nfs_cnf:
                    server_name = suffix2used_nfs[nfs_cnf["server_suffix"]]
                    mnt_parent_path = nfs_vm_suffixes2dpath[nfs_cnf["server_suffix"]]
                else:
                    server_name = unused_nfs[unused_ID_cnt]
                    unused_ID_cnt += 1
                    mnt_parent_path = config["azure_cluster"]["nfs_data_disk_path"]
                server_ip = nfs_names2ip[server_name]
                for mntname, mntcnf in list(nfs_cnf["mnt_point"].items()):
                    if not (mnt_parent_path is None or mntcnf["filesharename"].startswith(mnt_parent_path)):
                        print("Error: Wrong filesharename {}! Mount path is {} !".format(mntcnf["filesharename"], mnt_parent_path))
                        raise ValueError
                    if mntname in cc["mountpoints"]:
                        print("Warning, duplicated mountpoints item name {}, skipping".format(mntname))
                        continue

                    if server_name not in fullynamed_nfs:
                        cc["nfs_disk_mnt"][server_name]["fileshares"] += mntcnf["filesharename"],
                    cc["mountpoints"][mntname] = mntcnf
                    cc["mountpoints"][mntname]["type"] = "nfs"
                    cc["mountpoints"][mntname]["server"] = server_ip
                    cc["mountpoints"][mntname]["servername"] = server_name

    cntr = {}
    for mc in worker_machines:
        vm_sz = mc["vmSize"]
        cntr[vm_sz] = cntr.get(vm_sz, 0) + 1
    cc["worker_sku_cnt"] = cntr

    if "sku_mapping" in config:
        cc["sku_mapping"] = config["sku_mapping"]
        for sku in cc["worker_sku_cnt"]:
            # this means that the cluster deployed with this pipeline cannot be heterogeneous
            cc["gpu_type"] = cc["sku_mapping"].get(sku, {}).get('gpu-type', "None")
            break

    if output_file:
        print(yaml.dump(cc, default_flow_style=False))
        with open(output_file_name, 'w') as outfile:
            yaml.dump(cc, outfile, default_flow_style=False)

    return cc

def isNewlyScaledMachine(vmname):
    scaler_config_file = os.path.join(dirpath, "deploy/scaler.yaml")
    if os.path.exists(scaler_config_file):
        scaler_config = yaml.load(open(scaler_config_file))
        for vmSize, nodeGroup in list(scaler_config["node_groups"].items()):
            for nodeName in nodeGroup["last_scaled_up_nodes"]:
                if nodeName == vmname:
                    return True
    # If scaler.yaml is not found, then it should never be a scaled node.
    return False


def get_vm_list_by_grp():
    cmd = """
        az vm list --output json -g %s --query '[].{name:name, vmSize:hardwareProfile.vmSize}'

        """ % (config["azure_cluster"]["resource_group"])

    if verbose:
        print(cmd)
    output = utils.exec_cmd_local(cmd)
    print("raw")
    print(output)

    return utils.json_loads_byteified(output)

def get_vm_private_ip():
    cmd = """
        az vm list-ip-addresses -g %s --output json --query '[].{name:virtualMachine.name, privateIP:virtualMachine.network.privateIpAddresses}'

        """ % (config["azure_cluster"]["resource_group"])
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
    return ''.join(random.choice(string.ascii_lowercase) for x in range(length))


def delete_cluster():
    print("!!! WARNING !!! Resource group {0} will be deleted".format(config["azure_cluster"]["resource_group"]))
    response = input(
        "!!! WARNING !!! You are performing a dangerous operation that will permanently delete the entire Azure DL Workspace cluster. Please type (DELETE) in ALL CAPITALS to confirm the operation ---> ")
    if response == "DELETE":
        delete_group()

def check_subscription():
    chkcmd ="az account list | grep -A5 -B5 '\"isDefault\": true'"
    output = utils.exec_cmd_local(chkcmd)
    if isinstance(output, bytes):
        output = output.decode()
    if not config["azure_cluster"]["subscription"] in output:
        setcmd = "az account set --subscription \"{}\"".format(config["azure_cluster"]["subscription"])
        setout = utils.exec_cmd_local(setcmd)
    output = utils.exec_cmd_local(chkcmd)
    if isinstance(output, bytes):
        output = output.decode()
    assert config["azure_cluster"]["subscription"] in output

def run_command(args, command, nargs, parser):
    if command == "genconfig":
        gen_cluster_config("cluster.yaml", no_az=args.noaz)
    else:
        check_subscription()
    if command == "create":
        create_cluster(args.arm_password, args.parallelism)
        vm_interconnects()
        nfs_allow_master()

    elif command == "addworkers":
        add_workers(args.arm_password, args.parallelism)
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

        print(scaler_config)

        groupName = nargs[0]
        for vmSize, nodeGroup in list(scaler_config["node_groups"].items()):
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

    elif command == "nfsallowmaster":
        nfs_allow_master()

    elif command == "whitelist":
        if nargs[0] == "add":
            ips = None if len(nargs) == 1 else nargs[1]
            add_nsg_rule_whitelist(config, args, ips)
        elif nargs[0] == "remove":
            ips = None if len(nargs) == 1 else nargs[1]
            remove_nsg_rule_whitelist(config, args, ips)
        elif nargs[0] == "delete":
            delete_nsg_rule_whitelist(config, args)

    elif command == "service_tag_rules":
        if nargs[0] == "create":
            create_nsg_rules_with_service_tags(config, args)
        elif nargs[0] == "delete":
            delete_nsg_rules_with_service_tags(config, args)

    elif command == "logging_storage":
        if nargs[0] == "create":
            create_logging_storage_account(config, args)
            create_logging_container(config, args)
        elif nargs[0] == "delete":
            response = input(
                "Delete logging storage? (Please type YES to confirm)")
            if response == "YES":
                delete_logging_storage_account(config, args)
        elif nargs[0] == "connection_string":
            get_connection_string_for_logging_storage_account(config, args)


if __name__ == '__main__':
    # the program always run at the current directory.
    dirpath = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
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
                        config["cloud_config_nsg_rules"]["vnet_range"],
                        action="store",
                        default=None)

    parser.add_argument("--default_admin_username",
                        help="Specify the default admin username of azure virtual machine, default = " +
                        config["cloud_config_nsg_rules"]["default_admin_username"],
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
    parser.add_argument("--output", "-o",
                        default="",
                        help='Specify the output file path')
    parser.add_argument("--dryrun", "-d",
                        help="Dry run -- no actual execution",
                        action="store_true")

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
        print("{0}".format(args))

    # Cluster Config

    config_file = os.path.join(dirpath, "config.yaml")
    if os.path.exists(config_file):
        with open(config_file) as cf:
            tmpconfig = yaml.load(cf)
        merge_config(config, tmpconfig, verbose)
        if tmpconfig is not None and "cluster_name" in tmpconfig:
            config["azure_cluster"]["cluster_name"] = tmpconfig["cluster_name"]
        if tmpconfig is not None and "datasource" in tmpconfig:
            config["azure_cluster"]["datasource"] = tmpconfig["datasource"]
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
        config["cloud_config_nsg_rules"][
            "default_admin_username"] = args.default_admin_username
    if (args.file_share_name is not None):
        config["azure_cluster"]["file_share_name"] = args.file_share_name

    config = update_config(config)

    if "cluster_name" not in config["azure_cluster"] or config["azure_cluster"]["cluster_name"] is None:
        print("Cluster Name cannot be empty")
        exit()
    run_command(args, command, nargs, parser)
