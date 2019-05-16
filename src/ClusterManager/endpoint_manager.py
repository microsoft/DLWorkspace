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

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../utils"))


def isSshServerReady(pod_name):
    bash_script = "sudo service ssh status"
    output = k8sUtils.kubectl_exec("exec %s %s" % (pod_name, " -- " + bash_script))
    if output == "":
        return False
    return True


def querySshPort(pod_name):
    bash_script = "grep ^Port /etc/ssh/sshd_config | cut -d' ' -f2"
    ssh_port = k8sUtils.kubectl_exec("exec %s %s" % (pod_name, " -- " + bash_script))
    return int(ssh_port)


def setupSshServer(pod_name, username, host_network=False):
    '''Setup the ssh server in container, and return the listening port.'''
    bash_script = "sudo bash -c 'apt-get update && apt-get install -y openssh-server && cat /home/" + username + "/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys && service ssh restart'"

    ssh_port = 22

    # modify the script for HostNewtork
    if host_network:
        ssh_port = random.randint(40001, 49999)
        # bash_script = "sed -i '/^Port 22/c Port "+str(ssh_port)+"' /etc/ssh/sshd_config && "+bash_script
        bash_script = "sudo bash -c 'apt-get update && apt-get install -y openssh-server && sed -i \"s/^Port 22/c Port "+str(ssh_port)+"/\" /etc/ssh/sshd_config && cat /home/" + username + "/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys && service ssh restart'"

    # TODO setup reasonable timeout
    # output = k8sUtils.kubectl_exec("exec %s %s" % (jobId, " -- " + bash_script), 1)
    output = k8sUtils.kubectl_exec("exec %s %s" % (pod_name, " -- " + bash_script))
    if output == "":
        raise Exception("Failed to setup ssh server in container. JobId: %s " % pod_name)
    return ssh_port


def getK8sEndpoint(endpointDescriptionPath):
    endpointDescriptionPath = os.path.join(config["storage-mount-path"], endpointDescriptionPath)
    return k8sUtils.kubectl_exec("get -o json -f %s" % endpointDescriptionPath)


def generateNodePortService(job_id, pod_name, endpoint_id, name, target_port):
    endpointDescription = """kind: Service
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
    print("endpointDescription: %s" % endpointDescription)
    return endpointDescription


def createNodePort(endpoint):
    endpointDescription = generateNodePortService(endpoint["jobId"], endpoint["podName"], endpoint["id"], endpoint["name"], endpoint["port"])
    endpointDescriptionPath = os.path.join(config["storage-mount-path"], endpoint["endpointDescriptionPath"])
    print("endpointDescriptionPath: %s" % endpointDescriptionPath)
    with open(endpointDescriptionPath, 'w') as f:
        f.write(endpointDescription)

    result = k8sUtils.kubectl_create(endpointDescriptionPath)
    if result == "":
        raise Exception("Failed to create NodePort for ssh. JobId: %s " % endpoint["jobId"])

    print("Submitted endpoint %s to k8s, returned with status %s" % (endpoint["jobId"], result))


def startEndpoint(endpoint):
    # pending, running, stopped
    print("Starting endpoint: %s" % (endpoint))

    # podName
    pod_name = endpoint["podName"]

    # setup ssh server only is the ssh server is not up
    if not isSshServerReady(pod_name):
        print("Ssh server is not ready for pod: %s. Setup ..." % pod_name)
        ssh_port = setupSshServer(pod_name, endpoint["username"], endpoint["hostNetwork"])
    else:
        ssh_port = querySshPort(pod_name)
    endpoint["port"] = ssh_port

    print("Ssh server is ready for pod: %s. Ssh listen on %s" % (pod_name, ssh_port))

    # create NodePort
    createNodePort(endpoint)


def start_endpoints():
    try:
        dataHandler = DataHandler()
        pending_endpoints = dataHandler.GetPendingEndpoints()
        for _, endpoint in pending_endpoints.items():
            print("\n\n\n\n\n\n----------------Begin to start endpoint %s" % endpoint["id"])
            output = getK8sEndpoint(endpoint["endpointDescriptionPath"])
            if(output != ""):
                endpointDescription = json.loads(output)
                endpoint["endpointDescription"] = endpointDescription
                endpoint["status"] = "running"
            else:
                startEndpoint(endpoint)

            endpoint["lastUpdated"] = datetime.datetime.now().isoformat()
            dataHandler = DataHandler()
            dataHandler.UpdateEndpoint(endpoint)
    except Exception as e:
        traceback.print_exc()
    finally:
        pass


def cleanup_endpoints():
    try:
        dataHandler = DataHandler()
        dead_endpoints = dataHandler.GetDeadEndpoints()
        for endpoint_id, dead_endpoint in dead_endpoints.items():
            print("\n\n\n\n\n\n----------------Begin to cleanup endpoint %s" % endpoint_id)
            endpointDescriptionPath = os.path.join(config["storage-mount-path"], dead_endpoint["endpointDescriptionPath"])
            still_running = getK8sEndpoint(endpointDescriptionPath)
            # empty mean not existing
            if still_running == "":
                print("Endpoint already gone %s" % endpoint_id)
                status = "stopped"
            else:
                output = k8sUtils.kubectl_delete(endpointDescriptionPath)
                # 0 for success
                if output == 0:
                    status = "stopped"
                    print("Succeed cleanup endpoint %s" % endpoint_id)
                else:
                    print("Clean dead endpoint %s failed, endpoints: %s" % (endpoint_id, dead_endpoint))

            dead_endpoint["status"] = status
            dead_endpoint["lastUpdated"] = datetime.datetime.now().isoformat()
            dataHandler = DataHandler()
            dataHandler.UpdateEndpoint(dead_endpoint)
    except Exception as e:
        traceback.print_exc()
    finally:
        pass


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
