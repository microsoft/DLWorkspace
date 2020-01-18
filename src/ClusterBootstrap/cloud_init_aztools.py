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


def update_config_resgrp(config):
    """load resource group related config info"""
    if "resource_group_name" not in config["azure_cluster"]:
        config["azure_cluster"]["resource_group_name"] = config["cluster_name"] + "ResGrp"
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


def execute_or_dump_locally(cmd, verbose, output_file):
    cmd = ' '.join(cmd.split())+'\n'
    if verbose:
        print(cmd)
    if output_file == '':
        output = utils.exec_cmd_local(cmd)
        if verbose:
            print(output)
        return output
    else:
        with open(output_file, 'a') as wf:
            wf.write(cmd)


def create_group(config, verbose, output_file):
    cmd = """az group create --name %s --location %s
        """ % (config["azure_cluster"]["resource_group_name"], config["azure_cluster"]["azure_location"])
    execute_or_dump_locally(cmd, verbose, output_file)


def create_vnet(config, verbose, output_file):
    cmd = """az network vnet create \
            --resource-group %s \
            --name %s \
            --address-prefix %s \
            --subnet-name mySubnet \
            --subnet-prefix %s
        """ % (config["azure_cluster"]["resource_group_name"],
               config["azure_cluster"]["vnet_name"],
               config["cloud_config"]["vnet_range"],
               config["cloud_config"]["vnet_range"])
    execute_or_dump_locally(cmd, verbose, output_file)


def create_nsg(config, verbose, output_file):
    assert "source_addresses_prefixes" in config["cloud_config"]["dev_network"] and "Please \
    setup source_addresses_prefixes in config.yaml, otherwise, your cluster cannot be accessed"
    # if "source_addresses_prefixes" in config["cloud_config"]["dev_network"]:
    source_addresses_prefixes = config["cloud_config"][
        "dev_network"]["source_addresses_prefixes"]
    if isinstance(source_addresses_prefixes, list):
        source_addresses_prefixes = " ".join(
            list(set(source_addresses_prefixes)))
    # else:
    #     print("Please setup source_addresses_prefixes in config.yaml, otherwise, your cluster cannot be accessed \
    #         from outside")
    #     exit()
    cmd = """az network nsg create \
            --resource-group %s \
            --name %s
        """ % (config["azure_cluster"]["resource_group_name"],
               config["azure_cluster"]["nsg_name"])
    execute_or_dump_locally(cmd, verbose, output_file)

    if "tcp_port_ranges" in config["cloud_config"]:
        cmd = """az network nsg rule create \
                --resource-group %s \
                --nsg-name %s \
                --name allowalltcp \
                --protocol tcp \
                --priority 1000 \
                --destination-port-ranges %s \
                --access allow
            """ % (config["azure_cluster"]["resource_group_name"],
                   config["azure_cluster"]["nsg_name"],
                   config["cloud_config"]["tcp_port_ranges"]
                   )
        execute_or_dump_locally(cmd, verbose, output_file)

    if "udp_port_ranges" in config["cloud_config"]:
        cmd = """az network nsg rule create \
                --resource-group %s \
                --nsg-name %s \
                --name allowalludp \
                --protocol udp \
                --priority 1010 \
                --destination-port-ranges %s \
                --access allow
            """ % (config["azure_cluster"]["resource_group_name"],
                   config["azure_cluster"]["nsg_name"],
                   config["cloud_config"]["udp_port_ranges"]
                   )
        execute_or_dump_locally(cmd, verbose, output_file)

    cmd = """az network nsg rule create \
            --resource-group %s \
            --nsg-name %s \
            --name allowdevtcp \
            --protocol tcp \
            --priority 900 \
            --destination-port-ranges %s \
            --source-address-prefixes %s \
            --access allow
        """ % (config["azure_cluster"]["resource_group_name"],
               config["azure_cluster"]["nsg_name"],
               config["cloud_config"]["dev_network"]["tcp_port_ranges"],
               source_addresses_prefixes
               )
    execute_or_dump_locally(cmd, verbose, output_file)


def create_nfs_nsg(config, verbose, output_file):
    assert "source_addresses_prefixes" in config["cloud_config"]["dev_network"] and "Please \
    setup source_addresses_prefixes in config.yaml, otherwise, your cluster cannot be accessed"
    source_addresses_prefixes = config["cloud_config"][
        "dev_network"]["source_addresses_prefixes"]
    if int(config["azure_cluster"]["nfs_node_num"]) > 0:
        cmd = """az network nsg create \
                --resource-group %s \
                --name %s
            """ % (config["azure_cluster"]["resource_group_name"],
                   config["azure_cluster"]["nfs_nsg_name"])
        execute_or_dump_locally(cmd, verbose, output_file)

    merged_ip = keep_widest_subnet(
        config["cloud_config"]["nfs_ssh"]["source_ips"] + source_addresses_prefixes)
    cmd = """az network nsg rule create \
            --resource-group %s \
            --nsg-name %s \
            --name allow_ssh\
            --priority 1200 \
            --destination-port-ranges %s \
            --source-address-prefixes %s \
            --access allow
        """ % (config["azure_cluster"]["resource_group_name"],
               config["azure_cluster"]["nfs_nsg_name"],
               config["cloud_config"]["nfs_ssh"]["port"],
               " ".join(merged_ip),
               )
    execute_or_dump_locally(cmd, verbose, output_file)

    cmd = """az network nsg rule create \
            --resource-group %s \
            --nsg-name %s \
            --name allow_share \
            --priority 1300 \
            --source-address-prefixes %s \
            --destination-port-ranges \'*\' \
            --access allow
        """ % (config["azure_cluster"]["resource_group_name"],
               config["azure_cluster"]["nfs_nsg_name"],
               " ".join(config["cloud_config"]["nfs_share"]["source_ips"]),
               )
    execute_or_dump_locally(cmd, verbose, output_file)


def deploy_cluster(config, verbose, output_file):
    if output_file != "":
        with open(output_file, 'w') as f:
            f.write("#!/bin/bash\n")
    create_group(config, verbose, output_file)
    create_vnet(config, verbose, output_file)
    create_nsg(config, verbose, output_file)
    create_nfs_nsg(config, verbose, output_file)
    os.system('chmod +x ' + output_file)


def validate_machine_spec(config, spec):
    assert "role" in spec and ((set(spec["role"]) - set(config["allroles"])) == set()) and \
        "must specify valid role for vm!"
    if "name" in spec:
        assert spec["num"] <= 1 and "cannot overwirte name for multiple machines one time!"
    if "nfs" in spec["role"]:
        assert spec["num"] <= 1 and "NFS machine spec must be configured one by one!"
    if "worker" in spec["role"]:
        assert "gpu_type" in spec and "Must specify gpu_type for worker node!"


def render_infra_and_nfs(complementary_file_name, config):
    """based on info from config.yaml, generate the expected machine names etc."""

    # generate infra and nfs vmname, infer infra ip, dump to cluster.yaml, skip nfs ip

    # cloud_init_deploy.py render templates.

    # deploy master and nfs node.

    # complete nfs mount ip info in cluster.yaml['mountpoints']
    cc = {}
    cc["cluster_name"] = config["cluster_name"]
    cc["useclusterfile"] = True
    cc["deploydockerETCD"] = False
    cc["platform-scripts"] = "ubuntu"
    cc["basic_auth"] = "%s,admin,1000" % uuid.uuid4().hex[:16]
    domain_mapping = {
        "regular": "%s.cloudapp.azure.com" % config["azure_cluster"]["azure_location"],
        "low": config.get("network_domain", config["azure_cluster"]["default_low_priority_domain"])}
    cc["machines"] = {}
    for spec in config["azure_cluster"]["vm"]:
        validate_machine_spec(config, spec)
        for i in range(spec["num"]):
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
                if k == "num":
                    continue
                cc["machines"][vmname][k] = v
            if "kube_label_groups" not in spec:
                if "infra" in spec["role"]:
                    cc["machines"][vmname]["kube_label_groups"] = [
                        "all", "etcd_node", "etcd_node_1"]
                elif "worker" in spec["role"]:
                    cc["machines"][vmname]["kube_label_groups"] = [
                        "all", "worker_node"]

    cc["etcd_node_num"] = len(
        [mv for mv in list(cc["machines"].values()) if 'infra' in mv['role']])
    cc["admin_username"] = config["cloud_config"]["default_admin_username"]
    cc["network"] = {"domain": domain_mapping[config["priority"]]}
    if complementary_file_name != '':
        with open(complementary_file_name, 'w') as outfile:
            yaml.dump(cc, outfile, default_flow_style=False)
    return cc


def add_machines(config, args, outputfile):
    os.system('rm -f ' + outputfile)
    for vmname, spec in config["machines"].items():
        updated_spec = add_machine(vmname, spec, args.verbose, outputfile)
        config["machines"][vmname] = updated_spec
    if os.path.exists(outputfile):
        os.system('chmod +x ' + outputfile)


def is_independent_nfs(role):
    """NFS not on infra"""
    return "nfs" in role and not (set(["infra", "etcd", "kubernetes_master"]) & set(role))


def add_machine(vmname, spec, verbose, output_file):
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
    cldinit_appendix = "cloud_init_{}.txt".format(vmname)
    if "infra" in spec["role"]:
        cldinit_appendix = "cloud_init_infra.txt"
    elif "worker" in spec["role"]:
        cldinit_appendix = "cloud_init_worker.txt"
    cloud_init_file = spec.get(
        "cloud_init_file", 'deploy/cloud-config/{}'.format(cldinit_appendix))
    if os.path.exists(cloud_init_file):
        cloud_init = "--custom-data {}".format(cloud_init_file)

    # default sku and size by role

    storage_sku, os_disk_size_gb, data_disk_sizes_gb, disk_id = "", "", "", 0
    if "storage" in spec:
        for st in spec["storage"]:
            if "is_os" in st and st["is_os"]:
                assert st["disk_num"] == 1 and "Could have only 1 OS disk!"
                storage_sku += "os={}".format(st.get("sku",
                                                     config["azure_cluster"]["os_storage_sku"]))
                os_disk_size_gb = "--os-disk-size-gb " + \
                    str(st.get("size_gb",
                               config["azure_cluster"]["os_storage_sz"]))
            elif "infra" in spec["role"]:
                storage_sku += " " + " ".join(["{}={}".format(dsk_id, st.get("sku", config["azure_cluster"][
                    "vm_local_storage_sku"])) for dsk_id in range(disk_id, disk_id + st["disk_num"])])
                data_disk_sizes_gb += " " + \
                    " ".join([str(st.get("size_gb", config["azure_cluster"]
                                         ["infra_local_storage_sz"]))] * st["disk_num"])
            elif "worker" in spec["role"]:
                storage_sku += " " + " ".join(["{}={}".format(dsk_id, st.get("sku", config["azure_cluster"][
                    "vm_local_storage_sku"])) for dsk_id in range(disk_id, disk_id + st["disk_num"])])
                data_disk_sizes_gb += " " + \
                    " ".join([str(st.get("size_gb", config["azure_cluster"]
                                         ["worker_local_storage_sz"]))] * st["disk_num"])
            elif "nfs" in spec["role"]:
                storage_sku += " " + " ".join(["{}={}".format(dsk_id, st.get("sku", config["azure_cluster"][
                    "nfs_data_disk_sku"])) for dsk_id in range(disk_id, disk_id + st["disk_num"])])
                data_disk_sizes_gb += " " + \
                    " ".join([str(st.get("size_gb", config["azure_cluster"]
                                         ["nfs_data_disk_sz"]))] * st["disk_num"])
        disk_id += st["disk_num"]
    else:
        if "infra" in spec["role"]:
            data_disk_sizes_gb += " " + \
                str(config["azure_cluster"]["infra_local_storage_sz"])
            storage_sku = config["azure_cluster"]["vm_local_storage_sku"]
        elif "worker" in spec["role"]:
            data_disk_sizes_gb += " " + \
                str(config["azure_cluster"]["worker_local_storage_sz"])
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
            vm_size = config["azure_cluster"]["infra_vm_size"]
        elif "worker" in spec["role"]:
            vm_size = config["azure_cluster"]["worker_vm_size"]
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
    """.format(config["azure_cluster"]["resource_group_name"],
               vmname,
               "role=" + '-'.join(spec["role"]),
               spec.get("vm_image", config["azure_cluster"]["vm_image"]),
               priv_ip,
               vmname,
               config["azure_cluster"]["azure_location"],
               vm_size,
               config["azure_cluster"]["vnet_name"],
               config["azure_cluster"][nsg],
               config["cloud_config"]["default_admin_username"],
               cloud_init,
               storage_sku,
               os_disk_size_gb,
               data_disk_sizes_gb,
               auth,
               availability_set)

    if "other_params" in spec:
        for k, v in spec["other_params"]:
            cmd += " --{} {}".format(k, v)
    # cmd += ' &'
    execute_or_dump_locally(cmd, verbose, output_file)


def list_vm(config, verbose=True):
    cmd = """
        az vm list --resource-group %s
        """ % (config["azure_cluster"]["resource_group_name"])
    output = utils.exec_cmd_local(cmd)
    allvm = json.loads(output)
    vminfo = {}
    for onevm in allvm:
        vmname = onevm["name"]
        print("VM ... %s" % vmname)
        cmd1 = """ az vm show -d -g %s -n %s""" % (
            config["azure_cluster"]["resource_group_name"], vmname)
        output1 = utils.exec_cmd_local(cmd1)
        json1 = json.loads(output1)
        vminfo[vmname] = json1
        if verbose:
            print(json1)
    return vminfo


def vm_interconnects(config, verbose, output_file):
    vminfo = list_vm(config, False)
    ports = []
    for name, onevm in vminfo.items():
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
        """ % (config["azure_cluster"]["resource_group_name"],
               config["azure_cluster"]["nsg_name"],
               config["cloud_config"]["inter_connect"]["tcp_port_ranges"],
               portinfo
               )
    execute_or_dump_locally(cmd, verbose, output_file)


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
    with open(args.output, "w") as wf:
        yaml.dump({"machines": brief}, wf)


def run_command(command, config, args, nargs):
    if command == "prerender":
        render_infra_and_nfs(args.output, config)
    config = update_config_resgrp(config)
    if command == "deploy":
        deploy_cluster(config, args.verbose, "scripts/deploy_framework.sh")
        config = load_sshkey(config)
        add_machines(config, args, "scripts/add_machines.sh")
    if command == "deployframework":
        deploy_cluster(config, args.verbose, args.output)
    if command == "addmachines":
        config = load_sshkey(config)
        add_machines(config, args, args.output)
    if command == "interconnect":
        vm_interconnects(config, args.verbose, args.output)
    if command == "listcluster":
        get_deployed_cluster_info(config, args)


if __name__ == "__main__":
    dirpath = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
    os.chdir(dirpath)
    parser = argparse.ArgumentParser(prog='az_utils.py',
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
    parser.add_argument('-o', '--output', default='',
                        help='Specify the output file path')
    parser.add_argument('-v', '--verbose', type=bool,
                        help='Verbose mode', default='False')
    args = parser.parse_args()
    command = args.command
    nargs = args.nargs
    default_config = init_config()
    config = add_configs_in_order(args.config, default_config)
    run_command(command, config, args, nargs)
