#!/usr/bin/python3
import os
import sys
import uuid
import yaml
import json
import textwrap
import argparse
from az_params import *
from params import *
import utils
from multiprocessing import Pool
import subprocess
from utils import random_str, keep_widest_subnet
sys.path.append("../utils")
from ConfigUtils import add_configs_in_order

def init_config():
    config = {}
    for k, v in list(default_config_parameters.items()):
        config[k] = v
    for k, v in list(default_az_parameters.items()):
        config[k] = v
    return config


def load_config_based_on_command(command):
    default_config = init_config()
    config_file_list = args.config
    if not args.config:
        config_file_list = ["config.yaml"]
        if command in ["deploy", "interconnect"]:
            config_file_list += "az_complementary.yaml",
    config = add_configs_in_order(config_file_list, default_config)
    if command not in ["prerender"]:
        config = update_config_resgrp(config)
    if command in ["deploy", "addmachines"]:
        config = load_sshkey(config)
    return config


def update_config_resgrp(config):
    """load resource group related config info"""
    if "resource_group" not in config["azure_cluster"]:
        config["azure_cluster"]["resource_group"] = config["cluster_name"] + "ResGrp"
    config["azure_cluster"]["vnet_name"] = config["cluster_name"] + "-VNet"
    config["azure_cluster"]["storage_account_name"] = config["cluster_name"] + "storage"
    config["azure_cluster"]["nsg_name"] = config["cluster_name"] + "-nsg"
    config["azure_cluster"]["nfs_nsg_name"] = config["cluster_name"] + [
        "", "-nfs"][int(int(config["azure_cluster"]["nfs_node_num"]) > 0)] + "-nsg"
    return config


def load_sshkey(config):
    assert os.path.exists(
        './deploy/sshkey/id_rsa.pub') and "Generate SSHKey first!"
    with open('./deploy/sshkey/id_rsa.pub') as f:
        config["azure_cluster"]["sshkey"] = f.read()
    return config


def execute_or_dump_locally(cmd, verbose, dryrun, output_file):
    cmd = ' '.join(cmd.split())+'\n'
    if output_file:
        with open(output_file, 'a') as wf:
            wf.write(cmd)
    if not dryrun:
        output = utils.exec_cmd_local(cmd, verbose)
        return output


def set_subscription(config):
    if "subscription" not in config["azure_cluster"]:
        print("No subscription to set")
        return

    subscription = config["azure_cluster"]["subscription"]

    chkcmd = "az account list | grep -A5 -B5 '\"isDefault\": true'"
    output = utils.exec_cmd_local(chkcmd)
    if not subscription in output:
        setcmd = "az account set --subscription \"{}\"".format(subscription)
        setout = utils.exec_cmd_local(setcmd)
    assert subscription in utils.exec_cmd_local(chkcmd, True)


def create_group(config, args):
    subscription = "--subscription \"{}\"".format(
        config["azure_cluster"]["subscription"]) if "subscription" in config["azure_cluster"] else ""
    if subscription != "":
        set_subscription(config)
    cmd = """az group create --name {} --location {} {}
        """.format(config["azure_cluster"]["resource_group"], config["azure_cluster"]["azure_location"], subscription)
    execute_or_dump_locally(cmd, args.verbose, args.dryrun, args.output)


def create_availability_set(config, args):
    subscription = "--subscription \"{}\"".format(
        config["azure_cluster"]["subscription"]) if "subscription" in config["azure_cluster"] else ""
    availability_sets = set()
    if "availability_set" in config["azure_cluster"]:
        availability_sets.add(config["azure_cluster"]["availability_set"])
    for vmname, spec in config["machines"].items():
        if "availability_set" in spec:
            availability_sets.add(spec["availability_set"])
    listcmd = "az vm availability-set list --resource-group {} --query \"[].name\"".format(config["azure_cluster"]["resource_group"])
    as_res = execute_or_dump_locally(listcmd, args.verbose, False, args.output)
    existing_as = set(json.loads(as_res))
    availability_sets -= existing_as
    cmd = ';'.join(["""az vm availability-set create --name {} --resource-group {} --location {} {}
        """.format(avs, config["azure_cluster"]["resource_group"], config["azure_cluster"]["azure_location"], subscription) for avs in availability_sets])
    execute_or_dump_locally(cmd, args.verbose, args.dryrun, args.output)


def create_vnet(config, args):
    cmd = """az network vnet create \
            --resource-group %s \
            --name %s \
            --address-prefix %s \
            --subnet-name mySubnet \
            --subnet-prefix %s
        """ % (config["azure_cluster"]["resource_group"],
               config["azure_cluster"]["vnet_name"],
               config["cloud_config_nsg_rules"]["vnet_range"],
               config["cloud_config_nsg_rules"]["vnet_range"])
    execute_or_dump_locally(cmd, args.verbose, args.dryrun, args.output)


def create_nsg(config, args):
    assert "source_addresses_prefixes" in config["cloud_config_nsg_rules"]["dev_network"] and "Please \
    setup source_addresses_prefixes in config.yaml, otherwise, your cluster cannot be accessed"
    source_addresses_prefixes = config["cloud_config_nsg_rules"][
        "dev_network"]["source_addresses_prefixes"]

    if isinstance(source_addresses_prefixes, list):
        source_addresses_prefixes = " ".join(
            list(set(source_addresses_prefixes)))

    restricted_source_address_prefixes = "'*'"
    if "restricted_source_address_prefixes" in config["cloud_config_nsg_rules"]:
        restricted_source_address_prefixes = config["cloud_config_nsg_rules"]["restricted_source_address_prefixes"]
        if isinstance(restricted_source_address_prefixes, list):
            restricted_source_address_prefixes = " ".join(
                list(set(restricted_source_address_prefixes)))
    
    cmd = """az network nsg create \
            --resource-group %s \
            --name %s
        """ % (config["azure_cluster"]["resource_group"],
               config["azure_cluster"]["nsg_name"])
    execute_or_dump_locally(cmd, args.verbose, args.dryrun, args.output)

    if "tcp_port_ranges" in config["cloud_config_nsg_rules"]:
        cmd = """az network nsg rule create \
                --resource-group %s \
                --nsg-name %s \
                --name allowalltcp \
                --protocol tcp \
                --priority 1000 \
                --destination-port-ranges %s \
                --source-address-prefixes %s \
                --access allow
            """ % (config["azure_cluster"]["resource_group"],
                   config["azure_cluster"]["nsg_name"],
                   config["cloud_config_nsg_rules"]["tcp_port_ranges"],
                   restricted_source_address_prefixes
                   )
        execute_or_dump_locally(cmd, args.verbose, args.dryrun, args.output)

    if "udp_port_ranges" in config["cloud_config_nsg_rules"]:
        cmd = """az network nsg rule create \
                --resource-group %s \
                --nsg-name %s \
                --name allowalludp \
                --protocol udp \
                --priority 1010 \
                --destination-port-ranges %s \
                --source-address-prefixes %s \
                --access allow
            """ % (config["azure_cluster"]["resource_group"],
                   config["azure_cluster"]["nsg_name"],
                   config["cloud_config_nsg_rules"]["udp_port_ranges"],
                   restricted_source_address_prefixes
                   )
        execute_or_dump_locally(cmd, args.verbose, args.dryrun, args.output)

    cmd = """az network nsg rule create \
            --resource-group %s \
            --nsg-name %s \
            --name allowdevtcp \
            --protocol tcp \
            --priority 900 \
            --destination-port-ranges %s \
            --source-address-prefixes %s \
            --access allow
        """ % (config["azure_cluster"]["resource_group"],
               config["azure_cluster"]["nsg_name"],
               config["cloud_config_nsg_rules"]["dev_network"]["tcp_port_ranges"],
               source_addresses_prefixes
               )
    execute_or_dump_locally(cmd, args.verbose, args.dryrun, args.output)


def create_nfs_nsg(config, args):
    assert "source_addresses_prefixes" in config["cloud_config_nsg_rules"]["dev_network"] and "Please \
    setup source_addresses_prefixes in config.yaml, otherwise, your cluster cannot be accessed"
    source_addresses_prefixes = config["cloud_config_nsg_rules"][
        "dev_network"]["source_addresses_prefixes"]
    if int(config["azure_cluster"]["nfs_node_num"]) > 0:
        cmd = """az network nsg create \
                --resource-group %s \
                --name %s
            """ % (config["azure_cluster"]["resource_group"],
                   config["azure_cluster"]["nfs_nsg_name"])
        execute_or_dump_locally(cmd, args.verbose, args.dryrun, args.output)

    merged_ip = keep_widest_subnet(
        config["cloud_config_nsg_rules"]["nfs_ssh"]["source_ips"] + source_addresses_prefixes)
    cmd = """az network nsg rule create \
            --resource-group %s \
            --nsg-name %s \
            --name allow_ssh\
            --priority 1200 \
            --destination-port-ranges %s \
            --source-address-prefixes %s \
            --access allow
        """ % (config["azure_cluster"]["resource_group"],
               config["azure_cluster"]["nfs_nsg_name"],
               config["cloud_config_nsg_rules"]["nfs_ssh"]["port"],
               " ".join(merged_ip),
               )
    execute_or_dump_locally(cmd, args.verbose, args.dryrun, args.output)

    cmd = """az network nsg rule create \
            --resource-group %s \
            --nsg-name %s \
            --name allow_share \
            --priority 1300 \
            --source-address-prefixes %s \
            --destination-port-ranges \'*\' \
            --access allow
        """ % (config["azure_cluster"]["resource_group"],
               config["azure_cluster"]["nfs_nsg_name"],
               " ".join(config["cloud_config_nsg_rules"]
                        ["nfs_share"]["source_ips"]),
               )
    execute_or_dump_locally(cmd, args.verbose, args.dryrun, args.output)


def deploy_cluster(config, args):
    if args.output != "":
        with open(args.output, 'w') as f:
            f.write("#!/bin/bash\n")
    create_group(config, args)
    create_vnet(config, args)
    create_availability_set(config, args)
    create_nsg(config, args)
    create_nfs_nsg(config, args)
    if args.output and os.path.exists(args.output):
        os.system('chmod +x ' + args.output)


def validate_machine_spec(config, spec):
    assert "role" in spec and ((set(spec["role"]) - set(config["allroles"])) == set()) and \
        "must specify valid role for vm!"
    if "name" in spec:
        assert spec["number_of_instance"] <= 1 and "cannot overwirte name for multiple machines one time!"
    if "nfs" in spec["role"]:
        assert spec["number_of_instance"] <= 1 and "NFS machine spec must be configured one by one!"


def gen_machine_list_4_deploy_action(complementary_file_name, config):
    """based on info from config.yaml, generate the expected machine names etc."""
    cc = {}
    cc["machines"] = {}
    for spec in config["azure_cluster"]["virtual_machines"]:
        validate_machine_spec(config, spec)
        for i in range(spec["number_of_instance"]):
            # if explicitly specified a name, we use it
            if "name" in spec:
                vmname = spec["name"]
            else:
                vmname_pref = spec["prefix"] if "prefix" in spec else "{}-{}".format(
                    config["cluster_name"], spec["role"][0])
                vmname = vmname_pref + '-' + random_str(6)
            vmname = vmname.lower()
            cc["machines"][vmname] = {'role': spec["role"]}
            for k, v in spec.items():
                if k == "number_of_instance":
                    continue
                cc["machines"][vmname][k] = v
            if "kube_label_groups" not in spec:
                cc["machines"][vmname]["kube_label_groups"] = []
                for role in spec["role"]:
                    if role in config["default_kube_labels_by_node_role"]:
                        cc["machines"][vmname]["kube_label_groups"].append(
                            role)

    complementary_file_name = "az_complementary.yaml" if complementary_file_name == '' else complementary_file_name
    with open(complementary_file_name, 'w') as outfile:
        yaml.safe_dump(cc, outfile, default_flow_style=False)
    return cc


def add_machines(config, args):
    # we don't run az command in add_machine when batch_size is larger than 1, regardless of args.dryrun
    # instead, we would run those commands in parallel, and dump output sequentially. the machines would still
    # be added sequentially, but we could avoid overburdening devbox(sending too many request at one batch)
    os.system('rm -f ' + args.output)
    delay_run = (args.batch_size > 1) and (not args.dryrun)
    commands_list = []
    for vmname, spec in config["machines"].items():
        cmd = add_machine(vmname, spec, args.verbose,
                          delay_run or args.dryrun, args.output)
        if delay_run:
            commands_list += cmd,
    if os.path.exists(args.output):
        os.system('chmod +x ' + args.output)
    if delay_run:
        outputs = add_machine_in_parallel(commands_list, args)
        return outputs


def is_independent_nfs(role):
    """NFS not on infra"""
    return "nfs" in role and not (set(["infra", "etcd", "kubernetes_master"]) & set(role))


def add_machine_in_parallel(cmds, args):
    tuples = [(utils.exec_cmd_local, cmd, args.verbose, 600 * args.batch_size)
              for cmd in cmds]
    res = utils.multiprocess_with_func_arg_tuples(args.batch_size, tuples)
    return res


def add_machine(vmname, spec, verbose, dryrun, output_file):
    multual_exclusive_roles = set(["infra", "worker", "elasticsearch", "mysqlserver"])
    mul_ex_role_in_spec = list(set(spec["role"]) & multual_exclusive_roles)
    assert len(mul_ex_role_in_spec) <= 1 and "We don't allow role overlapping between these roles."
    if "pwd" in spec:
        auth = "--authentication-type password --admin-password '{}' ".format(
            spec["pwd"])
    else:
        auth = "--generate-ssh-keys --authentication-type ssh --ssh-key-value '{}' ".format(
            config["azure_cluster"]["sshkey"])

    # if just want to update private IP, then keep vmname unchanged, and only update IP.
    priv_ip = ""
    if "private_ip_address" in spec:
        priv_ip = "--private-ip-address {} ".format(spec["private_ip_address"])
    else:
        assert (not 'nfs' in spec["role"]
                ) and "Must specify IP address for NFS node!"

    nsg = "nfs_nsg_name" if is_independent_nfs(spec["role"]) else "nsg_name"

    availability_set = ""
    if "availability_set" in spec:
        availability_set = "--availability-set '{}'".format(
            spec["availability_set"])
    elif "worker" in spec["role"] and "availability_set" in config["azure_cluster"]:
        availability_set = "--availability-set '{}'".format(
            config["azure_cluster"]["availability_set"])

    cloud_init = ""
    # by default, if this is a unique machine, then itself would have a cloud-init file
    cldinit_appendix = "cloud_init_{}.txt".format(vmname)
    # we support heterogeneous cluster that has several different types of worker nodes
    # if later there are differences other than vm_size, we can consider adding a field
    # called "spec_name" for a spec. as for now, workers are different only in vm_size
    if "worker" in spec["role"]:
        cldinit_appendix = "cloud_init_worker_{}.txt".format(spec["vm_size"])
    elif len(mul_ex_role_in_spec) == 1:
        cldinit_appendix = "cloud_init_{}.txt".format(mul_ex_role_in_spec[0])
    cloud_init_file = spec.get(
        "cloud_init_file", 'deploy/cloud-config/{}'.format(cldinit_appendix))
    if os.path.exists(cloud_init_file):
        cloud_init = "--custom-data {}".format(cloud_init_file)

    # default sku and size by role

    storage_sku, os_disk_size_gb, data_disk_sizes_gb, disk_id = "", "", "", 0
    if "managed_disks" in spec:
        for st in spec["managed_disks"]:
            if "is_os" in st and st["is_os"]:
                assert st["disk_num"] == 1 and "Could have only 1 OS disk!"
                storage_sku += "os={}".format(st.get("sku",
                                                     config["azure_cluster"]["os_storage_sku"]))
                os_disk_size_gb = "--os-disk-size-gb " + \
                    str(st.get("size_gb",
                               config["azure_cluster"]["os_storage_sz"]))
            elif len(mul_ex_role_in_spec) == 1:
                storage_sku += " " + " ".join(["{}={}".format(dsk_id, st.get("sku", config["azure_cluster"][
                    "vm_local_storage_sku"])) for dsk_id in range(disk_id, disk_id + st["disk_num"])])
                data_disk_sizes_gb += " " + \
                    " ".join([str(st.get("size_gb", config["azure_cluster"]
                                         ["{}_local_storage_sz".format(mul_ex_role_in_spec[0])]))] * st["disk_num"])
            elif "nfs" in spec["role"]:
                storage_sku += " " + " ".join(["{}={}".format(dsk_id, st.get("sku", config["azure_cluster"][
                    "nfs_data_disk_sku"])) for dsk_id in range(disk_id, disk_id + st["disk_num"])])
                data_disk_sizes_gb += " " + \
                    " ".join([str(st.get("size_gb", config["azure_cluster"]
                                         ["nfs_data_disk_sz"]))] * st["disk_num"])
        disk_id += st["disk_num"]
    else:
        if len(mul_ex_role_in_spec) == 1:
            data_disk_sizes_gb += " " + \
                str(config["azure_cluster"]["{}_local_storage_sz".format(mul_ex_role_in_spec[0])])
            storage_sku = config["azure_cluster"]["vm_local_storage_sku"]
        if "nfs" in spec["role"]:
            nfs_dd_sz, nfs_dd_num = config["azure_cluster"]["nfs_data_disk_sz"], config["azure_cluster"]["nfs_data_disk_num"]
            data_disk_sizes_gb += " " + " ".join([str(nfs_dd_sz)]*nfs_dd_num)
            storage_sku = storage_sku if "infra" in spec[
                "role"] else config["azure_cluster"]["nfs_data_disk_sku"]

    if "vm_size" in spec:
        vm_size = spec["vm_size"]
    else:
        if "infra" in spec["role"]:
            vm_size = config["azure_cluster"]["{}_vm_size".format(mul_ex_role_in_spec[0])]
        elif "nfs" in spec["role"]:
            vm_size = config["azure_cluster"]["nfs_vm_size"]

    cmd = """
        az vm create --resource-group {} \
             --name {} \
             --tags {} \
             --image {} \
             {} \
             --public-ip-address-dns-name {} \
             --location {} \
             --size {} \
             --vnet-name {} \
             --subnet mySubnet \
             --nsg {} \
             --admin-username {} \
             {} \
             --storage-sku {}\
             {} \
             --data-disk-sizes-gb {}\
             {} \
             {} \
    """.format(config["azure_cluster"]["resource_group"],
               vmname,
               "role=" + '-'.join(spec["role"]),
               spec.get("vm_image", config["azure_cluster"]["vm_image"]),
               priv_ip,
               vmname,
               config["azure_cluster"]["azure_location"],
               vm_size,
               config["azure_cluster"]["vnet_name"],
               config["azure_cluster"][nsg],
               config["cloud_config_nsg_rules"]["default_admin_username"],
               cloud_init,
               storage_sku,
               os_disk_size_gb,
               data_disk_sizes_gb,
               auth,
               availability_set)

    if "other_params" in spec:
        for k, v in spec["other_params"]:
            cmd += " --{} {}".format(k, v)

    execute_or_dump_locally(cmd, verbose, dryrun, output_file)
    cmd = ' '.join(cmd.split())
    return cmd


def list_vm(config, verbose=True):
    cmd = """
        az vm list --resource-group %s
        """ % (config["azure_cluster"]["resource_group"])
    output = utils.exec_cmd_local(cmd, verbose)
    allvm = json.loads(output)
    vminfo = {}
    for onevm in allvm:
        vmname = onevm["name"]
        print("VM ... %s" % vmname)
        cmd1 = """ az vm show -d -g %s -n %s""" % (
            config["azure_cluster"]["resource_group"], vmname)
        output1 = utils.exec_cmd_local(cmd1, verbose)
        json1 = json.loads(output1)
        vminfo[vmname] = json1
        if verbose:
            print(json1)
    return vminfo


def vm_interconnects(config, args):
    vminfo = list_vm(config, False)
    ip_list, infra_ip_list = [], []
    for name, onevm in vminfo.items():
        ip_list.append(onevm["publicIps"] + "/32")
        if 'infra' in onevm['tags']['role']:
            infra_ip_list.append(onevm["publicIps"] + "/32")
    allowed_incoming_ips = " ".join(ip_list)
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
        """ % (config["azure_cluster"]["resource_group"],
               config["azure_cluster"]["nsg_name"],
               config["cloud_config_nsg_rules"]["inter_connect"]["tcp_port_ranges"],
               allowed_incoming_ips
               )
    allowed_incoming_infra_ips = " ".join(infra_ip_list)
    cmd += """
        ; az network nsg rule create \
            --resource-group %s \
            --nsg-name %s \
            --name nfs_allow_master \
            --protocol tcp \
            --priority 1400 \
            --destination-port-ranges %s \
            --source-address-prefixes %s \
            --access allow
        """ % (config["azure_cluster"]["resource_group"],
               config["azure_cluster"]["nfs_nsg_name"],
               config["cloud_config_nsg_rules"]["nfs_allow_master"]["tcp_port_ranges"],
               allowed_incoming_infra_ips
               )
    execute_or_dump_locally(cmd, args.verbose, args.dryrun, args.output)


def get_deployed_cluster_info(config, args):
    vminfo = list_vm(config, False)
    brief = {}
    for name, spec in vminfo.items():
        brief_spec = {}
        brief_spec["admin_username"] = spec["osProfile"]["adminUsername"]
        brief_spec["public_ip"] = spec["publicIps"]
        brief_spec["private_ip"] = spec["privateIps"]
        brief_spec["fqdns"] = spec["fqdns"]
        brief_spec["role"] = spec["tags"]["role"].split('-')
        brief[name] = brief_spec
    args.output = "status.yaml" if not args.output else args.output
    with open(args.output, "w") as wf:
        yaml.safe_dump({"machines": brief}, wf)


def whitelist_source_address_prefixes():
    resource_group = config["azure_cluster"]["resource_group"]
    nsg_name = config["azure_cluster"]["nsg_name"]

    cmd = """
        az network nsg rule list \
            --resource-group %s \
            --nsg-name %s
        """ % (resource_group,
               nsg_name)

    output = utils.exec_cmd_local(cmd)

    try:
        rules = json.loads(output)
        for rule in rules:
            if rule.get("name") == "whitelist":
                return rule.get("sourceAddressPrefixes", [])
    except Exception as e:
        print("Exception: %s" % e)

    return []


def add_nsg_rule_whitelist(ips, dry_run=False):
    # Replicating dev_network access for whitelisting users
    source_address_prefixes = whitelist_source_address_prefixes()
    if len(source_address_prefixes) == 0:
        dev_network = config["cloud_config_nsg_rules"]["dev_network"]
        source_address_prefixes = dev_network.get("source_addresses_prefixes")

        if source_address_prefixes is None:
            print("Please setup source_addresses_prefixes in config.yaml")
            exit()

        if isinstance(source_address_prefixes, str):
            source_address_prefixes = source_address_prefixes.split(" ")

    # Assume ips is a comma separated string if valid
    if ips is not None and ips != "":
        source_address_prefixes += ips.split(",")

    # Safe guard against overlapping IP range
    source_address_prefixes = utils.keep_widest_subnet(source_address_prefixes)

    source_address_prefixes = " ".join(list(set(source_address_prefixes)))

    resource_group = config["azure_cluster"]["resource_group"]
    nsg_name = config["azure_cluster"]["nsg_name"]
    tcp_port_ranges = config["cloud_config_nsg_rules"]["tcp_port_ranges"]

    cmd = """
        az network nsg rule create \
            --resource-group %s \
            --nsg-name %s \
            --name whitelist \
            --protocol tcp \
            --priority 1005 \
            --destination-port-ranges %s \
            --source-address-prefixes %s \
            --access allow
        """ % (resource_group,
               nsg_name,
               tcp_port_ranges,
               source_address_prefixes)

    if not dry_run:
        output = utils.exec_cmd_local(cmd)
        print(output)


def delete_nsg_rule_whitelist(dry_run=False):
    resource_group = config["azure_cluster"]["resource_group"]
    nsg_name = config["azure_cluster"]["nsg_name"]

    cmd = """
        az network nsg rule delete \
            --resource-group %s \
            --nsg-name %s \
            --name whitelist
        """ % (resource_group,
               nsg_name)

    if not dry_run:
        output = utils.exec_cmd_local(cmd)
        print(output)


def run_command(command, config, args, nargs):
    if command == "prerender":
        gen_machine_list_4_deploy_action(args.output, config)
    if command == "deploy":
        deploy_cluster(config, args)
        add_machines(config, args)
    if command == "deployframework":
        deploy_cluster(config, args)
    if command == "addmachines":
        add_machines(config, args)
    if command == "interconnect":
        vm_interconnects(config, args)
    if command == "listcluster":
        get_deployed_cluster_info(config, args)
    elif command == "whitelist":
        set_subscription(config)
        if nargs[0] == "add":
            ips = None if len(nargs) == 1 else nargs[1]
            add_nsg_rule_whitelist(ips, args.dryrun)
        elif nargs[0] == "delete":
            delete_nsg_rule_whitelist(args.dryrun)
        

if __name__ == "__main__":
    dirpath = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
    os.chdir(dirpath)
    parser = argparse.ArgumentParser(prog='cloud_init_aztools.py',
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=textwrap.dedent('''\
Create and manage a Azure VM cluster.

Prerequest:
* Create config.yaml according to instruction in docs/deployment/azure/configure.md.

Command:
    prerender Add complementary information required to create an Azure VM cluster based on given config.yaml file,
        both config.yaml and the complementary file generated are used to describe one-time action
    scaleup Scale up operation.
    scaledown shutdown a particular VM.
    list list VMs.
    interconnect create network links among VMs
    genconfig Generate configuration files to describe the static status for Azure VM cluster.
    '''))
    parser.add_argument(
        "command", help="See above for the list of valid command")
    parser.add_argument('nargs', nargs=argparse.REMAINDER,
                        help="Additional command argument")
    parser.add_argument('-cnf', '--config', action='append', help='Specify the config files you want to load, later ones \
        would overwrite former ones, e.g., -cnf config.yaml -cnf az_complementary.yaml')
    parser.add_argument('-b', '--batch_size', type=int, default=8,
                        help='batch size that we add machines')
    parser.add_argument('-wt', '--wait_time', type=int, default=360,
                        help='max time that we would wait for a command to execute')
    parser.add_argument('-o', '--output', default='',
                        help='Specify the output file path')
    parser.add_argument('-v', '--verbose',
                        help='Verbose mode', action="store_true")
    parser.add_argument(
        '-d', '--dryrun', help='Dry run -- no actual execution', action="store_true")
    args = parser.parse_args()
    command = args.command
    nargs = args.nargs
    config = load_config_based_on_command(command)
    run_command(command, config, args, nargs)
