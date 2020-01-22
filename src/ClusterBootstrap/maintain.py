#!/usr/bin/python3
import os
import re
import sys
import utils
import yaml
import argparse
import textwrap
import random
sys.path.append("../utils")
from ConfigUtils import *
from params import default_config_parameters
from cloud_init_deploy import load_node_list_by_role_from_config

def connect_to_machine(config, args):
    if args.nargs[0] in config['allroles']:
        target_role = args.nargs[0]
        index = int(args.nargs[1])
        nodes, _ = load_node_list_by_role_from_config(config, [target_role])
        node = nodes[index]
    else:
        node = args.nargs[0]
        assert node in config["machines"]
    utils.SSH_connect(config["ssh_cert"], config["machines"][node]
                      ["admin_username"], config["machines"][node]["fqdns"])


def run_kubectl(config, args, commands):
    one_command = " ".join(commands)
    nodes, _ = load_node_list_by_role_from_config(config, ["infra"])
    master_node = random.choice(nodes)
    kube_command = "./deploy/bin/kubectl --server=https://{}:{} --certificate-authority={} --client-key={} --client-certificate={} {}".format(
        config["machines"][master_node]["fqdns"], config["k8sAPIport"], "./deploy/ssl/ca/ca.pem", "./deploy/ssl/kubelet/apiserver-key.pem", "./deploy/ssl/kubelet/apiserver.pem", one_command)
    os.system(kube_command)


def run_script(node, ssh_cert, adm_usr, nargs, sudo=False, noSupressWarning=True):
    if ".py" in nargs[0]:
        if sudo:
            fullcmd = "sudo /opt/bin/python"
        else:
            fullcmd = "/opt/bin/python"
    else:
        if sudo:
            fullcmd = "sudo bash"
        else:
            fullcmd = "bash"
    len_args = len(nargs)
    for i in range(len_args):
        if i == 0:
            fullcmd += " " + os.path.basename(nargs[i])
        else:
            fullcmd += " " + nargs[i]
    srcdir = os.path.dirname(nargs[0])
    utils.SSH_exec_cmd_with_directory(
        ssh_cert, adm_usr, node, srcdir, fullcmd, noSupressWarning)


def run_script_wrapper(arg_tuple):
    node, ssh_cert, adm_usr, nargs, sudo, noSupressWarning = arg_tuple
    run_script(node, ssh_cert, adm_usr, nargs, sudo, noSupressWarning)


def copy2_wrapper(arg_tuple):
    node, ssh_cert, adm_usr, nargs, sudo, noSupressWarning = arg_tuple
    source, target = nargs[0], nargs[1]
    if sudo:
        utils.sudo_scp(ssh_cert, source, target, adm_usr,
                       node, verbose=noSupressWarning)
    else:
        utils.scp(ssh_cert, source, target, adm_usr,
                  node, verbose=noSupressWarning)


def execute_in_in_parallel(config, nodes, nargs, func, sudo=False, noSupressWarning=True):
    args_list = [(config["machines"][node]["fqdns"], config["ssh_cert"],
                  config["admin_username"], nargs, sudo, noSupressWarning) for node in nodes]
    from multiprocessing import Pool
    pool = Pool(processes=len(nodes))
    pool.map(func, args_list)
    pool.close()


def get_multiple_machines(config, args):
    valid_roles = set(config['allroles']) & set(args.roles_or_machine)
    valid_machine_names = set(config['machines']) & set(args.roles_or_machine)
    invalid_rom = set(args.roles_or_machine) - \
        valid_roles - valid_machine_names
    if invalid_rom:
        print("Warning: invalid roles/machine names detected, the following names \\\
            are neither valid role names nor machines in our cluster: " + ",".join(list(invalid_rom)))
    nodes, _ = load_node_list_by_role_from_config(config, list(valid_roles))
    return nodes + list(valid_machine_names)


def run_scripts_on_nodes(config, args):
    nodes = get_multiple_machines(config, args)
    execute_in_in_parallel(config, nodes, args.nargs, run_script_wrapper,
                           sudo=args.sudo, noSupressWarning=args.verbose)


def copy_2_nodes(config, args):
    nodes = get_multiple_machines(config, args)
    execute_in_in_parallel(config, nodes, args.nargs, copy2_wrapper,
                           sudo=args.sudo, noSupressWarning=args.verbose)


def run_command(args, command):
    config = init_config(default_config_parameters)
    config = add_configs_in_order(args.config, config)
    config["ssh_cert"] = config.get("ssh_cert", "./deploy/sshkey/id_rsa")
    if command == "connect":
        connect_to_machine(config, args)
    if command == "kubectl":
        run_kubectl(config, args, args.nargs[0:])
    if command == "runscript":
        run_scripts_on_nodes(config, args)
    if command == "copy2":
        copy_2_nodes(config, args)


if __name__ == '__main__':
    # the program always run at the current directory.
    # ssh -q -o "StrictHostKeyChecking no" -o "UserKnownHostsFile=/dev/null" -i deploy/sshkey/id_rsa core@
    dirpath = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
    os.chdir(dirpath)
    parser = argparse.ArgumentParser(prog='maintain.py',
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=textwrap.dedent('''
        Maintain the status of the cluster.

        Prerequest:
        * Have the accumulated config file ready.

        Command:
            connect  connect to a machine in the deployed cluster
    '''))
    parser.add_argument('-cnf', '--config', action='append', default=[], help='Specify the config files you want to load, later ones \
        would overwrite former ones, e.g., -cnf config.yaml -cnf az_complementary.yaml')
    parser.add_argument('-i', '--in', action='append',
                        default=[], help='Files to take as input')
    parser.add_argument('-o', '--out', help='File to dump to as output')
    parser.add_argument("-v", "--verbose",
                        help="verbose print", action="store_true")
    parser.add_argument('-r', '--roles_or_machine', action='append', default=[], help='Specify the roles of machines that you want to copy file \
        to or execute command on')
    parser.add_argument("-s", "--sudo", action="store_true",
                        help='Execute scripts in sudo')
    parser.add_argument("command",
                        help="See above for the list of valid command")
    parser.add_argument('nargs', nargs=argparse.REMAINDER,
                        help="Additional command argument")
    args = parser.parse_args()
    command = args.command
    nargs = args.nargs

    run_command(args, command)
