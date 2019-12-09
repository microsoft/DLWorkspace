import subprocess
import logging
from kubernetes import client, config

def cordon_node(node_name, dry_run=True):
    args = ['kubectl', 'cordon', node_name]

    if dry_run:
        args.append('--dry-run')

    try:
        output = subprocess.check_output(args, stderr=subprocess.STDOUT)
        output_decoded = output.decode()
        logging.info(output_decoded)
        return output_decoded
    except Exception as e:
        logging.exception(f'Exception attempting to cordon node {node_name}')
        return str(e)


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