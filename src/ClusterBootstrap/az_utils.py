#!/usr/bin/python3

from utils import exec_cmd_local, execute_or_dump_locally


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

