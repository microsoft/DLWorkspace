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


def isSshServerReady(pod_id):
    bash_script = "sudo service ssh status"
    output = k8sUtils.kubectl_exec("exec %s %s" % (pod_id, " -- " + bash_script))
    if output == "":
        return False
    return True


def querySshPort(pod_id):
    bash_script = "grep ^Port /etc/ssh/sshd_config | cut -d' ' -f2"
    ssh_port = k8sUtils.kubectl_exec("exec %s %s" % (pod_id, " -- " + bash_script))
    return int(ssh_port)


def setupSshServer(pod_id, username, host_network=False):
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
    output = k8sUtils.kubectl_exec("exec %s %s" % (pod_id, " -- " + bash_script))
    if output == "":
        raise Exception("Failed to setup ssh server in container. JobId: %s " % pod_id)
    return ssh_port


def getK8sEndpoint(endpointDescriptionPath):
    endpointDescriptionPath = os.path.join(config["storage-mount-path"], endpointDescriptionPath)
    return k8sUtils.kubectl_exec("get -o json -f %s" % endpointDescriptionPath)


def generateNodePortService(jobId, endpoint_id, name, targetPort):
    endpointDescription = """kind: Service
apiVersion: v1
metadata:
  name: {3}-{1}
  labels:
    run: {0}
    jobId: {0}
    # podName: tutorial-pytorch
spec:
  type: NodePort
  selector:
    podName: {0}
  ports:
  - name: {1}
    protocol: "TCP"
    targetPort: {2}
    port: {2}
""".format(jobId, name, targetPort, endpoint_id)
    print("endpointDescription: %s" % endpointDescription)
    return endpointDescription


def createNodePort(endpoint, sshPort):
    endpointDescription = generateNodePortService(endpoint["jobId"], endpoint["id"], endpoint["name"], sshPort)
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

    # podId
    pod_id = endpoint["podId"]

    # setup ssh server only is the ssh server is not up
    if not isSshServerReady(pod_id):
        print("Ssh server is not ready for pod: %s. Setup ..." % pod_id)
        ssh_port = setupSshServer(pod_id, endpoint["username"], endpoint["hostNetwork"])
    else:
        ssh_port = querySshPort(pod_id)

    print("Ssh server is ready for pod: %s. Ssh listen on %s" % (pod_id, ssh_port))

    # create NodePort for ssh
    createNodePort(endpoint, ssh_port)


def Run():
    while True:
        try:
            dataHandler = DataHandler()
            pendingEndpoints = dataHandler.GetPendingEndpoints()
            for _, endpoint in pendingEndpoints.items():
                print("\n\n\n\n\n\n----------------Begin to process endpoint %s" % endpoint["id"])
                output = getK8sEndpoint(endpoint["endpointDescriptionPath"])
                if(output != ""):
                    endpointDescription = json.loads(output)
                    endpoint["endpointDescription"] = endpointDescription
                    endpoint["status"] = "running"
                else:
                    startEndpoint(endpoint)

                endpoint["last_updated"] = datetime.datetime.now().isoformat()
                dataHandler = DataHandler()
                dataHandler.UpdateEndpoint(endpoint)
        except Exception as e:
            traceback.print_exc()
        finally:
            pass

        time.sleep(1)


if __name__ == '__main__':
    Run()
