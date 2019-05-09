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

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../utils"))


def setupSshServer(jobId, username):
    bash_script = "sudo bash -c 'apt-get update && apt-get install -y openssh-server && cat /home/" + username + "/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys && service ssh restart'"
    # TODO setup reasonable timeout
    # output = k8sUtils.kubectl_exec("exec %s %s" % (jobId, " -- " + bash_script), 1)
    output = k8sUtils.kubectl_exec("exec %s %s" % (jobId, " -- " + bash_script))
    if output == "":
        raise Exception("Failed to setup ssh server in container. JobId: %s " % jobId)
    # TODO return ssh port, need to handle HostNetwork
    return 22


def getK8sEndpoint(endpointDescriptionPath):
    endpointDescriptionPath = os.path.join(config["storage-mount-path"], endpointDescriptionPath)
    return k8sUtils.kubectl_exec("get -o json -f %s" % endpointDescriptionPath)


def generateNodePortService(jobId, endpointName, endpointPort):
    # TODO need to handle HostNetwork
    endpointDescription = """kind: Service
apiVersion: v1
metadata:
  name: {0}-{1}
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
    port: 8022
""".format(jobId, endpointName, endpointPort)
    print("endpointDescription: %s" % endpointDescription)
    return endpointDescription


def createNodePort(endpoint, sshPort):
    endpointDescription = generateNodePortService(endpoint["jobId"], endpoint["name"], sshPort)
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
    print("Processing endpoint: %s" % (endpoint))

    # setup ssh server
    sshPort = setupSshServer(endpoint["jobId"], endpoint["username"])

    # create NodePort for ssh
    createNodePort(endpoint, sshPort)


def Run():
    while True:
        try:
            dataHandler = DataHandler()
            pendingEndpoints = dataHandler.GetPendingEndpoints()
            for _, endpoint in pendingEndpoints.items():
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
