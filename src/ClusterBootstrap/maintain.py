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
from cloud_init_deploy import load_node_list_by_role_from_config
from params import default_config_parameters
from ConfigUtils import *


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


def run_script(node, args, sudo=False, supressWarning=False):
    if ".py" in args[0]:
        if sudo:
            fullcmd = "sudo /opt/bin/python"
        else:
            fullcmd = "/opt/bin/python"
    else:
        if sudo:
            fullcmd = "sudo bash"
        else:
            fullcmd = "bash"
    nargs = len(args)
    for i in range(nargs):
        if i == 0:
            fullcmd += " " + os.path.basename(args[i])
        else:
            fullcmd += " " + args[i]
    srcdir = os.path.dirname(args[0])
    utils.SSH_exec_cmd_with_directory(
        config["ssh_cert"], config["admin_username"], node, srcdir, fullcmd, supressWarning)


def run_script_wrapper(arg_tuple):
    node, args, sudo, supressWarning = arg_tuple
    run_script(node, args, sudo, supressWarning)


def run_script_on_all_in_parallel(nodes, args, sudo=False, supressWarning=False):
    args_list = [(node, args, sudo, supressWarning) for node in nodes]
    from multiprocessing import Pool
    pool = Pool(processes=len(nodes))
    pool.map(run_script_wrapper, args_list)
    pool.close()


def runonroles(config, args):
    invalid_roles = set(config['allroles']) - set(args.roles)
    if invalid_roles:
        print("Warning: invalid roles detected: " + ",".join(list(invalid_roles)))
    nodes, _ = load_node_list_by_role_from_config(config, list(set(args.roles) & set(config['allroles'])))
    pssh_cmd = 'parallel-ssh {} -t 0 -p {} -H {} -x "-oStrictHostKeyChecking=no -oUserKnownHostsFile=/dev/null -i deploy/sshkey/id_rsa" -l core {}'.format(
        log_option, len(nodes), ' '.join(nodes), args.nargs[0])
    os.system(pssh_cmd)


def run_command(args, command):
    config = init_config(default_config_parameters)
    config = add_configs_in_order(args.config, config)
    config["ssh_cert"] = config.get("ssh_cert", "./deploy/sshkey/id_rsa")
    if command == "connect":
        connect_to_machine(config, args)
    if command == "kubectl":
        run_kubectl(config, args, args.nargs[0:])
    if command == "runonroles":
        pass
    if command == "copy2roles":
        pass

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
    parser.add_argument('-r', '--roles', action='append', default=[], help='Specify the roles of machines that you want to copy file \
        to or execute command on')
    parser.add_argument("-s", "--sudo", action="store_true", help='Execute scripts in sudo')
    parser.add_argument("command",
                        help="See above for the list of valid command")
    parser.add_argument('nargs', nargs=argparse.REMAINDER,
                        help="Additional command argument")
    args = parser.parse_args()
    command = args.command
    nargs = args.nargs

    run_command(args, command)
