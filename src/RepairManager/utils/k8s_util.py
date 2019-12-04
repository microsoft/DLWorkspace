import os
import logging
from kubernetes import client, config

def cordon_node(node_name):
    output = os.system('kubectl cordon %s' % node_name)
    return output


def is_node_unschedulable(node_info, node_name):
    for node in node_info.items:
        for address in node.status.addresses:
            if address.type == 'Hostname' and address.address == node_name:
                return node.spec.unschedulable

    logging.warning(f"Could not find node with hostname {node_name}")


def list_node():
    config.load_kube_config(config_file='/etc/kubernetes/restapi-kubeconfig.yaml')
    api_instance = client.CoreV1Api()
    return api_instance.list_node()