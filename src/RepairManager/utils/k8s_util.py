import subprocess
import logging
from kubernetes import client, config

kubernetes_config_file = '/etc/kubernetes/restapi-kubeconfig.yaml'

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
    config.load_kube_config(config_file=kubernetes_config_file)
    api_instance = client.CoreV1Api()
    return api_instance.list_node()



def list_pod_for_all_namespaces():
    config.load_kube_config(config_file=kubernetes_config_file)
    api_instance = client.CoreV1Api()
    return api_instance.list_pod_for_all_namespaces()



def list_namespaced_pod(namespace):
    config.load_kube_config(config_file=kubernetes_config_file)
    api_instance = client.CoreV1Api()
    return api_instance.list_namespaced_pod(namespace)


def get_job_info_from_nodes(nodes, portal_url, cluster_name):
    pods = list_namespaced_pod("default")
    jobs = {}
    for pod in pods.items:
        if pod.metadata and pod.metadata.labels:
            if 'jobId' in pod.metadata.labels and 'userName' in pod.metadata.labels:
                if pod.spec.node_name in nodes:
                    job_id = pod.metadata.labels['jobId']
                    user_name = pod.metadata.labels['userName']
                    node_name = pod.spec.node_name
                    vc_name = pod.metadata.labels['vcName']
                    if job_id not in jobs:
                        jobs[job_id] = {
                        'user_name': user_name,
                        'node_names': {node_name},
                        'vc_name': vc_name,
                        'job_link': f'https://{portal_url}/job/{vc_name}/{cluster_name}/{job_id}'}
                    else:
                        jobs[job_id]['node_names'].add(node_name)
    return jobs


def get_node_address_info():
    # map InternalIP to Hostname
    node_info = list_node()
    address_map = {}
    if node_info:
        for node in node_info.items:
            internal_ip = None
            hostname = None
            for address in node.status.addresses:
                if address.type == 'InternalIP':
                    internal_ip = address.address
                if address.type == 'Hostname':
                    hostname = address.address
                address_map[internal_ip] = hostname
    logging.debug(f'node address map: {address_map}')
    return address_map
