#!/usr/bin/python3
import os
import sys
import yaml
import json
import textwrap
import argparse

from az_params import *
from params import *
from utils import random_str, keep_widest_subnet, \
    multiprocess_with_func_arg_tuples, exec_cmd_local, \
    execute_or_dump_locally
from az_utils import \
    set_subscription, \
    add_nsg_rule_whitelist, \
    remove_nsg_rule_whitelist, \
    delete_nsg_rule_whitelist, \
    create_nsg_rule, \
    delete_nsg_rule, \
    create_nsg_rules_with_service_tags, \
    create_nsg_rule_with_service_tag, \
    delete_nsg_rules_with_service_tags, \
    create_logging_storage_account, \
    create_logging_container, \
    delete_logging_storage_account, \
    get_connection_string_for_logging_storage_account

from cloud_init_deploy import load_node_list_by_role_from_config
from ctl import run_kubectl
sys.path.append("../utils")
from ConfigUtils import add_configs_in_order, merge_config
from constants import ENV_CNF_YAML, ACTION_YAML, STATUS_YAML


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
        config_file_list = [ENV_CNF_YAML]
        if command in ["deploy", "deployframework", "addmachines"]:
            config_file_list.append(ACTION_YAML)
        if command in ["delete_nodes", "dynamic_around", "interconnect"]:
            config_file_list.append(STATUS_YAML)
    config = add_configs_in_order(config_file_list, default_config)
    if command not in ["prerender"]:
        config = update_config_resgrp(config)
    if command in ["deploy", "addmachines", "dynamic_around"]:
        config = load_sshkey(config)
    return config


def update_config_resgrp(config):
    """load resource group related config info"""
    cnf_az_cluster = config["azure_cluster"]
    cnf_az_cluster["resource_group"] = cnf_az_cluster.get(
        "resource_group", config["cluster_name"] + "ResGrp")
    cnf_az_cluster["vnet_name"] = config["cluster_name"] + "-VNet"
    cnf_az_cluster["subnet_name"] = cnf_az_cluster.get(
        "subnet_name", config["cluster_name"] + "-subnet")
    cnf_az_cluster["storage_account_name"] = config["cluster_name"] + "storage"
    cnf_az_cluster["nsg_name"] = config.get("nsg_name", config[
                                    "cluster_name"] + "-nsg")
    cnf_az_cluster["nfs_nsg_name"] = config.get("nfs_nsg_name", 
        config["cluster_name"] + ["", "-nfs"][int(int(config["azure_cluster"][
                                              "nfs_node_num"]) > 0)] + "-nsg")
    return config


def load_sshkey(config):
    assert os.path.exists(
        './deploy/sshkey/id_rsa.pub'), "Generate SSHKey first!"
    with open('./deploy/sshkey/id_rsa.pub') as f:
        config["azure_cluster"]["sshkey"] = f.read()
    return config


def create_group(config, args):
    subscription = "--subscription \"{}\"".format(
        config["azure_cluster"]["subscription"]) if "subscription" in config["azure_cluster"] else ""
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
    listcmd = "az vm availability-set list --resource-group {} --query \"[].name\"".format(
        config["azure_cluster"]["resource_group"])
    as_res = execute_or_dump_locally(listcmd, args.verbose, False, args.output)
    try:
        existing_as = set(json.loads(as_res))
        availability_sets -= existing_as
    except:
        print("no existing availability sets found")
    cmd = ';'.join(["""az vm availability-set create --name {} --resource-group {} --location {} {}
        """.format(avs, config["azure_cluster"]["resource_group"], config["azure_cluster"]["azure_location"], subscription) for avs in availability_sets])
    execute_or_dump_locally(cmd, args.verbose, args.dryrun, args.output)


def create_vnet(config, args):
    cmd = """az network vnet create \
            --resource-group {} \
            --name {} \
            --address-prefix {} \
            --subnet-name {} \
            --subnet-prefix {}
        """.format(config["azure_cluster"]["resource_group"],
                   config["azure_cluster"]["vnet_name"],
                   config["cloud_config_nsg_rules"]["vnet_range"],
                   config["azure_cluster"]["subnet_name"],
                   config["cloud_config_nsg_rules"]["vnet_range"])
    execute_or_dump_locally(cmd, args.verbose, args.dryrun, args.output)


def create_main_nsg(config, args):
    """
    create main nsg, which infra and worker nodes follow
    """
    # create service tag to allow corpnet machines
    main_nsg_name = config["azure_cluster"]["nsg_name"]
    resource_group = config["azure_cluster"]["resource_group"]
    dev_ports = config["cloud_config_nsg_rules"]["corpnet_dev_ports"]
    user_ports = config["cloud_config_nsg_rules"]["corpnet_user_ports"]
    service_tags = config["cloud_config_nsg_rules"]["service_tags"]
    cmd = """az network nsg create --resource-group {} --name {}""".format(
        resource_group, main_nsg_name)
    execute_or_dump_locally(cmd, args.verbose, args.dryrun, args.output)
    priority = 1500
    # set nsg rules for devs
    for tag in service_tags:
        create_nsg_rule(resource_group, main_nsg_name, priority, 
                        "Main-Allow-Dev-{}".format(tag), dev_ports, tag, args)
        priority += 1
    # set nsg rules for users
    priority = 1600
    for tag in service_tags:
        create_nsg_rule(resource_group, main_nsg_name, priority, 
                        "Main-Allow-User-{}".format(tag), user_ports, tag, args)
        priority += 1


def create_nfs_nsg(config, args):
    nfs_nsg_name = config["azure_cluster"]["nfs_nsg_name"]
    resource_group = config["azure_cluster"]["resource_group"]
    nfs_ports = config["cloud_config_nsg_rules"]["nfs_ports"]
    nfs_nodes, config = load_node_list_by_role_from_config(config, ["nfs"])
    infra_nodes, config = load_node_list_by_role_from_config(config, ["infra"])
    if len(set(nfs_nodes) - set(infra_nodes)):
        cmd = """az network nsg create --resource-group {} --name {}""".format(
            resource_group, nfs_nsg_name)
        execute_or_dump_locally(cmd, args.verbose, args.dryrun, args.output)
    priority = 1700
    # set nsg rules for devs, (and samba, since samba machines are all in corpnet)
    for tag in config["cloud_config_nsg_rules"]["service_tags"]:
        create_nsg_rule(resource_group, nfs_nsg_name, priority, 
        "NFS-Allow-Dev-{}".format(tag), nfs_ports, tag, args)
        priority += 1



def deploy_cluster(config, args):
    if args.output != "":
        with open(args.output, 'w') as f:
            f.write("#!/bin/bash\n")
    create_group(config, args)
    create_vnet(config, args)
    create_availability_set(config, args)
    create_main_nsg(config, args)
    create_nfs_nsg(config, args)
    need_logging = False
    for spec in config.get("machines", {}).values():
        if "kube_services" in spec and "logging" in spec["kube_services"]:
            need_logging = True
            break
    if need_logging:
        create_logging_storage_account(config, args)
        create_logging_container(config, args)    
        if args.dryrun:
            print("Warining: dry-run mode, later please manually add logging" \
                "storage connection_string to config.")
        else:
            get_connection_string_for_logging_storage_account(config, args)
            # TODO we don't load and dump here since it would break the orders
            # check whether we could do it more formally
            os.system("cat logging_config.yaml >> {}".format(ENV_CNF_YAML))

    if args.output and os.path.exists(args.output):
        os.system('chmod +x ' + args.output)


def validate_machine_spec(config, spec):
    assert "role" in spec and ((set(spec["role"]) - set(config["allroles"])) == set()), \
        "must specify valid role for vm!"
    if "name" in spec:
        assert spec["number_of_instance"] <= 1, "cannot overwirte name for multiple machines one time!"
    if "nfs" in spec["role"]:
        assert spec["number_of_instance"] <= 1, "NFS machine spec must be configured one by one!"


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
    if complementary_file_name is not None:
        complementary_file_name = ACTION_YAML if complementary_file_name == '' else complementary_file_name
        with open(complementary_file_name, 'w') as outfile:
            yaml.safe_dump(cc, outfile, default_flow_style=False)
    return cc


def add_machines(config, args):
    # we don't run az command in add_machine when batch_size is larger than 1, regardless of args.dryrun
    # instead, we would run those commands in parallel, and dump output sequentially. the machines would still
    # be added sequentially, but we could avoid overburdening devbox(sending too many request at one batch)
    delay_run = (args.batch_size > 1) and (not args.dryrun)
    # we don't execute when dryrun specified, otherwise we delay execution if possible to run in batch
    dryrun_or_delay = delay_run or args.dryrun
    commands_list = []
    for vmname, spec in config["machines"].items():
        cmd = add_machine(vmname, spec, args.verbose,
                          dryrun_or_delay, args.output)
        if delay_run:
            commands_list += cmd,
    if os.path.exists(args.output):
        os.system('chmod +x ' + args.output)
    if delay_run:
        outputs = execute_cmd_local_in_parallel(commands_list, args)
    if delay_run:
        return outputs


def delete_az_vm(config, args, vm_name):
    # TODO try delete with resource delete, if possible, remove this function
    az_cli_verbose = '--verbose' if args.verbose else ''
    resource_group = config["azure_cluster"]["resource_group"]
    delete_cmd = 'az vm delete -g {} -n {} --yes {}'.format(
        resource_group, vm_name, az_cli_verbose)
    execute_or_dump_locally(delete_cmd, args.verbose, args.dryrun, args.output)


def delete_az_resource(config, args, resource_name, resource_type):
    az_cli_verbose = '--verbose' if args.verbose else ''
    resource_group = config["azure_cluster"]["resource_group"]
    delete_cmd = 'az resource delete -g {} -n {} --resource-type {} {}'.format(
        resource_group, resource_name, resource_type, az_cli_verbose)
    execute_or_dump_locally(delete_cmd, args.verbose, args.dryrun, args.output)


def delete_az_vms(config, args, machine_list):
    os.system('rm -f ' + args.output)
    delay_run = (args.batch_size > 1) and (not args.dryrun)
    # we don't execute when dryrun specified, otherwise we delay execution if possible to run in batch
    commands_list = []
    az_cli_verbose = '--verbose' if args.verbose else ''
    for vm_name in machine_list:
        vm_spec = get_default_vm_info_json(config, vm_name, False)
        # TODO parallelize deleting resource of different nodes
        delete_az_vm(config, args, vm_name)
        # Nic must be deleted first, then public IP
        delete_az_resource(config, args, "{}VMNic".format(
            vm_name), "Microsoft.Network/networkInterfaces")
        delete_az_resource(config, args, "{}PublicIP".format(
            vm_name), "Microsoft.Network/publicIPAddresses")
        for disk in vm_spec["storageProfile"]["dataDisks"]:
            delete_az_resource(
                config, args, disk["name"], "Microsoft.Compute/disks")
        delete_az_resource(
            config, args, vm_spec["storageProfile"]["osDisk"]["name"], "Microsoft.Compute/disks")
    if os.path.exists(args.output):
        os.system('chmod +x ' + args.output)


def is_independent_nfs(role):
    """NFS not on infra"""
    return "nfs" in role and not (set(["infra", "etcd", "kubernetes_master"]) & set(role))


def execute_cmd_local_in_parallel(cmds, args):
    tuples = [(exec_cmd_local, cmd, args.verbose, 600 * args.batch_size)
              for cmd in cmds]
    res = multiprocess_with_func_arg_tuples(args.batch_size, tuples)
    return res


def add_n_machines(config, args, num_2_add):
    target_spec = None
    for spec in config["azure_cluster"]["virtual_machines"]:
        if "worker" in spec["role"]:
            target_spec = spec
            break
    assert target_spec is not None, "no worker node spec found, please specify in config.yaml"
    target_spec["number_of_instance"] = num_2_add
    config["azure_cluster"]["virtual_machines"] = [target_spec]
    # we have to dump the action config, to keep more detailed info
    # (kube_label_groups etc.), otherwise render might lose this
    node_2_add_cnf = gen_machine_list_4_deploy_action(args.output, config)
    config.update(node_2_add_cnf)
    os.system('rm -f ' + args.output)
    add_machines(config, args)
    # need to set args.output to '' since we want to dump machine list to STATUS_YAML
    script_fn, args.output = args.output, ''
    get_deployed_cluster_info(config, args)
    args.output = args.output
    vm_interconnects(config, args)


def add_machine(vmname, spec, verbose, dryrun, output_file):
    multual_exclusive_roles = set(
        ["infra", "worker", "elasticsearch", "mysqlserver", "lustre"])
    mul_ex_role_in_spec = list(set(spec["role"]) & multual_exclusive_roles)
    assert len(mul_ex_role_in_spec) <= 1, "We don't allow role overlapping between these roles:{}.".format(
        ",".join(list(multual_exclusive_roles)))
    if "pwd" in spec:
        auth = "--authentication-type password --admin-password '{}' ".format(
            spec["pwd"])
    else:
        auth = "--generate-ssh-keys --authentication-type ssh --ssh-key-value '{}' ".format(
            config["azure_cluster"]["sshkey"])

    # if just want to update private IP, then keep vmname unchanged, and only update IP.
    priv_ip = ""
    if "private_ip" in spec:
        priv_ip = "--private-ip-address {} ".format(spec["private_ip"])
    else:
        assert (not 'nfs' in spec["role"]
                ), "Must specify IP address for NFS node!"

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
    elif len(mul_ex_role_in_spec) == 1 and "lustre" not in spec["role"]:
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
                assert st["disk_num"] == 1, "Could have only 1 OS disk!"
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
                str(config["azure_cluster"]
                    ["{}_local_storage_sz".format(mul_ex_role_in_spec[0])])
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
            vm_size = config["azure_cluster"]["{}_vm_size".format(
                mul_ex_role_in_spec[0])]
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
             --subnet {} \
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
               config["azure_cluster"]["subnet_name"],
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


def get_default_vm_info_json(config, vmname, verbose=True):
    cmd = """ az vm show -d -g %s -n %s""" % (
        config["azure_cluster"]["resource_group"], vmname)
    output1 = exec_cmd_local(cmd, verbose)
    az_vm_spec = json.loads(output1)
    return az_vm_spec


def list_vm(config, verbose=True):
    cmd = """
        az vm list --resource-group %s
        """ % (config["azure_cluster"]["resource_group"])
    output = exec_cmd_local(cmd, verbose)
    allvm = json.loads(output)
    vminfo = {}
    for onevm in allvm:
        vmname = onevm["name"]
        print("VM ... %s" % vmname)
        vminfo[vmname] = get_default_vm_info_json(config, vmname, verbose)
        if verbose:
            print(vminfo[vmname])
    return vminfo


# deprecated since we now use service tag, no longer to do this ad-hoc step
def vm_interconnects(config, args):
    with open(STATUS_YAML) as f:
        vminfo = yaml.safe_load(f)
    ip_list, infra_ip_list = [], []
    for name, onevm in vminfo["machines"].items():
        ip_list.append(onevm["public_ip"] + "/32")
        if 'infra' in onevm['role']:
            infra_ip_list.append(onevm["public_ip"] + "/32")
    allowed_incoming_ips = " ".join(ip_list)
    main_nsg_name = config["azure_cluster"]["nsg_name"]
    resource_group = config["azure_cluster"]["resource_group"]
    inter_conn_ports = config["cloud_config_nsg_rules"]["inter_connect_ports"]
    priority = 1550
    create_nsg_rule(resource_group, main_nsg_name, priority, 
        "Allow-Interconnect", inter_conn_ports, allowed_incoming_ips, args)


def get_deployed_cluster_info(config, args):
    # load existing status yaml file, default {}
    output_file = STATUS_YAML if not args.output else args.output
    existing_info = {}
    if os.path.exists(output_file):
        with open(output_file) as ef:
            existing_info = yaml.safe_load(ef).get("machines", {})
    # get info from az cli
    vminfo = list_vm(config, False)
    brief = {}
    for name, spec in vminfo.items():
        brief_spec = {}
        brief_spec["admin_username"] = spec["osProfile"]["adminUsername"]
        brief_spec["vm_size"] = spec["hardwareProfile"]["vmSize"]
        brief_spec["public_ip"] = spec["publicIps"]
        brief_spec["private_ip"] = spec["privateIps"]
        brief_spec["fqdns"] = spec["fqdns"]
        brief_spec["role"] = spec["tags"]["role"].split('-')
        brief[name] = brief_spec
    # load action yaml file
    action_info = {}
    action_file = ACTION_YAML
    if os.path.exists(action_file):
        with open(action_file) as af:
            action_info = yaml.safe_load(af).get("machines", {})
    # merge and dump, based on az_cli_config(that's the real-time accurate info)
    updated_info = {}
    for vm_name, vm_spec in brief.items():
        new_spec = {}
        # fill static info that already exist or have been updated in action.yaml
        merge_config(new_spec, existing_info.get(vm_name, {}))
        merge_config(new_spec, action_info.get(vm_name, {}))
        # fill dynamic info such as ip
        merge_config(new_spec, vm_spec)
        updated_info[vm_name] = new_spec
    for vm_name, vm_spec in existing_info.items():
        if "samba" in vm_spec["role"]:
            updated_info[vm_name] = vm_spec
    with open(output_file, "w") as wf:
        yaml.safe_dump({"machines": updated_info}, wf)


def get_k8s_node_list_under_condition(config, args, k8scmd):
    '''we only do query here, so won't dump commands'''
    output = run_kubectl(config, args, [k8scmd], True)
    nodes = output.split()
    return nodes


def delete_k8s_nodes(node_list, config, args):
    for node in node_list:
        cmd = run_kubectl(config, args, ['delete node {}'.format(node)], True)


def cordon_node_2_delete_later(num_of_worker_2_cordon, config, args):
    if num_of_worker_2_cordon <= 0:
        return
    query_cmds = "get nodes -l worker=active --no-headers | grep Ready | awk '{print $1}'"
    ready_nodes = get_k8s_node_list_under_condition(config, args, query_cmds)
    for node in ready_nodes[:num_of_worker_2_cordon]:
        cmd = run_kubectl(config, args, ['cordon {}'.format(node)], True)


def delete_specified_or_cordoned_idling_nodes(config, args, num_limit=-1):
    if args.node_list:
        nodes2delete = args.node_list
    else:
        busy_cmds = "get pods -l type=job -o jsonpath='{.items[*].spec.nodeName}'"
        busy_nodes = get_k8s_node_list_under_condition(config, args, busy_cmds)
        cordoned_cmds = "get nodes -l worker=active --no-headers | grep SchedulingDisabled | awk '{print $1}'"
        # would be [] if no such node
        cordoned_nodes = get_k8s_node_list_under_condition(
            config, args, cordoned_cmds)
        cordoned_idling = set(cordoned_nodes) - set(busy_nodes)
        nodes2delete = cordoned_idling
        if args.verbose:
            print(
                "Node list not specified, would delete cordoned idling worker nodes by default")
        # with :num_limit, we always only delete min(num_limit, # of qualified node) nodes
        nodes2delete = list(nodes2delete)[:num_limit]
    if args.verbose:
        print("Deleting following nodes:\n", nodes2delete)
    delete_az_vms(config, args, nodes2delete)
    delete_k8s_nodes(nodes2delete, config, args)
    # if we don't have enough qualified node to delete, we randomly cordon some nodes so they'll be cordoned when pod on them finished
    num_of_worker_2_cordon = num_limit - len(nodes2delete)
    cordon_node_2_delete_later(num_of_worker_2_cordon, config, args)
    if not args.dryrun:
        get_deployed_cluster_info(config, args)


def dynamically_add_or_delete_around_a_num(config, args):
    # need some time for the newly added worker to register
    monitor_again_after = config.get("monitor_again_after", 10)
    while True:
        # TODO currently don't keep history of operation here. or name the bash by time?
        os.system("rm -f {}".format(args.output))
        config = load_config_based_on_command("dynamic_around")
        dynamic_worker_num = config.get("dynamic_worker_num", -1)
        if dynamic_worker_num < 0:
            print(
                "This round would be skipped. Please specify dynamic_worker_num in config.")
            os.system("sleep {}m".format(monitor_again_after))
            continue
        query_cmds = "get nodes -l worker=active --no-headers | awk '{print $1}'"
        k8s_worker_nodes = get_k8s_node_list_under_condition(
            config, args, query_cmds)
        worker_in_records, config = load_node_list_by_role_from_config(config, [
                                                                       "worker"], False)
        print("worker in records:\n", worker_in_records)
        print("Dynamically scaling number of workers:\n {}/{} worker nodes registered in k8s, targeting {}".format(
            len(k8s_worker_nodes), len(worker_in_records), dynamic_worker_num))
        delta = dynamic_worker_num - len(worker_in_records)
        if delta > 0:
            add_n_machines(config, args, delta)
        elif delta < 0:
            delete_specified_or_cordoned_idling_nodes(config, args, -delta)
        os.system("sleep {}m".format(monitor_again_after))


def white_list_ip(config, args):
    if args.nargs[0] == "add":
        ips = None if len(args.nargs) == 1 else args.nargs[1]
        add_nsg_rule_whitelist(config, args, ips)
    elif args.nargs[0] == "remove":
        ips = None if len(args.nargs) == 1 else args.nargs[1]
        remove_nsg_rule_whitelist(config, args, ips)
    elif args.nargs[0] == "delete":
        delete_nsg_rule_whitelist(config, args)


def logging_storage(config, args):
    if args.nargs[0] == "create":
        create_logging_storage_account(config, args)
        create_logging_container(config, args)
    elif args.nargs[0] == "delete":
        response = input(
            "Delete logging storage? (Please type YES to confirm)")
        if response == "YES":
            delete_logging_storage_account(config, args)
    elif args.nargs[0] == "connection_string":
        get_connection_string_for_logging_storage_account(config, args)


def run_command(command, config, args):
    if command == "prerender":
        gen_machine_list_4_deploy_action(args.output, config)
    if command == "deploy":
        deploy_cluster(config, args)
        add_machines(config, args)
    if command == "deployframework":
        deploy_cluster(config, args)
    if command == "addmachines":
        os.system('rm -f ' + args.output)
        add_machines(config, args)
    if command == "interconnect":
        vm_interconnects(config, args)
    if command == "listcluster":
        get_deployed_cluster_info(config, args)
    if command == "whitelist":
        white_list_ip(config, args)
    if command == "service_tag_rules":
        service_tag_func = eval(
            "{}_nsg_rules_with_service_tags".format(args.nargs[0]))
        service_tag_func(config, args)
    if command == "delete_nodes":
        delete_specified_or_cordoned_idling_nodes(config, args)
    if command == "dynamic_around":
        dynamically_add_or_delete_around_a_num(config, args)
    if command == "logging_storage":
        logging_storage(config, args)


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
    parser.add_argument('-n', '--node_list', action='append', help='Node list')
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
    config = load_config_based_on_command(command)
    set_subscription(config)
    run_command(command, config, args)
