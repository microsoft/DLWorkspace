#!/usr/bin/python
# Tools to build ACS cluster

import sys
import os
import subprocess
import yaml
import re
import numbers

sys.path.append("../utils")
import utils

import az_tools

# AZ ACS commands
def az_cmd(cmd):
    if verbose:
        print "az "+cmd
    output = subprocess.check_output("az "+cmd, shell=True)
    return yaml.load(output)

def az_sys(cmd):
    if verbose:
        print "az "+cmd
    os.system("az "+cmd)

def az_tryuntil(cmd, stopFn, waitPeriod=5):
    return utils.tryuntil(lambda : az_sys(cmd), stopFn, lambda : (), waitPeriod)

def acs_get_id(elem):
    elemFullName = elem["id"]
    reMatch = re.match('(.*)/(.*)', elemFullName)
    return reMatch.group(2)

def key_extract(dic, keys):
    return dict((k, dic[k]) for k in keys if k in dic)

def inList(elem, list):
    i = 0
    for l in list:
        if l == elem:
            return True, i
        i += 1
    return False, -1

# Create SQL database
def az_create_sql_server():
    # escape the password in case it has characters such as "$"
    pwd = utils.shellquote(config["sqlserver-password"])
    cmd = "sql server create"
    cmd += " --resource-group=%s" % config["resource_group"]
    cmd += " --location=%s" % config["cluster_location"]
    cmd += " --name=%s" % config["azure-sqlservername"]
    cmd += " --admin-user=%s" % config["sqlserver-username"]
    cmd += " --admin-password=%s" % pwd
    az_sys(cmd)
    # now open firewall
    cmd = "sql server firewall-rule create"
    cmd += " --resource-group=%s" % config["resource_group"]
    cmd += " --server=%s" % config["azure-sqlservername"]
    # first open all IPs
    cmd2 = cmd + " --name=All --start-ip-address=0.0.0.0 --end-ip-address=255.255.255.255"
    az_sys(cmd2)
    # now open Azure
    cmd2 = cmd + " --name=Azure --start-ip-address=0.0.0.0 --end-ip-address=0.0.0.0"
    az_sys(cmd2)

def az_create_sql_database(dbname):
    cmd = "sql db create"
    cmd += " --resource-group=%s" % config["resource_group"]
    cmd += " --server=%s" % config["azure-sqlservername"]
    cmd += " --name=%s" % dbname
    az_sys(cmd)

def az_create_sql():
    az_create_sql_server()
    az_create_sql_database(config["sqlserver-database"])

def az_grp_exist(grpname):
    resgrp = az_cmd("group show --name=%s" % grpname)
    return not resgrp is None

# Overwrite resource group with location where machines are located
# If no machines are found, that may be because they are not created, so leave it as it is
def acs_set_resource_grp(exitIfNotFound):
    if not "acs_resource_group" in config:
        config["acs_resource_group"] = config["resource_group"] # where container service resides
    if (not "resource_group_set" in config) or (not config["resource_group_set"]):
        bFoundMachines = False
        if (az_grp_exist(config["resource_group"])):
            machines = az_cmd("vm list --resource-group=%s" % config["resource_group"])
            if (len(machines) > 0):
                bFoundMachines = True
            if not bFoundMachines:
                # try child resource group
                tryGroup = "%s_%s_%s" % (config["resource_group"], config["cluster_name"], config["cluster_location"])
                print "Grp %s has no matchines trying %s" % (config["resource_group"], tryGroup)
                if (az_grp_exist(tryGroup)):
                    machines = az_cmd("vm list --resource-group=%s" % tryGroup)
                    if (len(machines) > 0):
                        # overwrite with group where machines are located
                        config["resource_group"] = tryGroup
                        bFoundMachines = True
        if bFoundMachines:
            config["resource_group_set"] = True
        if not bFoundMachines and exitIfNotFound:
            print "No machines found -- quitting"
            exit()
        print "Resource group = %s" % config["resource_group"]

# Get names of kubernetes nodes (machine names)
def acs_get_kube_nodes():
    if "acs_nodes" not in config:
        binary = os.path.abspath('./deploy/bin/kubectl')
        kubeconfig = os.path.abspath('./deploy/'+config["acskubeconfig"])
        if (os.path.exists(binary)):
            cmd = binary + ' -o=json --kubeconfig='+kubeconfig+' get nodes'
            nodeInfo = utils.subproc_runonce(cmd)
            try:
                nodes = yaml.load(nodeInfo)
                nodeNames = []
                for n in nodes["items"]:
                    nodeNames.append(n["metadata"]["name"])
                #print "Nodes: {0}\n NodeNames: {1}".format(nodes, nodeNames)
                #exit()
                config["acs_nodes"] = nodeNames
                return nodeNames
            except Exception as e:
                return []
        else:
            return []
    else:
        return config["acs_nodes"]

# wait for nodes to be up
def acs_wait_for_kube():
    numNodes = 0
    expectedNodes = config["worker_node_num"] + config["master_node_num"]
    while numNodes < expectedNodes:
        binary = os.path.abspath('./deploy/bin/kubectl')
        kubeconfig = os.path.abspath('./deploy/'+config["acskubeconfig"])
        cmd = binary + ' -o=json --kubeconfig='+kubeconfig+' get nodes'
        nodeInfo = utils.subproc_runonce(cmd)
        nodes = yaml.load(nodeInfo)
        numNodes = len(nodes["items"])
        if numNodes < expectedNodes:
            print "Waiting for {0} kubernetes nodes to start up, currently have only {1} nodes".format(expectedNodes, numNodes)
            time.sleep(5)

# divide nodes into master / agent
def acs_set_nodes_info():
    if "acs_master_nodes" not in config or "acs_agent_nodes" not in config:
        allnodes = acs_get_kube_nodes()
        if len(allnodes) > 0:
            config['acs_master_nodes'] = []
            config['acs_agent_nodes'] = []
            for n in allnodes:
                match = re.match('k8s-master.*', n)
                if match is not None:
                    config['acs_master_nodes'].append(n)
                match = re.match('k8s-agent.*', n)
                if match is not None:
                    config['acs_agent_nodes'].append(n)

# Get full network info on node
def acs_get_ip_info_full(node):
    nics = az_cmd("vm show --name="+node+" --resource-group="+config["resource_group"])
    if nics is None or "networkProfile" not in nics:
        return {}
    ipInfo = nics["networkProfile"]["networkInterfaces"]
    nicIndex = 0
    for nic in ipInfo:
        nicName = acs_get_id(nic)
        ipconfigs = az_cmd("network nic show --resource-group="+config["resource_group"]+" --name="+nicName)
        ipInfo[nicIndex]["nicName"] = nicName
        ipInfo[nicIndex]["ipConfigs"] = ipconfigs["ipConfigurations"]
        ipConfigIndex = 0
        for ipConfig in ipInfo[nicIndex]["ipConfigs"]:
            ipConfigName = acs_get_id(ipConfig)
            ipInfo[nicIndex]["ipConfigs"][ipConfigIndex]["ipConfigName"] = ipConfigName
            configInfo = az_cmd("network nic ip-config show --resource-group="+config["resource_group"]+
                                " --nic-name="+nicName+" --name="+ipConfigName)
            ipInfo[nicIndex]["ipConfigs"][ipConfigIndex]["privateIp"] = configInfo["privateIpAddress"]
            ipInfo[nicIndex]["ipConfigs"][ipConfigIndex]["publicIpInfo"] = configInfo["publicIpAddress"]
            ipConfigIndex += 1
        nicIndex += 1
    return ipInfo

def acs_get_node_info(node):
    if "acs_node_info" not in config:
        config["acs_node_info"] = {}
    if node not in config["acs_node_info"]:
        config["acs_node_info"][node] = {}
    return config["acs_node_info"][node]

def acs_set_desired_dns(node, nodeInfo=None):
    if nodeInfo is None:
        nodeInfo = acs_get_node_info(node)
    if "desiredDns" not in nodeInfo:
        acs_set_nodes_info()
        if "acs_nodes" in config:
            if "acs_node_from_dns" not in config:
                config["acs_node_from_dns"] = {}
            isInList, index = inList(node, config["acs_master_nodes"])
            if isInList and index==0:
                nodeInfo["desiredDns"] = config["master_dns_name"]
            else:
                nodeInfo["desiredDns"] = node
            config["acs_node_from_dns"][nodeInfo["desiredDns"]] = node

def acs_set_node_from_dns(dnsname, checkForNode=True):
    if "acs_node_from_dns" not in config or 0==len(config["acs_node_from_dns"]) or (checkForNode and (dnsname not in config["acs_node_from_dns"])):
        allnodes = acs_get_kube_nodes()
        for n in allnodes:
            acs_set_desired_dns(n)

def acs_set_node_ip_info(node, needPrivateIP):
    nodeInfo = acs_get_node_info(node)
    if "publicIpName" not in nodeInfo or "publicIp" not in nodeInfo or "dnsName" not in nodeInfo or "fqdn" not in nodeInfo:
        nodeInfo["publicIpName"] = node + "-public-ip-0"
        ipInfo = az_cmd("network public-ip show --resource-group="+config["resource_group"]+" --name="+nodeInfo["publicIpName"])
        if ipInfo is not None and "ipAddress" in ipInfo:
            nodeInfo["publicIp"] = ipInfo["ipAddress"]
        if ipInfo is not None and "dnsSettings" in ipInfo and ipInfo["dnsSettings"] is not None:
            nodeInfo["dnsName"] = ipInfo["dnsSettings"]["domainNameLabel"]
            nodeInfo["fqdn"] = ipInfo["dnsSettings"]["fqdn"]
    if needPrivateIP and "privateIp" not in nodeInfo:
        fullInfo = acs_get_ip_info_full(node)
        if fullInfo is not None:
            nodeInfo["privateIp"] = fullInfo[0]["ipConfigs"][0]["privateIp"]
    acs_set_desired_dns(node, nodeInfo)
    return nodeInfo

def acs_set_desired_dns_nodes():
    acs_set_node_from_dns("", False)

# create public ip for node
def acs_create_public_ip(node):
    nodeInfo = acs_set_node_ip_info(node, False)
    publicIpName = config["acs_node_info"][node]["publicIpName"]
    if "publicIp" not in nodeInfo:
        fullInfo = acs_get_ip_info_full(node)
        # Create IP
        print "Creating public-IP: "+publicIpName
        cmd = "network public-ip create --allocation-method=Dynamic"
        cmd += " --resource-group=%s" % config["resource_group"]
        cmd += " --name=%s" % publicIpName
        cmd += " --location=%s" % config["cluster_location"]
        az_sys(cmd)
        # Add to NIC of machine
        cmd = "network nic ip-config update"
        cmd += " --resource-group=%s" % config["resource_group"]
        cmd += " --nic-name=%s" % fullInfo[0]["nicName"]
        cmd += " --name=%s" % fullInfo[0]["ipConfigs"][0]["ipConfigName"]
        cmd += " --public-ip-address=%s" % publicIpName
        az_sys(cmd)
        # call again to update node info
        acs_set_node_ip_info(node, False)

def acs_create_dns(node):
    nodeInfo = acs_set_node_ip_info(node, False)
    if "dnsName" not in nodeInfo:
        cmd = "network public-ip update"
        cmd += " --resource-group=%s" % config["resource_group"]
        cmd += " --name=%s" % nodeInfo["publicIpName"]
        cmd += " --dns-name=%s" % nodeInfo["desiredDns"]
        az_sys(cmd)
        acs_set_node_ip_info(node, False)

def acs_set_create_node_ip_info(node):
    nodeInfo = acs_set_node_ip_info(node, False)
    acs_create_public_ip(node)
    acs_create_dns(node)

def acs_is_valid_nsg_rule(rule):
    #print "Access: %s D: %s P: %s P: %s" % (rule["access"].lower()=="allow",
    #rule["direction"].lower()=="inbound",rule["sourceAddressPrefix"]=='*',
    #(rule["protocol"].lower()=="tcp" or rule["protocol"]=='*'))
    return (rule["access"].lower()=="allow" and
            rule["direction"].lower()=="inbound" and
            rule["sourceAddressPrefix"]=='*' and
            (rule["protocol"].lower()=="tcp" or rule["protocol"]=='*'))

def acs_add_nsg_rules(ports_to_add):
    nsgs = az_cmd("network nsg list --resource-group={0}".format(config["resource_group"]))
    nsg_name = acs_get_id(nsgs[0])
    cmd = "network nsg show --resource-group="+config["resource_group"]+" --name="+nsg_name
    rulesInfo = az_cmd(cmd)
    rules = rulesInfo["defaultSecurityRules"] + rulesInfo["securityRules"]

    maxThreeDigitRule = 100
    for rule in rules:
        if acs_is_valid_nsg_rule(rule):
            if (rule["priority"] < 1000):
                #print "Priority: %d" % rule["priority"]
                maxThreeDigitRule = max(maxThreeDigitRule, rule["priority"])

    if verbose:
        print "Existing max three digit rule for NSG: %s is %d" % (nsg_name, maxThreeDigitRule)

    for port_rule in ports_to_add:
        port_num = ports_to_add[port_rule]
        createRule = True
        isNum = isinstance(port_num, numbers.Number)
        if (not isNum) and port_num.isdigit():
            port_num = int(port_num)
            isNum = True
        if isNum:
            # check for existing rules
            found_port = None
            for rule in rules:
                if acs_is_valid_nsg_rule(rule):
                    match = re.match('(.*)-(.*)', rule["destinationPortRange"])
                    if (match is None):
                        minPort = int(rule["destinationPortRange"])
                        maxPort = minPort
                    elif (rule["destinationPortRange"] != "*"):
                        minPort = int(match.group(1))
                        maxPort = int(match.group(2))
                    else:
                        minPort = -1
                        maxPort = -1
                    if (minPort <= port_num) and (port_num <= maxPort):
                        found_port = rule["name"]
                        break
            if not (found_port is None):
                print "Rule for %s : %d -- already satisfied by %s" % (port_rule, port_num, found_port)
                createRule = False
        if createRule:
            maxThreeDigitRule = maxThreeDigitRule + 10
            cmd = "network nsg rule create"
            cmd += " --resource-group=%s" % config["resource_group"]
            cmd += " --nsg-name=%s" % nsg_name
            cmd += " --name=%s" % port_rule
            cmd += " --access=Allow"
            if isNum:
                cmd += " --destination-port-range=%d" % port_num
            else:
                cmd += " --destination-port-range=%s" % port_num
            cmd += " --direction=Inbound"
            cmd += " --priority=%d" % maxThreeDigitRule
            az_cmd(cmd)

def acs_get_config(force=False):
    # Install kubectl / get credentials
    if not (os.path.exists('./deploy/bin/kubectl')):
        os.system("mkdir -p ./deploy/bin")
        az_tryuntil("acs kubernetes install-cli --install-location ./deploy/bin/kubectl", lambda : os.path.exists('./deploy/bin/kubectl'))
    if (force):
        os.system("rm ./deploy/%s" % config["acskubeconfig"])
    if not (os.path.exists('./deploy/'+config["acskubeconfig"])):
        cmd = "acs kubernetes get-credentials"
        cmd += " --resource-group=%s" % config["acs_resource_group"]
        cmd += " --name=%s" % config["cluster_name"]
        cmd += " --file=./deploy/%s" % config["acskubeconfig"]
        cmd += " --ssh-key-file=%s" % "./deploy/sshkey/id_rsa"
        az_tryuntil(cmd, lambda : os.path.exists("./deploy/%s" % config["acskubeconfig"]))

def acs_get_storage_key():
    cmd = "storage account keys list"
    cmd += " --account-name=%s" % config["mountpoints"]["rootshare"]["accountname"]
    cmd += " --resource-group=%s" % config["resource_group"]
    keys = az_cmd(cmd)
    return keys[0]["value"]

def acs_create_storage():
    # Create storage account
    cmd = "storage account create"
    cmd += " --name=%s" % config["mountpoints"]["rootshare"]["accountname"]
    cmd += " --resource-group=%s" % config["resource_group"]
    cmd += " --sku=%s" % config["mountpoints"]["rootshare"]["azstoragesku"]
    az_sys(cmd)
    # Create file share
    azureKey = acs_get_storage_key()
    config["mountpoints"]["rootshare"]["accesskey"] = azureKey
    cmd = "storage share create"
    cmd += " --name=%s" % config["mountpoints"]["rootshare"]["filesharename"]
    cmd += " --quota=%s" % config["mountpoints"]["rootshare"]["azfilesharequota"]
    cmd += " --account-name=%s" % config["mountpoints"]["rootshare"]["accountname"]
    cmd += " --account-key=%s" % azureKey
    az_sys(cmd)

def acs_load_azconfig():
    if (os.path.exists(azConfigFile)):
        with open(azConfigFile, "r") as f:
            return yaml.load(f)
    else:
        return None

def acs_write_azconfig(configToWrite):
    with open(azConfigFile, "w") as f:
        yaml.dump(configToWrite, f, default_flow_style=False)

def acs_init_azconfig():
    az_tools.config = az_tools.init_config()
    az_tools.config["isacs"] = True
    az_tools.config["azure_cluster"]["file_share_name"] = "files"
    az_tools.config["azure_cluster"]["cluster_name"] = config["cluster_name"]
    az_tools.config["azure_cluster"]["azure_location"] = config["cluster_location"]
    az_tools.config = az_tools.update_config(az_tools.config, False)
    if not "resource_group" in config:
        config["resource_group"] = az_tools.config["azure_cluster"]["resource_group_name"]

def acs_generate_azconfig():
    acs_init_azconfig()
    acs_set_resource_grp(False)
    az_tools.config["azure_cluster"]["resource_group_name"] = config["resource_group"]
    azConfig = az_tools.gen_cluster_config("", False)
    # add resource group names
    azConfig["resource_group"] = config["resource_group"]
    azConfig["acs_resource_group"] = config["acs_resource_group"]
    # now change machine names to correct
    azConfig.pop("machines", None)
    return azConfig

def acs_create_node_ips():
    nodes = acs_get_kube_nodes()
    for n in nodes:
        acs_set_create_node_ip_info(n)

def acs_get_ip_info_nodes(bNeedPrivateIP):
    nodes = acs_get_kube_nodes()
    for n in nodes:
        acs_set_node_ip_info(n, bNeedPrivateIP)
    return config["acs_node_info"]

def acs_update_machines(configLocal):
    if (not "machines" in configLocal) or (len(configLocal["machines"])==0):
        acs_set_desired_dns_nodes()
        #print "Worker: {0}".format(config["acs_agent_nodes"])
        #print "Master: {0}".format(config["acs_master_nodes"])
        configLocal["machines"] = {}
        if "acs_nodes" in config and len(config["acs_nodes"]) > 0:
            for nKey in config["acs_node_info"]:
                n = config["acs_node_info"][nKey]
                #print "NKey={0} N={1} DNS={2}".format(nKey, n, n["desiredDns"])
                if nKey in config["acs_master_nodes"]:
                    configLocal["machines"][n["desiredDns"]] = {"role": "infrastructure"}
                else:
                    configLocal["machines"][n["desiredDns"]] = {"role": "worker"}
            #exit()
            return True
        else:
            return False
    else:
        return False

def acs_update_azconfig(gen_cluster_config):
    acs_config = acs_load_azconfig()
    if not gen_cluster_config:
        if acs_config is None:
            acs_config = acs_generate_azconfig()
            acs_update_machines(acs_config)
            acs_write_azconfig(acs_config)
        else:
            acs_init_azconfig()
            bModified = acs_update_machines(acs_config)
            if bModified:
                acs_write_azconfig(acs_config)
    else:
        configNew = acs_generate_azconfig()
        if acs_config is None:
            acs_config = {}
        acs_update_machines(acs_config)
        utils.mergeDict(acs_config, configNew, False)
        acs_write_azconfig(acs_config)
    return acs_config

def acs_deploy():
    global config

    generate_key = not os.path.exists("./deploy/sshkey")

    cmd = "group create"
    cmd += " --location=%s" % config["cluster_location"]
    cmd += " --name=%s" % config["resource_group"]
    az_sys(cmd)

    cmd = "acs create --orchestrator-type=kubernetes"
    cmd += " --resource-group=%s" % config["acs_resource_group"]
    cmd += " --name=%s" % config["cluster_name"]
    cmd += " --agent-count=%d" % config["worker_node_num"]
    cmd += " --master-count=%d" % config["master_node_num"]
    cmd += " --location=%s" % config["cluster_location"]
    cmd += " --agent-vm-size=%s" % config["acsagentsize"]
    cmd += " --admin-username=%s" % config["admin_username"]
    cmd += " --ssh-key-value=%s" % "./deploy/sshkey/id_rsa.pub"
    if (generate_key):
        os.system("rm -r ./deploy/sshkey || true")
        cmd += " --generate-ssh-keys"
    az_sys(cmd)

    acs_set_resource_grp(True) # overwrite resource group if machines are elsewhere

    acs_create_storage()
    az_create_sql()

    # Add rules for NSG
    acs_add_nsg_rules({"HTTPAllow" : 80, "RestfulAPIAllow" : 5000, "AllowKubernetesServicePorts" : "30000-49999"})

    # Get kubectl binary / acs config
    acs_get_config()

    # Wait for nodes to start up
    acs_wait_for_kube()

    # Create public IP / DNS
    acs_create_node_ips()

    # Update machine names in config / storage keys
    acs_update_azconfig(True)

# Main / Globals
azConfigFile = "azure_cluster_config.yaml"
if __name__ == '__main__':
    # nothing for now
    verbose = False
    config = {}

