import subprocess
import logging
from kubernetes import client, config

def cordon_node(node_name, dry_run=True):
    args = ['kubectl', 'cordon', node_name]

    if dry_run:
        args.append('--dry-run')

    try:
        output = subprocess.check_output(args, stderr=subprocess.STDOUT)
        logging.info(output.decode())
        return output.decode()
    except subprocess.CalledProcessError as e:
        logging.exception(f'Exception attempting to cordon node {node_name}')
        return e.output.decode()


def is_node_cordoned(node_info, node_name):
    for node in node_info.items:
        for address in node.status.addresses:
            if address.type == 'Hostname' and address.address == node_name:
                return node.spec.unschedulable

    logging.warning(f"Could not find node with hostname {node_name}")


def list_node():
    config.load_kube_config(config_file='/etc/kubernetes/restapi-kubeconfig.yaml')
    api_instance = client.CoreV1Api()
    return api_instance.list_node()

def list_pod_for_all_namespaces():
    config.load_kube_config(config_file='/etc/kubernetes/restapi-kubeconfig.yaml',)
    api_instance = client.CoreV1Api()
    return api_instance.list_pod_for_all_namespaces()