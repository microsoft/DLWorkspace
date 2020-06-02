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
import pytz

from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream
from kubernetes.stream.ws_client import ERROR_CHANNEL, STDERR_CHANNEL, STDOUT_CHANNEL

from cluster_manager import setup_exporter_thread, manager_iteration_histogram, register_stack_trace_dump, update_file_modification_time

sys.path.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../utils"))

from DataHandler import DataHandler
from config import config
import k8sUtils

logger = logging.getLogger(__name__)

k8s_config.load_kube_config()
k8s_core_api = client.CoreV1Api()


def is_ssh_server_ready(pod_name):
    bash_script = "service ssh status"
    output = k8sUtils.kubectl_exec("exec %s %s" %
                                   (pod_name, " -- " + bash_script))
    if output == "":
        return False
    return True


def pod_exec(pod_name, exec_command, timeout=60):
    """work as the command (with timeout): kubectl exec 'pod_name' 'exec_command'"""
    try:
        logger.debug("Exec on pod %s: %s", pod_name, exec_command)
        client = stream(
            k8s_core_api.connect_get_namespaced_pod_exec,
            name=pod_name,
            namespace="default",
            command=exec_command,
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False,
            _preload_content=False,
        )
        client.run_forever(timeout=timeout)

        err = yaml.full_load(client.read_channel(ERROR_CHANNEL))
        if err is None:
            return [-1, "Timeout"]

        if err["status"] == "Success":
            status_code = 0
        else:
            logger.debug("Exec on pod %s failed. cmd: %s, err: %s.", pod_name,
                         exec_command, err)
            status_code = int(err["details"]["causes"][0]["message"])
        output = client.read_all()
        logger.info("Exec on pod %s, status: %s, cmd: %s, output: %s", pod_name,
                    status_code, exec_command, output)
        return [status_code, output]
    except ApiException as err:
        logger.exception("Exec on pod %s error. cmd: %s, err: %s.", pod_name,
                         exec_command, err)
        return [-1, err.message]


def query_ssh_port(pod_name):
    bash_script = "grep ^Port /usr/etc/sshd_config | cut -d' ' -f2"
    status_code, output = pod_exec(pod_name, ["/bin/bash", "-c", bash_script])
    if status_code != 0:
        raise RuntimeError("Query ssh port failed: {}".format(pod_name))
    if not output:
        return 22
    return int(output)


def start_ssh_server(pod_name):
    '''Setup the ssh server in container, and return the listening port.'''
    bash_script = "service ssh start" # assume ssh server already setup

    # TODO setup reasonable timeout
    # output = k8sUtils.kubectl_exec("exec %s %s" % (jobId, " -- " + bash_script), 1)
    output = k8sUtils.kubectl_exec("exec %s %s" %
                                   (pod_name, " -- " + bash_script))
    if output == "":
        raise Exception("Failed to setup ssh server in container. JobId: %s " %
                        pod_name)


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


def generate_service_selector(pod_name):
    """
                |   python launcher  | framework controller
    ------------------------------------------------
    regular     | ab8e7a11-bff7-497f-bd6d-22a326d2c304 | 9cfb453b7afc453bb40a963be1225549-master-0
    distributed | 842e9fc8-a4a1-425c-b551-4e5b4fad4337-{ps,worker}[0-9]+ | eb43c114365a441881faf95ac24a9f88-{ps,worker}-[0-9]+
    """
    parts = pod_name.split("-")
    if len(parts) == 3:
        # job created by framework controller
        uuid, role, idx = parts
        return {
            "FC_FRAMEWORK_NAME": uuid,
            "FC_TASKROLE_NAME": role,
            "FC_TASK_INDEX": idx
        }
    else:
        return {"podName": pod_name}


def generate_node_port_service(job_id, pod_name, endpoint_id, name,
                               target_port):
    # Ref: https://kubernetes.io/docs/concepts/services-networking/service/#nodeport
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
            "type":
                "NodePort",
            "selector":
                generate_service_selector(pod_name),
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
    endpoint_description = generate_node_port_service(endpoint["jobId"],
                                                      endpoint["podName"],
                                                      endpoint["id"],
                                                      endpoint["name"],
                                                      endpoint["podPort"])

    try:
        resp = k8s_core_api.create_namespaced_service("default",
                                                      endpoint_description)
        logger.debug("submitted endpoint %s to k8s, returned with status %s",
                     endpoint["jobId"], resp)
    except ApiException as e:
        logger.exception("could not create k8s service")
        raise Exception("Failed to create NodePort for ssh. JobId: %s " %
                        endpoint["jobId"])


def setup_ssh_server(user_name, pod_name, host_network=False):
    '''Setup ssh server on pod and return the port'''
    # setup ssh server only is the ssh server is not up
    if not is_ssh_server_ready(pod_name):
        logger.info("Ssh server is not ready for pod: %s. Setup ...", pod_name)
        start_ssh_server(pod_name)
    ssh_port = query_ssh_port(pod_name)
    logger.info("Ssh server is ready for pod: %s. Ssh listen on %s", pod_name,
                ssh_port)
    return ssh_port


def setup_jupyter_server(user_name, pod_name):
    jupyter_port = random.randint(40000, 49999)
    bash_script = "bash -c 'export DEBIAN_FRONTEND=noninteractive; apt-get update && apt-get --no-install-recommends install -y python3-pip && python3 -m pip install --upgrade pip && python3 -m pip install jupyter && cd /home/" + \
        user_name + " && runuser -l " + user_name + \
        " -c \"jupyter notebook --no-browser --ip=0.0.0.0 --NotebookApp.token= --port=" + \
        str(jupyter_port) + " &>> /tmp/dlts-jupyter.out &\"'"
    output = k8sUtils.kubectl_exec("exec %s %s" %
                                   (pod_name, " -- " + bash_script))
    if output == "":
        raise Exception(
            "Failed to start jupyter server in container. JobId: %s " %
            pod_name)
    else:
        logger.info("install jupyter output is %s", output)
    return jupyter_port


def setup_tensorboard(user_name, pod_name):
    tensorboard_port = random.randint(40000, 49999)
    bash_script = "bash -c 'export DEBIAN_FRONTEND=noninteractive; pip install tensorboard; runuser -l " + user_name + \
        " -c \"mkdir -p ~/tensorboard/\${DLWS_JOB_ID}/logs; nohup tensorboard --logdir=~/tensorboard/\${DLWS_JOB_ID}/logs --port=" + str(
            tensorboard_port) + " &>> /tmp/dlts-tensorboard.out &\"'"
    output = k8sUtils.kubectl_exec("exec %s %s" %
                                   (pod_name, " -- " + bash_script))
    if output == "":
        raise Exception("Failed to start tensorboard in container. JobId: %s " %
                        pod_name)
    else:
        logger.info("install tensorboard output is %s", output)
    return tensorboard_port


def infer_real_pod_name(origin_pod_name):
    """ Because restfulapi will generate pod name according to rule previous launcher do,
    but framework controller will not do this, so we try to generate a real pod name if we
    used framework controller """
    if k8sUtils.get_pod("default", origin_pod_name) is not None:
        return origin_pod_name

    # must be controller jobs
    name_part = origin_pod_name.split("-")
    if len(name_part) == 5: # regular job
        return "".join(name_part) + "-master-0"
    else:
        match = re.match("([a-z]+)([0-9]+)", name_part[-1])
        if match:
            role, idx = match.groups()
            name_part.pop()
            return "".join(name_part) + "-%s-%s" % (role, idx)
        logger.warning("unknown pod_name format %s", origin_pod_name)
        return origin_pod_name


def start_endpoint(endpoint):
    logger.info("Starting endpoint: %s", endpoint)

    pod_name = infer_real_pod_name(endpoint["podName"])
    endpoint["podName"] = pod_name
    user_name = endpoint["username"]
    host_network = endpoint["hostNetwork"]

    port_name = endpoint["name"]
    if port_name == "ssh":
        endpoint["podPort"] = setup_ssh_server(user_name, pod_name,
                                               host_network)
    elif port_name == "ipython":
        endpoint["podPort"] = setup_jupyter_server(user_name, pod_name)
    elif port_name == "tensorboard":
        endpoint["podPort"] = setup_tensorboard(user_name, pod_name)
    else:
        endpoint["podPort"] = int(endpoint["podPort"])

    # create NodePort
    create_node_port(endpoint)


def start_endpoints():
    runnings = {} # return endpoints with status running to check it's status

    try:
        data_handler = DataHandler()
        try:
            pendings, runnings = data_handler.GetPendingEndpoints()

            for endpoint_id, endpoint in pendings.items():
                update_file_modification_time("endpoint_manager")

                try:
                    job = data_handler.GetJob(jobId=endpoint["jobId"])[0]
                    logger.info("checking endpoint %s, status is %s",
                                endpoint["jobId"], job["jobStatus"])
                    if job["jobStatus"] != "running":
                        continue

                    point = get_k8s_endpoint(endpoint["id"])
                    logger.debug("get endpoint %s", endpoint["jobId"])
                    if point is not None:
                        endpoint["status"] = "running"
                        # only retain spec here, some other fields have datetime,
                        # can not be serialized to json
                        endpoint["endpointDescription"] = {
                            "spec": point.spec.to_dict()
                        }
                        pod = k8sUtils.get_pod("default", endpoint["podName"])
                        if pod is not None:
                            logger.info("update endpoint's nodeName %s, %s",
                                        endpoint["jobId"], pod.spec.node_name)
                            endpoint["nodeName"] = pod.spec.node_name
                    else:
                        start_endpoint(endpoint)

                    endpoint["lastUpdated"] = datetime.datetime.now().isoformat(
                    )
                    data_handler.UpdateEndpoint(endpoint)
                except Exception as e:
                    logger.exception("Process endpoint failed %s", endpoint)
        except Exception as e:
            logger.exception("start endpoint failed")
        finally:
            data_handler.Close()
    except Exception as e:
        logger.exception("close data handler failed")
    return runnings


def fix_endpoints(runnings):
    if len(runnings) == 0:
        logger.debug("no running endpoints to fix")
        return

    resp = k8s_core_api.list_namespaced_pod(
        namespace="default",
        pretty="pretty_example",
        label_selector="type=job",
    )
    start = pytz.UTC.localize(datetime.datetime.now() -
                              datetime.timedelta(hours=1))
    pods = {
        pod.metadata.name: pod
        for pod in resp.items
        if pod.metadata.creation_timestamp > start
    }
    logger.info("get running pods %s", pods.keys())

    with DataHandler() as data_handler:
        for endpoint_id, point in runnings.items():
            update_file_modification_time("endpoint_manager")

            if is_need_fix(endpoint_id, point, pods):
                delete_k8s_endpoint(point["id"])
                point["status"] = "pending"
                logger.info("reset endpoint %s to pending", endpoint_id)
                data_handler.UpdateEndpoint(point)


def is_need_fix(endpoint_id, endpoint, pods):
    try:
        pod_name = endpoint["podName"]
        node_name = endpoint["nodeName"]
        pod_port = endpoint["podPort"]
        endpoint_type = endpoint["name"]

        real_pod = pods.get(pod_name)

        if real_pod is None: # pod maybe old than 1 hour, skip check to accelerate
            return False

        if node_name != real_pod.spec.node_name:
            return True

        # check if service started
        if endpoint_type in {"ipython", "tensorboard"}:
            binary = {"ipython": "jupyter", "tensorboard": "tensorboard"}

            status_code, output = pod_exec(pod_name,
                                           ["pgrep", binary[endpoint_type]])
            return status_code != 0
        elif endpoint_type == "ssh":
            if is_ssh_server_ready(pod_name):
                ssh_port = query_ssh_port(pod_name)
                return ssh_port != pod_port
            else:
                return True
        else:
            logger.warning("unknown endpoint_type %s for %s", endpoint_type,
                           endpoint_id)
    except Exception:
        logger.exception("processing running endpoint %s failed", endpoint_id)


def cleanup_endpoints():
    try:
        data_handler = DataHandler()
        try:
            dead_endpoints = data_handler.GetDeadEndpoints()
            for endpoint_id, dead_endpoint in dead_endpoints.items():
                try:
                    logger.info("Begin to cleanup endpoint %s", endpoint_id)
                    point = get_k8s_endpoint(dead_endpoint["id"])
                    if point is None:
                        logger.debug("Endpoint already gone %s", endpoint_id)
                        status = "stopped"
                    else:
                        delete_resp = delete_k8s_endpoint(point.metadata.name)
                        logger.info("delete_resp for endpoint is %s",
                                    delete_resp)
                        status = "stopped"
                    # we are not changing status from "pending", "pending" endpoints are planed to setup later
                    if dead_endpoint["status"] != "pending":
                        dead_endpoint["status"] = status
                    dead_endpoint["lastUpdated"] = datetime.datetime.now(
                    ).isoformat()
                    data_handler.UpdateEndpoint(dead_endpoint)
                except Exception as e:
                    logger.exception("clanup endpoint failed %s", dead_endpoint)
        except Exception as e:
            logger.exception("clean up endpoint failed")
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
            try:
                runnings = start_endpoints()

                fix_endpoints(runnings)

                # clean up endpoints for jobs which is NOT running
                cleanup_endpoints()
            except Exception:
                logger.exception("processing this round of endpoints failed")
        time.sleep(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--port",
                        "-p",
                        help="port of exporter",
                        type=int,
                        default=9205)
    args = parser.parse_args()
    setup_exporter_thread(args.port)

    Run()
