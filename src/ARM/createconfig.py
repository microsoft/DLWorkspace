#!/usr/bin/python
import argparse
import yaml
import os

def add_dashboard():
    server_name = "{0}-infra01.{1}.cloudapp.azure.com".format(
        config["cluster_name"], config["azure_cluster"][config["cluster_name"]]["azure_location"])
    config["Dashboards"] = {
        "grafana" : {"servers" : server_name},
        "influxDB" : {"servers" : server_name}
    }
    config["cloud_influxdb_node"] = server_name

def add_deploy(users):
    config["DeployAuthentications"] = ["Corp"]
    config["UserGroups"] = {
        "DLWSAdmins" : {
            "Allowed" : users,
            "gid" : "20000",
            "uid" : "{0}-{1}".format(20000, 20000+len(users))
        },
        "DLWSRegister" : {
            "Allowed" : ["""@gmail.com""", """@live.com""", """@hotmail.com""", """@microsoft.com"""],
            "gid" : "20001",
            "uid" : "20001-29999"
        }
    }
    config["WebUIadminGroups"] = ["DLWSAdmins"]
    config["WebUIauthorizedGroups"] = ["DLWSAdmins"]
    config["WebUIregisterGroups"] = ["DLWSRegister"]
    config["WinbindServers"] = []
    if args.openid_name == "Google" or args.openid_name == "MSFT":
        config["Authentications"] = {
            args.openid_name :  {
                "DisplayName" : args.openid_name,
                "Tenant" : args.openid_tenant,
                "ClientId" : args.openid_clientid,
                "ClientSecret" : args.openid_clientsecret
            }
        }
        if args.openid_name == "Google":
            config["Authentications"][args.openid_name].update({
                "AuthorityFormat" : "https://accounts.google.com",
                "Scope" : "openid email",
                "Domains" : ["gmail.com"]
            })
        if args.openid_name == "MSFT":
            config["Authentications"][args.openid_name].update({
                "AuthorityFormat" : "https://login.microsoftonline.com",
                "Domains" : [ "live.com", "hotmail.com", "outlook.com" ]
            })
        config["DeployAuthentications"].append(args.openid_name)

def add_azure_cluster(username, cluster_name, cluster_location, worker_vm_size, infra_vm_size, worker_node_num, infra_node_num):
    config["cluster_name"] = cluster_name
    config["azure_cluster"] = {
        config["cluster_name"] : {
            "azure_location" : cluster_location,
            "worker_vm_size" : worker_vm_size,
            "infra_vm_size" : infra_vm_size,
            "last_scaled_node_num" : 0,
            "worker_node_num" : int(worker_node_num),
            "infra_node_num" : int(infra_node_num)
        }
    }

def add_cloud_config():
    config["cloud_config"] = {
        "dev_network" : {
            "source_addresses_prefixes" : ["73.109.29.0/24", "167.220.0.0/16", "131.107.0.0/16", "52.151.11.0/24", "52.226.68.0/24"]
        }
    }

def add_misc():
    config["datasource"] = "MySQL"
    config["mysql_password"] = """M$ft2018"""
    config["webuiport"] = 3080

def copy_ssh_key(username, password, machine):
    cmd = """cat /home/%s/dlworkspace/src/ClusterBootstrap/deploy/sshkey/id_rsa.pub | /usr/bin/sshpass -p '%s' ssh -o "StrictHostKeyChecking=no" -o "UserKnownHostsFile=/dev/null" %s@%s "mkdir -p /home/%s/.ssh && cat >> /home/%s/.ssh/authorized_keys" """ % (username, password, username, machine, username, username)
    print cmd
    os.system(cmd)

if __name__ == '__main__':
    config = {} # empty config
    parser = argparse.ArgumentParser('createconfig.py')
    parser.add_argument("command",
			help="genconfig or sshkey")
    parser.add_argument("--outfile",
                        help="Configuration file output",
                        action="store")
    parser.add_argument("--cluster_name",
                        help="Specify a cluster name",
                        action="store")
    parser.add_argument("--cluster_location",
                        help="Cluster location",
                        action="store")
    parser.add_argument("--worker_vm_size")
    parser.add_argument("--infra_vm_size")
    parser.add_argument("--worker_node_num")
    parser.add_argument("--infra_node_num")
    parser.add_argument("--admin_username")
    parser.add_argument("--password")
    parser.add_argument("--users") # comma separated list
    parser.add_argument("--openid_name")
    parser.add_argument("--openid_tenant")
    parser.add_argument("--openid_clientid")
    parser.add_argument("--openid_clientsecret")

    args = parser.parse_args()

    if args.command == "genconfig":
        add_azure_cluster(args.admin_username, args.cluster_name, args.cluster_location, args.worker_vm_size, args.infra_vm_size, args.worker_node_num, args.infra_node_num)
        add_cloud_config()
        add_dashboard()
        add_misc()
        add_deploy([item.strip() for item in args.users.split(',')])
      
        with open(args.outfile, 'w') as f:
            yaml.dump(config, f)
    elif args.command == "sshkey":
        for i in range(0, int(args.infra_node_num)):
            copy_ssh_key(args.admin_username, args.password, "%s-infra%02d" % (args.cluster_name, (i+1)))
        for i in range(0, int(args.worker_node_num)):
            copy_ssh_key(args.admin_username, args.password, "%s-worker%02d" % (args.cluster_name, (i+1)))
