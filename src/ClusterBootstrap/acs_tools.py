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

def acs_get_id(elem):
    elemFullName = elem["id"]
    reMatch = re.match('(.*)/(.*)', elemFullName)
    return reMatch.group(2)

def acs_get_ip(ipaddrName):
    ipInfo = az_cmd("network public-ip show --resource-group="+config["resource_group"]+" --name="+ipaddrName)
    return ipInfo["ipAddress"]

def acs_attach_dns_to_node(node, dnsName=None):
    nodeName = config["nodenames_from_ip"][node]
    if (dnsName is None):
        dnsName = nodeName
    ipName = config["acsnodes"][nodeName]["publicipname"]
    cmd = "network public-ip update"
    cmd += " --resource-group=%s" % config["resource_group"]
    cmd += " --name=%s" % ipName
    cmd += " --dns-name=%s" % dnsName
    az_sys(cmd) 

def acs_get_machineIP(machineName):
    print "Machine: "+machineName
    nics = az_cmd("vm show --name="+machineName+" --resource-group="+config["resource_group"])
    #print nics
    nics = nics["networkProfile"]["networkInterfaces"]
    i = 0
    for nic in nics:
        nicName = acs_get_id(nic)
        print "Nic Name: "+nicName
        if (i==0):
            nicDefault = nicName
        ipconfigs = az_cmd("network nic show --resource-group="+config["resource_group"]+" --name="+nicName)
        ipConfigs = ipconfigs["ipConfigurations"]
        j = 0
        for ipConfig in ipConfigs:
            ipConfigName = acs_get_id(ipConfig)
            print "IP Config Name: "+ipConfigName
            if ((i==0) and (j==0)):
                ipConfigDefault = ipConfigName
            configInfo = az_cmd("network nic ip-config show --resource-group="+config["resource_group"]+
                                " --nic-name="+nicName+" --name="+ipConfigName)
            publicIP = configInfo["publicIpAddress"]
            if (not (publicIP is None)):
                ipName = acs_get_id(publicIP)
                print "IP Name: " + ipName
                return {"nic" : nicName, "ipconfig" : ipConfigName, "publicipname" : ipName, "publicip" : acs_get_ip(ipName)}
            j+=1
        i+=1
    return {"nic" : nicDefault, "ipconfig": ipConfigDefault, "publicipname" : None, "publicip" : None}

def acs_get_nodes():
    binary = os.path.abspath('./deploy/bin/kubectl')
    kubeconfig = os.path.abspath('./deploy/'+config["acskubeconfig"])
    cmd = binary + ' -o=json --kubeconfig='+kubeconfig+' get nodes'
    nodeInfo = utils.subproc_runonce(cmd)
    nodes = yaml.load(nodeInfo)
    return nodes["items"]

def acs_get_machinesAndIPs(bCreateIP):
    # Public IP on worker nodes
    nodes = acs_get_nodes()
    ipInfo = {}
    #print nodes["items"]
    config["nodenames_from_ip"] = {}
    for n in nodes:
        machineName = n["metadata"]["name"]
        ipInfo[machineName] = acs_get_machineIP(machineName)
        if bCreateIP and (ipInfo[machineName]["publicip"] is None):
            # Create IP
            ipName = machineName+"-public-ip-0"
            print "Creating public-IP: "+ipName
            cmd = "network public-ip create --allocation-method=Dynamic"
            cmd += " --resource-group=%s" % config["resource_group"]
            cmd += " --name=%s" % ipName
            cmd += " --location=%s" % config["cluster_location"]
            az_sys(cmd)
            # Add to NIC of machine
            cmd = "network nic ip-config update"
            cmd += " --resource-group=%s" % config["resource_group"]
            cmd += " --nic-name=%s" % ipInfo[machineName]["nic"]
            cmd += " --name=%s" % ipInfo[machineName]["ipconfig"]
            cmd += " --public-ip-address=%s" % ipName
            az_sys(cmd)
            # now update
            ipInfo[machineName]["publicipname"] = ipName
            ipInfo[machineName]["publicip"] = acs_get_ip(ipName)
        config["nodenames_from_ip"][ipInfo[machineName]["publicip"]] = machineName
    return ipInfo

def acs_get_machinesAndIPsFast():
    nodes = acs_get_nodes()
    ipInfo = {}
    config["nodenames_from_ip"] = {}
    for n in nodes:
        machineName = n["metadata"]["name"]
        #print "MachineName: "+machineName
        ipName = machineName+"-public-ip-0"
        if (verbose):
            print "PublicIP: "+ipName
        ipInfo[machineName] = {}
        ipInfo[machineName]["publicipname"] = ipName
        ipInfo[machineName]["publicip"] = acs_get_ip(ipName)
        config["nodenames_from_ip"][ipInfo[machineName]["publicip"]] = machineName
    return ipInfo

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

def acs_generate_azconfig():
    az_tools.config = az_tools.init_config()
    az_tools.config["azure_cluster"]["cluster_name"] = config["cluster_name"]
    az_tools.config["azure_cluster"]["azure_location"] = config["cluster_location"]
    az_tools.config = az_tools.update_config(az_tools.config, False)
    if not "resource_group" in config:
        config["resource_group"] = az_tools.config["azure_cluster"]["resource_group_name"]
    acs_set_resource_grp(False)
    az_tools.config["azure_cluster"]["resource_group_name"] = config["resource_group"]
    azConfig = az_tools.gen_cluster_config("", False)
    # add resource group names
    azConfig["resource_group"] = config["resource_group"]
    azConfig["acs_resource_group"] = config["acs_resource_group"]
    # now change machine names to correct
    azConfig.pop("machines", None)
    return azConfig

#def acs_update_machines():
    

def acs_update_azconfig(gen_cluster_config):
    config = acs_load_azconfig()
    if not gen_cluster_config:
        if config is None:
            config = acs_generate_azconfig()
            acs_write_azconfig(config)
        else:
            az_tools.config = {}
            az_tools.config["azure_cluster"] = {}
    else:
        configNew = acs_generate_azconfig()
        if config is None:
            config = {}
        utils.mergeDict(config, configNew, False)
        acs_write_azconfig(config)
    return config

def acs_deploy():
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

    acs_update_azconfig(True)

    acs_get_config()

    # Get/create public IP addresses for all machines
    Nodes = acs_get_machinesAndIPs(True)

    # Add rules for NSG
    acs_add_nsg_rules({"HTTPAllow" : 80, "RestfulAPIAllow" : 5000, "AllowKubernetesServicePorts" : "30000-32767"})

    return Nodes

# Main / Globals
azConfigFile = "azure_cluster_config.yaml"
if __name__ == '__main__':
    # nothing for now
    verbose = False
    config = {}

