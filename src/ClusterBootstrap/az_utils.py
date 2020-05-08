#!/usr/bin/python3

import json
import yaml

from utils import exec_cmd_local, execute_or_dump_locally, keep_widest_subnet


def set_subscription(config):
    if "subscription" not in config["azure_cluster"]:
        print("No subscription to set")
        return

    subscription = config["azure_cluster"]["subscription"]

    chkcmd = "az account list | grep -A5 -B5 '\"isDefault\": true'"
    output = exec_cmd_local(chkcmd)
    if not subscription in output:
        setcmd = "az account set --subscription \"{}\"".format(subscription)
        setout = exec_cmd_local(setcmd)
    assert subscription in exec_cmd_local(chkcmd, True)


def whitelist_source_address_prefixes(config):
    resource_group = config["azure_cluster"]["resource_group"]
    nsg_name = config["azure_cluster"]["nsg_name"]

    cmd = """
        az network nsg rule show \
            --resource-group %s \
            --nsg-name %s \
            --name whitelist
        """ % (resource_group,
               nsg_name)

    output = exec_cmd_local(cmd)

    source_address_prefixes = []
    try:
        data = json.loads(output)

        source = data.get("sourceAddressPrefix")
        if source is not None and source != "":
            source_address_prefixes.append(source)

        sources = data.get("sourceAddressPrefixes")
        if sources is not None:
            source_address_prefixes += sources
    except Exception:
        print("Exception when parsing whitelist response. "
              "Ignore existing whitelist")

    return source_address_prefixes


def add_nsg_rule_whitelist(config, args, ips):
    # Replicating dev_network access for whitelisting users
    source_address_prefixes = whitelist_source_address_prefixes(config)
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
    source_address_prefixes = keep_widest_subnet(source_address_prefixes)

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

    execute_or_dump_locally(cmd, args.verbose, args.dryrun, args.output)


def remove_nsg_rule_whitelist(config, args, ips):
    source_address_prefixes = whitelist_source_address_prefixes(config)

    # Assume ips is a comma separated string if valid
    if ips is not None and ips != "":
        ips = ips.split(",")

    resource_group = config["azure_cluster"]["resource_group"]
    nsg_name = config["azure_cluster"]["nsg_name"]

    new_source_address_prefixes = []
    for prefix in source_address_prefixes:
        if prefix not in ips:
            new_source_address_prefixes.append(prefix)

    if len(new_source_address_prefixes) == 0:
        print("Nothing will be left in whitelist, please use delete command!")
        return

    cmd = """
        az network nsg rule update \
            --resource-group %s \
            --nsg-name %s \
            --name whitelist \
            --source-address-prefixes %s 
        """ % (resource_group,
               nsg_name,
               " ".join(new_source_address_prefixes))

    execute_or_dump_locally(cmd, args.verbose, args.dryrun, args.output)


def delete_nsg_rule_whitelist(config, args):
    resource_group = config["azure_cluster"]["resource_group"]
    nsg_name = config["azure_cluster"]["nsg_name"]

    cmd = """
        az network nsg rule delete \
            --resource-group %s \
            --nsg-name %s \
            --name whitelist
        """ % (resource_group,
               nsg_name)

    execute_or_dump_locally(cmd, args.verbose, args.dryrun, args.output)


def create_nsg_rule(resource_group, nsg_name, priority, rule_name,
                                     port_ranges, service_tag_or_ip,
                                     args, protocol="tcp"):
    cmd = """
        az network nsg rule create \
            --resource-group %s \
            --nsg-name %s \
            --name %s \
            --protocol %s \
            --priority %s \
            --destination-port-ranges %s \
            --source-address-prefixes %s \
            --access allow
        """ % (resource_group,
               nsg_name,
               rule_name,
               protocol,
               priority,
               port_ranges,
               service_tag_or_ip)
    execute_or_dump_locally(cmd, args.verbose, args.dryrun, args.output)


def delete_nsg_rule(resource_group, nsg_name, rule_name,
                                     args):
    cmd = """
        az network nsg rule delete \
            --resource-group {} \
            --nsg-name {} \
            --name {}
        """.format(resource_group,
               nsg_name, rule_name)
    execute_or_dump_locally(cmd, args.verbose, args.dryrun, args.output)


# deprecated after updating port of nsg rules and converting configs
def create_nsg_rule_with_service_tag(resource_group, nsg_name, priority,
                                     port_ranges, service_tag, args,
                                     protocol="tcp"):
    cmd = """
        az network nsg rule create \
            --resource-group %s \
            --nsg-name %s \
            --name %s \
            --protocol %s \
            --priority %s \
            --destination-port-ranges %s \
            --source-address-prefixes %s \
            --access allow
        """ % (resource_group,
               nsg_name,
               "allow_%s" % service_tag,
               protocol,
               priority,
               port_ranges,
               service_tag)
    execute_or_dump_locally(cmd, args.verbose, args.dryrun, args.output)


# deprecated after updating port of nsg rules and converting configs
def delete_nsg_rule_with_service_tag(resource_group, nsg_name, service_tag,
                                     args):
    cmd = """
        az network nsg rule delete \
            --resource-group %s \
            --nsg-name %s \
            --name %s
        """ % (resource_group,
               nsg_name,
               "allow_%s" % service_tag)
    execute_or_dump_locally(cmd, args.verbose, args.dryrun, args.output)


def create_nsg_rules_with_service_tags(config, args):
    nsg_rules = config["cloud_config_nsg_rules"]
    service_tags = nsg_rules.get("service_tags", [])
    if not isinstance(service_tags, list):
        print("service_tags %s is not a list. Skip creating nsg rules with "
              "service tags." % service_tags)
        return

    tcp_port_ranges = nsg_rules.get("tcp_port_ranges")
    if tcp_port_ranges is None:
        print("tcp_port_ranges does not exist. Skip creating nsg rules with "
              "service tags.")

    # Reserve priority 950 - 999 for service tag rules
    max_rules = 50
    if len(service_tags) > max_rules:
        print("Creating up to %s nsg rules with service tags. The rest will "
              "be ignored." % max_rules)

    resource_group = config["azure_cluster"]["resource_group"]
    nsg_name = config["azure_cluster"]["nsg_name"]

    base_priority = 950
    for i, service_tag in enumerate(service_tags[:max_rules]):
        print("Creating nsg rule for service tag %s" % service_tag)
        create_nsg_rule_with_service_tag(resource_group,
                                         nsg_name,
                                         base_priority + i,
                                         tcp_port_ranges,
                                         service_tag,
                                         args)


def delete_nsg_rules_with_service_tags(config, args):
    nsg_rules = config["cloud_config_nsg_rules"]
    service_tags = nsg_rules.get("service_tags", [])
    if not isinstance(service_tags, list):
        print("service_tags %s is not a list. Skip deleting nsg rules with "
              "service tags." % service_tags)
        return

    resource_group = config["azure_cluster"]["resource_group"]
    nsg_name = config["azure_cluster"]["nsg_name"]

    # Try to delete all service tag rules
    for i, service_tag in enumerate(service_tags):
        try:
            print("Deleting nsg rule for service tag %s" % service_tag)
            delete_nsg_rule_with_service_tag(resource_group,
                                             nsg_name,
                                             service_tag,
                                             args)
        except Exception as e:
            print("Failed to delete nsg rule for service tag %s. Ex: %s" %
                  (service_tag, e))


def get_cluster_name(config):
    # Old pipeline has cluster_name in azure_cluster
    cluster_name = config.get("cluster_name")
    if cluster_name is not None:
        return cluster_name

    return config["azure_cluster"]["cluster_name"]


def gen_name_with_max_len(name, max_len):
    if len(name) > max_len:
        name = name[:max_len]
    return name


def gen_logging_storage_account_name(config):
    # There are naming restrictions for account_name:
    # Storage account name must be between 3 and 24 characters in length
    # and use numbers and lower-case letters only.
    name = get_cluster_name(config).lower()
    name = "".join([c for c in name if c.isalnum()])
    return gen_name_with_max_len(name, 24)


def gen_logging_container_name(config):
    # There are nameing restrictions for container_name:
    # Container name must be between 3 and 63 characters in length
    # and use numbers and lower-case letters only. Hyphen is allowed.
    name = get_cluster_name(config).lower()
    name = "".join([c for c in name if c.isalnum() or c == "-"])
    return gen_name_with_max_len(name, 63)


def get_connection_string(config, args):
    storage_account_name = gen_logging_storage_account_name(config)
    resource_group = config["azure_cluster"]["resource_group"]
    cmd = """
        az storage account show-connection-string \
            --name %s \
            --resource-group %s \
            --query 'connectionString' \
            --output tsv
        """ % (storage_account_name,
               resource_group)

    connection_string = \
        execute_or_dump_locally(cmd, args.verbose, args.dryrun, args.output)
    return connection_string.strip("\n")



def create_logging_container(config, args):
    container_name = gen_logging_container_name(config)
    connection_string = get_connection_string(config, args)
    cmd = """
        az storage container create \
            --name %s \
            --connection-string '%s'
        """ % (container_name,
               connection_string)

    print("Creating logging container %s with connection string %s" % 
          (container_name, connection_string))
    execute_or_dump_locally(cmd, args.verbose, args.dryrun, args.output)


def create_logging_storage_account(config, args):
    storage_account_name = gen_logging_storage_account_name(config)
    resource_group = config["azure_cluster"]["resource_group"]
    location = config["azure_cluster"]["azure_location"]
    cmd = """
        az storage account create \
            --name %s \
            --resource-group %s \
            --access-tier Hot \
            --kind StorageV2 \
            --sku Standard_RAGRS \
            --location %s
        """ % (storage_account_name,
               resource_group,
               location)

    print("Creating storage account %s in resource group %s" % 
          (storage_account_name, resource_group))
    execute_or_dump_locally(cmd, args.verbose, args.dryrun, args.output)


def delete_logging_storage_account(config, args):
    storage_account_name = gen_logging_storage_account_name(config)
    resource_group = config["azure_cluster"]["resource_group"]
    cmd = """
        az storage account delete \
            --name %s \
            --resource-group %s \
            --yes
        """ % (storage_account_name,
               resource_group)

    print("Deleting storage account %s in resource group %s" % 
          (storage_account_name, resource_group))
    execute_or_dump_locally(cmd, args.verbose, args.dryrun, args.output)


def get_connection_string_for_logging_storage_account(config, args):
    connection_string = get_connection_string(config, args)
    container_name = gen_logging_container_name(config)

    logging_config = {
        "azure_blob_log": {
            "enabled": True,
            "connection_string": connection_string,
            "container_name": container_name,
        }
    }

    # Print connection string
    print(logging_config)
    print(yaml.dump(logging_config))

    # Dump connection string to a file
    with open("logging_config.yaml", "w") as f:
        yaml.dump(logging_config, f)


