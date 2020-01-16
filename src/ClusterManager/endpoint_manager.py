#!/usr/bin/env python3

import json
import os
import time
import sys
import datetime
import random
import re
import logging
import yaml
import logging.config
import argparse

from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException

from cluster_manager import setup_exporter_thread, manager_iteration_histogram, register_stack_trace_dump, update_file_modification_time
from job_launcher import JobDeployer

sys.path.append(os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "../utils"))

from DataHandler import DataHandler
from config import config
import k8sUtils

logger = logging.getLogger(__name__)
deployer = JobDeployer()

k8s_config.load_kube_config()
k8s_core_api = client.CoreV1Api()

def is_ssh_server_ready(pod_name):
    bash_script = "service ssh status"
    output = k8sUtils.kubectl_exec(
        "exec %s %s" % (pod_name, " -- " + bash_script))
    if output == "":
        return False
    return True


def query_ssh_port(pod_name):
    bash_script = "grep ^Port /usr/etc/sshd_config | cut -d' ' -f2"
    status_code, output = deployer.pod_exec(
        pod_name, ["/bin/bash", "-c", bash_script])
    if status_code != 0:
        raise RuntimeError("Query ssh port failed: {}".format(pod_name))
    if not output:
        return 22
    return int(output)


def start_ssh_server(pod_name):
    '''Setup the ssh server in container, and return the listening port.'''
    bash_script = "service ssh start"  # assume ssh server already setup

    # TODO setup reasonable timeout
    # output = k8sUtils.kubectl_exec("exec %s %s" % (jobId, " -- " + bash_script), 1)
    output = k8sUtils.kubectl_exec(
        "exec %s %s" % (pod_name, " -- " + bash_script))
    if output == "":
        raise Exception(
            "Failed to setup ssh server in container. JobId: %s " % pod_name)


def get_k8s_endpoint(endpoint_id):
    try:
        resp = k8s_core_api.read_namespaced_service(endpoint_id, "default")
        return resp
    except ApiException as e:
        if e.status == 404:
            return None
        logger.exception("could not get k8s service")
        return None

def delete_k8s_endpoint(service_name):
    try:
        return k8s_core_api.delete_namespaced_service(service_name, "default")
    except ApiException as e:
        logger.exception("delete k8s service %s failed")


def generate_node_port_service(job_id, pod_name, endpoint_id, name, target_port):
    endpoint = {
        "kind": "Service",
        "apiVersion": "v1",
        "metadata": {
            "name": endpoint_id,
            "labels": {
                "run": job_id,
                "jobId": job_id,
                "pod_name": pod_name,
            }
        },
        "spec": {
            "type": "NodePort",
            "selector": {"podName": pod_name},
            "ports": [{
                "name": name,
                "protocol": "TCP",
                "targetPort": target_port,
                "port": target_port,
            }]
        }
    }
    logger.debug("endpoint description: %s", json.dumps(endpoint))
    return endpoint


def create_node_port(endpoint):
    endpoint_description = generate_node_port_service(
        endpoint["jobId"], endpoint["podName"], endpoint["id"], endpoint["name"], endpoint["podPort"])

    try:
        resp = k8s_core_api.create_namespaced_service("default", endpoint_description)
        logger.info("submitted endpoint %s to k8s, returned with status %s",
                    endpoint["jobId"], resp)
    except ApiException as e:
        logger.exception("could not create k8s service")
        raise Exception(
            "Failed to create NodePort for ssh. JobId: %s " % endpoint["jobId"])

def setup_ssh_server(user_name, pod_name, host_network=False):
    '''Setup ssh server on pod and return the port'''
    # setup ssh server only is the ssh server is not up
    if not is_ssh_server_ready(pod_name):
        logger.info("Ssh server is not ready for pod: %s. Setup ...", pod_name)
        start_ssh_server(pod_name)
    ssh_port = query_ssh_port(pod_name)
    logger.info("Ssh server is ready for pod: %s. Ssh listen on %s",
                pod_name, ssh_port)
    return ssh_port


def setup_jupyter_server(user_name, pod_name):
    jupyter_port = random.randint(40000, 49999)
    bash_script = "bash -c 'export DEBIAN_FRONTEND=noninteractive; apt-get update && apt-get install -y python3-pip && python3 -m pip install --upgrade pip && python3 -m pip install jupyter && cd /home/" + \
        user_name + " && runuser -l " + user_name + \
        " -c \"jupyter notebook --no-browser --ip=0.0.0.0 --NotebookApp.token= --port=" + \
        str(jupyter_port) + " &>/dev/null &\"'"
    output = k8sUtils.kubectl_exec(
        "exec %s %s" % (pod_name, " -- " + bash_script))
    if output == "":
        raise Exception(
            "Failed to start jupyter server in container. JobId: %s " % pod_name)
    else:
        logger.info("install jupyter output is %s", output)
    return jupyter_port


def setup_tensorboard(user_name, pod_name):
    tensorboard_port = random.randint(40000, 49999)
    bash_script = "bash -c 'export DEBIAN_FRONTEND=noninteractive; pip install tensorboard; runuser -l " + user_name + \
        " -c \"mkdir -p ~/tensorboard/\${DLWS_JOB_ID}/logs; nohup tensorboard --logdir=~/tensorboard/\${DLWS_JOB_ID}/logs --port=" + str(
            tensorboard_port) + " &>/dev/null &\"'"
    output = k8sUtils.kubectl_exec(
        "exec %s %s" % (pod_name, " -- " + bash_script))
    if output == "":
        raise Exception(
            "Failed to start tensorboard in container. JobId: %s " % pod_name)
    else:
        logger.info("install tensorboard output is %s", output)
    return tensorboard_port


def start_endpoint(endpoint):
    # pending, running, stopped
    logger.info("Starting endpoint: %s", endpoint)

    # podName
    pod_name = endpoint["podName"]
    user_name = endpoint["username"]
    host_network = endpoint["hostNetwork"]

    port_name = endpoint["name"]
    if port_name == "ssh":
        endpoint["podPort"] = setup_ssh_server(
            user_name, pod_name, host_network)
    elif port_name == "ipython":
        endpoint["podPort"] = setup_jupyter_server(user_name, pod_name)
    elif port_name == "tensorboard":
        endpoint["podPort"] = setup_tensorboard(user_name, pod_name)
    else:
        endpoint["podPort"] = int(endpoint["podPort"])

    # create NodePort
    create_node_port(endpoint)


def start_endpoints():
    try:
        data_handler = DataHandler()
        try:
            pending_endpoints = data_handler.GetPendingEndpoints()

            for endpoint_id, endpoint in list(pending_endpoints.items()):
                try:
                    job = data_handler.GetJob(jobId=endpoint["jobId"])[0]
                    logger.info("checking endpoint %s, status is %s", endpoint["jobId"], job["jobStatus"])
                    if job["jobStatus"] != "running":
                        continue

                    point = get_k8s_endpoint(endpoint["id"])
                    logger.info("endpoint of %s has %s", endpoint["jobId"], point)
                    if point is not None:
                        endpoint["status"] = "running"
                        # only retain spec here, some other fields have datetime,
                        # can not be serialized to json
                        endpoint["endpointDescription"] = {"spec": point.spec.to_dict()}
                        pod = k8sUtils.GetPod("podName=" + endpoint["podName"])
                        if "items" in pod and len(pod["items"]) > 0:
                            logger.info("update endpoint's nodeName %s", endpoint["jobId"])
                            endpoint["nodeName"] = pod["items"][0]["spec"]["nodeName"]
                    else:
                        start_endpoint(endpoint)

                    endpoint["lastUpdated"] = datetime.datetime.now().isoformat()
                    data_handler.UpdateEndpoint(endpoint)
                except Exception as e:
                    logger.warning("Process endpoint failed {}".format(
                        endpoint), exc_info=True)
        except Exception as e:
            logger.exception("start endpoint failed")
        finally:
            data_handler.Close()
    except Exception as e:
        logger.exception("close data handler failed")


def cleanup_endpoints():
    try:
        data_handler = DataHandler()
        try:
            dead_endpoints = data_handler.GetDeadEndpoints()
            for endpoint_id, dead_endpoint in list(dead_endpoints.items()):
                try:
                    logger.info("Begin to cleanup endpoint %s", endpoint_id)
                    point = get_k8s_endpoint(dead_endpoint["id"])
                    if point is None:
                        logger.info("Endpoint already gone %s", endpoint_id)
                        status = "stopped"
                    else:
                        delete_resp = delete_k8s_endpoint(endpoint.metadata.name)
                        logger.info("delete_resp for endpoint is %s", delete_resp)
                    # we are not changing status from "pending", "pending" endpoints are planed to setup later
                    if dead_endpoint["status"] != "pending":
                        dead_endpoint["status"] = status
                    dead_endpoint["lastUpdated"] = datetime.datetime.now(
                    ).isoformat()
                    data_handler.UpdateEndpoint(dead_endpoint)
                except Exception as e:
                    logger.warning("Clanup endpoint failed {}".format(
                        dead_endpoint), exc_info=True)
        except Exception as e:
            logger.exception("cleanup endpoint failed")
        finally:
            data_handler.Close()
    except Exception as e:
        logger.exception("close data handler failed")


def create_log(logdir='/var/log/dlworkspace'):
    if not os.path.exists(logdir):
        os.system("mkdir -p " + logdir)
    with open('logging.yaml') as f:
        logging_config = yaml.full_load(f)
        f.close()
        logging_config["handlers"]["file"]["filename"] = logdir + \
            "/endpoint_manager.log"
        logging.config.dictConfig(logging_config)


def Run():
    register_stack_trace_dump()
    create_log()

    while True:
        update_file_modification_time("endpoint_manager")

        with manager_iteration_histogram.labels("endpoint_manager").time():
            # start endpoints
            start_endpoints()
            time.sleep(1)

            # clean up endpoints for jobs which is NOT running
            cleanup_endpoints()
        time.sleep(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--port", "-p", help="port of exporter", type=int, default=9205)
    args = parser.parse_args()
    setup_exporter_thread(args.port)

    Run()
