from config import config, GetStoragePath, GetWorkPath
import k8sUtils
from DataHandler import DataHandler
import json
import os
import time
import sys
import datetime
import copy
import base64
import traceback
import random
import re

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../utils"))


def is_ssh_server_ready(pod_name):
    bash_script = "sudo service ssh status"
    output = k8sUtils.kubectl_exec("exec %s %s" % (pod_name, " -- " + bash_script))
    if output == "":
        return False
    return True


def query_ssh_port(pod_name):
    bash_script = "grep ^Port /etc/ssh/sshd_config | cut -d' ' -f2"
    ssh_port = k8sUtils.kubectl_exec("exec %s %s" % (pod_name, " -- " + bash_script))
    return int(ssh_port)


def start_ssh_server(pod_name, user_name, host_network=False, ssh_port=22):
    '''Setup the ssh server in container, and return the listening port.'''
    bash_script = "sudo bash -c 'apt-get update && apt-get install -y openssh-server && cd /home/" + user_name + " && (chown " + user_name + " -R .ssh; chmod 600 -R .ssh/*; chmod 700 .ssh; true) && service ssh restart'"

    # ssh_port = 22

    # modify the script for HostNewtork
    if host_network:
        # if the ssh_port is default value 22, randomly choose one
        if ssh_port == 22:
            ssh_port = random.randint(40000, 49999)
        # bash_script = "sed -i '/^Port 22/c Port "+str(ssh_port)+"' /etc/ssh/sshd_config && "+bash_script
        # TODO refine the script later
        bash_script = "sudo bash -c 'apt-get update && apt-get install -y openssh-server && sed -i \"s/^Port 22/Port " + str(ssh_port) + "/\" /etc/ssh/sshd_config && cd /home/" + user_name + " && (chown " + user_name + " -R .ssh; chmod 600 -R .ssh/*; chmod 700 .ssh; true) && service ssh restart'"

    # TODO setup reasonable timeout
    # output = k8sUtils.kubectl_exec("exec %s %s" % (jobId, " -- " + bash_script), 1)
    output = k8sUtils.kubectl_exec("exec %s %s" % (pod_name, " -- " + bash_script))
    if output == "":
        raise Exception("Failed to setup ssh server in container. JobId: %s " % pod_name)
    return ssh_port


def get_k8s_endpoint(endpoint_description_path):
    endpoint_description_path = os.path.join(config["storage-mount-path"], endpoint_description_path)
    return k8sUtils.kubectl_exec("get -o json -f %s" % endpoint_description_path)


def generate_node_port_service(job_id, pod_name, endpoint_id, name, target_port):
    endpoint_description = """kind: Service
apiVersion: v1
metadata:
  name: {2}
  labels:
    run: {0}
    jobId: {0}
    podName: {1}
spec:
  type: NodePort
  selector:
    podName: {1}
  ports:
  - name: {3}
    protocol: "TCP"
    targetPort: {4}
    port: {4}
""".format(job_id, pod_name, endpoint_id, name, target_port)
    print("endpointDescription: %s" % endpoint_description)
    return endpoint_description


def create_node_port(endpoint):
    endpoint_description = generate_node_port_service(endpoint["jobId"], endpoint["podName"], endpoint["id"], endpoint["name"], endpoint["podPort"])
    endpoint_description_path = os.path.join(config["storage-mount-path"], endpoint["endpointDescriptionPath"])
    print("endpointDescriptionPath: %s" % endpoint_description_path)
    with open(endpoint_description_path, 'w') as f:
        f.write(endpoint_description)

    result = k8sUtils.kubectl_create(endpoint_description_path)
    if result == "":
        raise Exception("Failed to create NodePort for ssh. JobId: %s " % endpoint["jobId"])

    print("Submitted endpoint %s to k8s, returned with status %s" % (endpoint["jobId"], result))


def setup_ssh_server(user_name, pod_name, host_network=False):
    '''Setup ssh server on pod and return the port'''
    # setup ssh server only is the ssh server is not up
    if not is_ssh_server_ready(pod_name):
        print("Ssh server is not ready for pod: %s. Setup ..." % pod_name)
        ssh_port = start_ssh_server(pod_name, user_name, host_network)
    else:
        ssh_port = query_ssh_port(pod_name)
    print("Ssh server is ready for pod: %s. Ssh listen on %s" % (pod_name, ssh_port))
    return ssh_port


def setup_jupyter_server(user_name, pod_name):

    jupyter_port = random.randint(40000, 49999)
    bash_script = "sudo bash -c 'export DEBIAN_FRONTEND=noninteractive; apt-get update && apt-get install -y python3-pip && python3 -m pip install --upgrade pip && python3 -m pip install jupyter && cd /home/" + user_name + " && runuser -l " + user_name + " -c \"jupyter notebook --no-browser --ip=0.0.0.0 --NotebookApp.token= --port=" + str(jupyter_port) + " &>/dev/null &\"'"
    output = k8sUtils.kubectl_exec("exec %s %s" % (pod_name, " -- " + bash_script))
    if output == "":
        raise Exception("Failed to start jupyter server in container. JobId: %s " % pod_name)
    return jupyter_port


def setup_tensorboard(user_name, pod_name):
    tensorboard_port = random.randint(40000, 49999)
    bash_script = "sudo bash -c 'export DEBIAN_FRONTEND=noninteractive; pip install tensorboard; runuser -l " + user_name + " -c \"mkdir -p ~/tensorboard/\${DLWS_JOB_ID}/logs; nohup tensorboard --logdir=~/tensorboard/\${DLWS_JOB_ID}/logs --port=" + str(tensorboard_port) + " &>/dev/null &\"'"
    output = k8sUtils.kubectl_exec("exec %s %s" % (pod_name, " -- " + bash_script))
    if output == "":
        raise Exception("Failed to start tensorboard in container. JobId: %s " % pod_name)
    return tensorboard_port


def start_endpoint(endpoint):
    # pending, running, stopped
    print("Starting endpoint: %s" % (endpoint))

    # podName
    pod_name = endpoint["podName"]
    user_name = endpoint["username"]
    host_network = endpoint["hostNetwork"]

    port_name = endpoint["name"]
    if port_name == "ssh":
        endpoint["podPort"] = setup_ssh_server(user_name, pod_name, host_network)
    elif port_name == "ipython":
        endpoint["podPort"] = setup_jupyter_server(user_name, pod_name)
    elif port_name == "tensorboard":
        endpoint["podPort"] = setup_tensorboard(user_name, pod_name)
    else:
        endpoint["podPort"] = int(endpoint["podPort"])

    # create NodePort
    create_node_port(endpoint)


def is_user_ready(pod_name):
    bash_script = "bash -c 'ls /dlws/USER_READY'"
    output = k8sUtils.kubectl_exec("exec %s %s" % (pod_name, " -- " + bash_script))
    if output == "":
        return False
    return True


def start_endpoints():
    try:
        try:
            data_handler = DataHandler()
            pending_endpoints = data_handler.GetPendingEndpoints()

            for endpoint_id, endpoint in pending_endpoints.items():
                job = data_handler.GetJob(jobId=endpoint["jobId"])[0]
                if job["jobStatus"] != "running":
                    continue
                if not is_user_ready(endpoint["podName"]):
                    continue

                # get endpointDescriptionPath
                # job["jobDescriptionPath"] = "jobfiles/" + time.strftime("%y%m%d") + "/" + jobParams["jobId"] + "/" + jobParams["jobId"] + ".yaml"
                endpoint_description_dir = re.search("(.*/)[^/\.]+.yaml", job["jobDescriptionPath"]).group(1)
                endpoint["endpointDescriptionPath"] = os.path.join(endpoint_description_dir, endpoint_id + ".yaml")

                print("\n\n\n\n\n\n----------------Begin to start endpoint %s" % endpoint["id"])
                output = get_k8s_endpoint(endpoint["endpointDescriptionPath"])
                if(output != ""):
                    endpoint_description = json.loads(output)
                    endpoint["endpointDescription"] = endpoint_description
                    endpoint["status"] = "running"
                    pod = k8sUtils.GetPod("podName=" + endpoint["podName"])
                    if "items" in pod and len(pod["items"]) > 0:
                        endpoint["nodeName"] = pod["items"][0]["spec"]["nodeName"]
                else:
                    start_endpoint(endpoint)

                endpoint["lastUpdated"] = datetime.datetime.now().isoformat()
                data_handler.UpdateEndpoint(endpoint)
        except Exception as e:
            traceback.print_exc()
    except Exception as e:
        traceback.print_exc()


def cleanup_endpoints():
    try:
        data_handler = DataHandler()
        try:
            dead_endpoints = data_handler.GetDeadEndpoints()
            for endpoint_id, dead_endpoint in dead_endpoints.items():
                print("\n\n\n\n\n\n----------------Begin to cleanup endpoint %s" % endpoint_id)
                endpoint_description_path = os.path.join(config["storage-mount-path"], dead_endpoint["endpointDescriptionPath"])
                still_running = get_k8s_endpoint(endpoint_description_path)
                # empty mean not existing
                if still_running == "":
                    print("Endpoint already gone %s" % endpoint_id)
                    status = "stopped"
                else:
                    output = k8sUtils.kubectl_delete(endpoint_description_path)
                    # 0 for success
                    if output == 0:
                        status = "stopped"
                        print("Succeed cleanup endpoint %s" % endpoint_id)
                    else:
                        # TODO will need to clean it up eventually
                        status = "unknown"
                        print("Clean dead endpoint %s failed, endpoints: %s" % (endpoint_id, dead_endpoint))

                dead_endpoint["status"] = status
                dead_endpoint["lastUpdated"] = datetime.datetime.now().isoformat()
                data_handler.UpdateEndpoint(dead_endpoint)
        except Exception as e:
            traceback.print_exc()
        finally:
            data_handler.Close()
    except Exception as e:
        traceback.print_exc()


def Run():
    while True:
        # start endpoints
        start_endpoints()
        time.sleep(1)

        # clean up endpoints for jobs which is NOT running
        cleanup_endpoints()
        time.sleep(1)


if __name__ == '__main__':
    Run()
