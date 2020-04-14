#!/usr/bin/python3

import os
import re
import sys
import time
import json
import utils
import yaml
import argparse
import textwrap
import random
from mysql import connector
cwd = os.path.dirname(__file__)
os.chdir(cwd)

sys.path.append("../utils")

from ConfigUtils import *
from constants import FILE_MAP_PATH, ENV_CNF_YAML, STATUS_YAML

from params import default_config_parameters
from cloud_init_deploy import load_node_list_by_role_from_config
from cloud_init_deploy import update_service_path
from cloud_init_deploy import get_kubectl_binary
from cloud_init_deploy import load_config as load_deploy_config
from cloud_init_deploy import render_restfulapi, render_dashboard, render_storagemanager, render_repairmanager
from cloud_init_deploy import check_buildable_images, push_docker_images


def load_config_4_ctl(args, command):
    # if we need to load all config
    if command in ["svc", "render_template", "download", "docker", "db"]:
        args.config = [ENV_CNF_YAML, STATUS_YAML] if not args.config else args.config
        config = load_deploy_config(args)
    else:
        if not args.config and command != "restorefromdir":
            args.config = [STATUS_YAML]
        config = init_config(default_config_parameters)
        config = add_configs_in_order(args.config, config)
        config["ssh_cert"] = config.get("ssh_cert", "./deploy/sshkey/id_rsa")
    return config


def connect_to_machine(config, args):
    if args.nargs[0] in config['allroles']:
        target_role = args.nargs[0]
        index = int(args.nargs[1]) if len(args.nargs) > 1 else 0
        nodes, _ = load_node_list_by_role_from_config(config, [target_role])
        node = nodes[index]
    else:
        node = args.nargs[0]
        assert node in config["machines"]
    utils.SSH_connect(config["ssh_cert"], config["machines"][node]
                      ["admin_username"], config["machines"][node]["fqdns"])


def run_kubectl(config, args, commands, need_output=False, dump_to_file=''):
    if not os.path.exists("./deploy/bin/kubectl"):
        print("please make sure ./deploy/bin/kubectl exists. One way is to use ./ctl.py download")
        exit(-1)
    one_command = " ".join(commands)
    nodes, _ = load_node_list_by_role_from_config(config, ["infra"], False)
    master_node = random.choice(nodes)
    kube_command = "./deploy/bin/kubectl --server=https://{}:{} --certificate-authority={} --client-key={} --client-certificate={} {}".format(
        config["machines"][master_node]["fqdns"], config["k8sAPIport"], "./deploy/ssl/ca/ca.pem", "./deploy/ssl/kubelet/apiserver-key.pem", "./deploy/ssl/kubelet/apiserver.pem", one_command)
    if need_output:
        # we may want to dump command to another file instead of args.output, when we don't want to mix k8s commands with others
        output = utils.execute_or_dump_locally(kube_command, args.verbose, args.dryrun, dump_to_file)
        if not args.verbose:
            print(output)
        return output
    else:
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


def run_cmd(node, ssh_cert, adm_usr, nargs, sudo=False, noSupressWarning=True):
    fullcmd = " ".join(nargs)
    utils.SSH_exec_cmd(
        ssh_cert, adm_usr, node, fullcmd, noSupressWarning)


def run_script_wrapper(arg_tuple):
    node, ssh_cert, adm_usr, nargs, sudo, noSupressWarning = arg_tuple
    run_script(node, ssh_cert, adm_usr, nargs, sudo, noSupressWarning)


def run_cmd_wrapper(arg_tuple):
    node, ssh_cert, adm_usr, nargs, sudo, noSupressWarning = arg_tuple
    run_cmd(node, ssh_cert, adm_usr, nargs, sudo, noSupressWarning)


def copy2_wrapper(arg_tuple):
    node, ssh_cert, adm_usr, nargs, sudo, noSupressWarning = arg_tuple
    source, target = nargs[0], nargs[1]
    if sudo:
        utils.sudo_scp(ssh_cert, source, target, adm_usr,
                       node, verbose=noSupressWarning)
    else:
        utils.scp(ssh_cert, source, target, adm_usr,
                  node, verbose=noSupressWarning)


def execute_in_parallel(config, nodes, nargs, sudo, func, noSupressWarning=True):
    args_list = [(config["machines"][node]["fqdns"], config["ssh_cert"],
                  config["admin_username"], nargs, sudo, noSupressWarning) for node in nodes]
    utils.multiprocess_exec(func, args_list, len(nodes))


def get_multiple_machines(config, args):
    valid_roles = set(config['allroles']) & set(args.roles_or_machine)
    valid_machine_names = set(config['machines']) & set(args.roles_or_machine)
    invalid_rom = set(args.roles_or_machine) - \
        valid_roles - valid_machine_names
    if invalid_rom:
        print("Warning: invalid roles/machine names detected, the following names \\\
            are neither valid role names nor machines in our cluster: " + ",".join(list(invalid_rom)))
    nodes, _ = load_node_list_by_role_from_config(config, list(valid_roles), False)
    return nodes + list(valid_machine_names)


def parallel_action_by_role(config, args, func):
    nodes = get_multiple_machines(config, args)
    execute_in_parallel(config, nodes, args.nargs, args.sudo,
                        func, noSupressWarning=args.verbose)


def verify_all_nodes_ready(config, args):
    """
    return unready nodes, used for contiguous integration(CI)
    """
    nodes_info_raw = run_kubectl(config, args, ["get nodes"], True)
    ready_machines = set([entry.split("Ready")[0].strip()
                          for entry in nodes_info_raw.split('\n')[1:]])
    expected_nodes = set(config["machines"].keys())
    nodes_expected_but_not_ready = expected_nodes - ready_machines
    if len(list(nodes_expected_but_not_ready)) > 0:
        print("following nodes not ready:\n{}".format(
            ','.join(list(nodes_expected_but_not_ready))))
        exit(1)


def change_kube_service(config, args, operation, service_list):
    assert operation in [
        "start", "stop"] and "you can only start or stop a service"
    kubectl_action = "create" if operation == "start" else "delete"
    if operation == "start": 
        render_services(config, service_list)
        remote_config_update(config, args)
    elif not os.path.exists("./deploy/services"):
        utils.render_template_directory("./services/", "./deploy/services/", config)
    service2path = update_service_path()
    for service_name in service_list:
        fname = service2path[service_name]
        dirname = os.path.dirname(fname)
        if os.path.exists(os.path.join(dirname, "launch_order")) and "/" not in service_name:
            with open(os.path.join(dirname, "launch_order"), 'r') as f:
                allservices = f.readlines()
                if operation == "stop":
                    allservices = reversed(allservices)
                for filename in allservices:
                    # If this line is a sleep tag (e.g. SLEEP 10), sleep for given seconds to wait for the previous service to start.
                    if filename.startswith("SLEEP"):
                        if operation == "start":
                            time.sleep(int(filename.split(" ")[1]))
                        else:
                            continue
                    filename = filename.strip('\n')
                    run_kubectl(config, args, [
                                "{} -f {}".format(kubectl_action, os.path.join(dirname, filename))])
        else:
            run_kubectl(config, args, [
                        "{} -f {}".format(kubectl_action, fname)])


def render_services(config, service_list):
    '''render services, ./ctl.py svc render <service name, e.g. monitor>'''
    for svc in service_list:
        if not os.path.exists("./services/{}".format(svc)):
            print("Warning: folder of service {} not found under ./services directory")
            continue
        utils.render_template_directory(
            "./services/{}".format(svc), "./deploy/services/{}".format(svc), config)


def remote_config_update(config, args, check_module=False):
    '''
    client end(infra/NFS node) config file update
    ./ctl.py -s svc configupdate restfulapi
    ./ctl.py [-r storage_machine1 [-r storage_machine2]] -s svc configupdate storage_manager
    by default sudo
    '''
    if check_module:
        assert set(args.nargs[1:]) - set(["restfulapi", "storagemanager", "repairmanager", "dashboard"]) == set(), "not supported"
    # need to get node list for this subcommand of svc, so load status.yaml
    if not os.path.exists(FILE_MAP_PATH):
        utils.render_template("template/cloud-config/file_map.yaml", FILE_MAP_PATH, config)
    with open(FILE_MAP_PATH) as f:
        file_map = yaml.load(f)
    for module in args.nargs[1:]:
        if module in ["restfulapi", "dashboard", "repairmanager"]:
            render_func = eval("render_{}".format(module))
            render_func(config)
            infra_nodes, _ = load_node_list_by_role_from_config(config, ["infra"], False)
            for file_pair in file_map[module]:
                src_dst_list = [file_pair["src"], file_pair["dst"]]
                execute_in_parallel(config, infra_nodes, src_dst_list,
                                    True, copy2_wrapper, noSupressWarning=args.verbose)
        elif module == "storagemanager":
            nfs_nodes, _ = load_node_list_by_role_from_config(config, ["nfs"], False)
            for node in nfs_nodes:
                config["storage_manager"] = config["machines"][node]["storage_manager"]
                render_storagemanager(config, node)
                src_dst_list = ["./deploy/StorageManager/{}_storage_manager.yaml".format(
                    node), "/etc/StorageManager/config.yaml"]
                args_list = (config["machines"][node]["fqdns"], config["ssh_cert"],
                             config["admin_username"], src_dst_list, True, args.verbose)
                copy2_wrapper(args_list)


def render_template_or_dir(config, args):
    nargs = args.nargs
    # no destination, then mirror one in ./deploy folder
    src = nargs[0]
    if len(nargs) == 1:
        dst = os.path.join("deploy", src.split("template/")[1])
    else:
        dst = nargs[1]
    if os.path.isdir(src):
        utils.render_template_directory(src, dst, config)
    else:
        utils.render_template(src, dst, config)


def maintain_db(config, args):
    """
    push/pull a table to/from DB
    """
    subcommand = args.nargs[0]
    assert subcommand in ["pull", "push", "connect"], "invalid action."
    host = config["mysql_node"]
    user = config["mysql_username"]
    password = config["mysql_password"]
    if subcommand == "connect":
        os.system("mysql -h {} -u {} -p{}".format(host, user, password))
    else:
        database = "DLWSCluster-{}".format(config["clusterId"])
        table_name = args.nargs[1]
        assert table_name in ["vc", "acl"], "invalid table."
        
        if args.verbose:
            print("connecting to {}@{}, DB {}".format(user, host, database))
        conn = connector.connect(user=user, password=password,
               host=host, database=database)
        if subcommand == "pull":
            sql = "SELECT * from {}".format(table_name)
            cursor = conn.cursor()
            cursor.execute(sql)
            col_names = [col[0] for col in cursor.description]
            serialized_rows = []
            rows = cursor.fetchall()
            for row in rows:
                serialized_row = {}
                for i, v in enumerate(row):
                    try:
                        serialized_row[col_names[i]] = json.loads(v)
                    # JSONDecodeError
                    except:
                        serialized_row[col_names[i]] = v
                serialized_rows.append(serialized_row)
            table_config = {"col_names": col_names, "rows": serialized_rows}
            dump2 = args.output if args.output else "{}.yaml".format(table_name)
            with open(dump2, "w") as wf:
                yaml.safe_dump(table_config, wf)
        elif subcommand == "push":
            sql = "DELETE from {}".format(table_name)
            cursor = conn.cursor()
            cursor.execute(sql)
            with open("{}.yaml".format(table_name)) as f:
                table_config = yaml.safe_load(f)
            col_names = table_config["col_names"]
            cols_2_ignore = table_config.get("columns_to_ignore", ["time"])
            cols_filtered = [col for col in col_names if col not in cols_2_ignore]
            cols_str = ", ".join(cols_filtered)
            for row in table_config["rows"]:
                vals = ", ".join(["'{}'".format(json.dumps(row[col])) for col in cols_filtered])
                sql = "INSERT INTO `{}` ({}) VALUES ({})".format(table_name, cols_str, vals)
                if args.verbose:
                    print(sql)
                cursor.execute(sql)
            conn.commit()

        cursor.close()


def run_command(args, command):
    config = load_config_4_ctl(args, command)
    if command == "restorefromdir":
        utils.restore_keys_from_dir(args.nargs)
    elif command == "connect":
        connect_to_machine(config, args)
    elif command == "kubectl":
        run_kubectl(config, args, args.nargs[0:])
    elif command == "runscript":
        parallel_action_by_role(config, args, run_script_wrapper)
    elif command == "runcmd":
        parallel_action_by_role(config, args, run_cmd_wrapper)
    elif command == "copy2":
        parallel_action_by_role(config, args, copy2_wrapper)
    elif command == "backuptodir":
        utils.backup_keys_to_dir(args.nargs)
    elif command == "restorefromdir":
        utils.restore_keys_from_dir(args.nargs)
    elif command == "verifyallnodes":
        verify_all_nodes_ready(config, args)
    elif command == "svc":
        assert len(
            args.nargs) > 1 and "at least 1 action and 1 kubernetes service name should be provided"
        if args.nargs[0] == "start":
            change_kube_service(config, args, "start", args.nargs[1:])
        elif args.nargs[0] == "stop":
            change_kube_service(config, args, "stop", args.nargs[1:])
        elif args.nargs[0] == "render":
            render_services(config, args.nargs[1:])
        elif args.nargs[0] == "configupdate":
            remote_config_update(config, args, True)
    elif command == "render_template":
        render_template_or_dir(config, args)
    elif command == "download":
        if not os.path.exists('deploy/bin/kubectl') or args.force:
            get_kubectl_binary(config)
    elif command == "docker":
        nargs = args.nargs
        if nargs[0] == "push":
            check_buildable_images(args.nargs[1], config)
            push_docker_images(args, config)
    elif command == "db":
        maintain_db(config, args)
    else:
        print("invalid command, please read the doc")


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
        would overwrite former ones, e.g., -cnf config.yaml -cnf status.yaml')
    parser.add_argument('-i', '--in', action='append',
                        default=[], help='Files to take as input')
    parser.add_argument('-o', '--output', default='', help='File to dump to as output')
    parser.add_argument("-v", "--verbose",
                        help="verbose print", action="store_true")
    parser.add_argument('-r', '--roles_or_machine', action='append', default=[], help='Specify the roles of machines that you want to copy file \
        to or execute command on')
    parser.add_argument("-s", "--sudo", action="store_true",
                        help='Execute scripts in sudo')
    parser.add_argument("-f", "--force", action="store_true",
                        help='Force execution')
    parser.add_argument("--nocache",
                        help="Build docker without cache",
                        action="store_true")
    parser.add_argument("command",
                        help="See above for the list of valid command")
    parser.add_argument('nargs', nargs=argparse.REMAINDER,
                        help="Additional command argument")
    args = parser.parse_args()
    command = args.command
    nargs = args.nargs
    run_command(args, command)
