#!/usr/bin/python3
import os
import sys
import yaml
import textwrap
import argparse
from az_params import *
from params import *
from utils import mergeDict, random_str
import uuid


def init_config():
    config = {}
    for k, v in default_config_parameters.items():
        config[k] = v
    for k, v in default_az_parameters.items():
        config[k] = v
    return config


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
        assert "role" in spec and ((set(spec["role"]) - set(config["allroles"])) == set()) and \
            "must specify valid role for vm!"
        for i in range(spec["num"]):
            # if explicitly specified a name, we use it
            if "name" in spec:
                assert spec["num"] == 1 and "cannot overwirte name for multiple machines one time!"
                vmname = spec["name"]
            else:
                vmname_pref = spec["prefix"] if "prefix" in spec else "{}-{}".format(
                    config["cluster_name"], '-'.join(spec["role"]))
                vmname = vmname_pref + '-' + random_str(6)
            cc["machines"][vmname] = {'role': spec["role"]}

    cc["etcd_node_num"] = len(
        [mv for mv in cc["machines"].values() if 'infra' in mv['role']])
    cc["admin_username"] = config["cloud_config"]["default_admin_username"]
    cc["network"] = {"domain": domain_mapping[config["priority"]]}
    if complementary_file_name != '':
        with open(complementary_file_name, 'w') as outfile:
            yaml.dump(cc, outfile, default_flow_style=False)
    return cc


def run_command(command, config, args, nargs):
    if command == "prerender":
        render_infra_and_nfs(args.complementary, config)


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
    output_file_name = "azcluster.yaml"
    parser.add_argument("--complementary",
                        help="Specify complementary file name the number of infra nodes",
                        action="store", default="complementary.yaml")
    args = parser.parse_args()
    command = args.command
    nargs = args.nargs
    default_config = init_config()
    # print(config["azure_cluster"])
    config_file = os.path.join(dirpath, "config.yaml")
    if os.path.exists(config_file):
        with open(config_file) as cf:
            config = yaml.safe_load(cf)
    mergeDict(config, default_config, False)
    # print(config["azure_cluster"])
    run_command(command, config, args, nargs)
