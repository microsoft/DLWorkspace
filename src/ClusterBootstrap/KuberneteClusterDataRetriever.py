#!/usr/bin/python
import json
import os
import subprocess
import argparse
import sys
import textwrap
import time
import datetime
from HostStatus import HostStatus
from ServiceStatus import ServiceStatus

class KuberneteClusterDataRetriever:
    # kubectl_prog: location of kubectl program
    # kube_masternode: DNS/IP of the kubenete master node
    # kubectl_opt: option of kubectl, including server & certificate information
    def __init__(self, kubectl_prog, kube_masternode, kubectl_opt, hostStatusPerMachineMap, verbose = False):
        self.verbose = verbose
        self.kubectl_prog = kubectl_prog
        self.kube_masternode = kube_masternode
        self.kubectl_opt = kubectl_opt
        self.hostStatusPerMachineMap = hostStatusPerMachineMap

    # Parse python dictionary dic for a particular entry (usually the dictionary is parsed from JSON/YAML)
    # E.g., entry: ["metadata", "name"] will first parse dictionary entry "metadata", within that 
    # entry, "name" is parsed
    def fetch_dictionary(self, dic, entry):
        if isinstance(entry, list):
            if self.verbose:
                print("Fetch " + str(dic) + "@" + str(entry) + "==" + str( dic[entry[0]] )) 
            if isinstance( dic, list ):
                for subdic in dic:
                    if entry[0] in subdic:
                        if len(entry)<=1:
                            return subdic[entry[0]]
                        else:
                            return self.fetch_dictionary(subdic[entry[0]], entry[1:])
                return None
            elif entry[0] in dic:
                if len(entry)<=1:
                    return dic[entry[0]]
                else:
                    return self.fetch_dictionary(dic[entry[0]], entry[1:])
            else:
                return None
        else:
            print("fetch_config expects to take a list, but gets " + str(entry))

    # Run a kubenete command, parse the output in json
    def run_kubectl( self, command ):
        if os.path.isfile(self.kubectl_prog):
            if self.kube_masternode is None:
                run_command = self.kubectl_prog + " " + self.kubectl_opt + " " + command
            else:
                run_command = self.kubectl_prog + (" --server https://%s:8443/ " %self.kube_masternode) + self.kubectl_opt + " " + command
            try:
                print(run_command)
                kubectl_output = subprocess.check_output(run_command, shell=True)
                kubectl_ctl_json = json.loads(kubectl_output)
                return kubectl_ctl_json
            except subprocess.CalledProcessError as e:
                print("kubectl failed, code %d" % (e.returncode))
                return {}
        else:
            return {}
    
    # List all current kubenete namespaces used. 
    def get_namespaces( self ): 
        namespaces_json = self.run_kubectl("get namespaces -o json")
        namespaces = []
        items = self.fetch_dictionary( namespaces_json, ["items"])
        if not items is None:
            for item in items:
                if item["kind"]=="Namespace":
                    namespace = self.fetch_dictionary( item, ["metadata", "name"])
                    if not namespace is None:
                        namespaces.append(namespace)
        if self.verbose:
            print("Kubernete Namespace: " + str(namespaces))
        return namespaces
    
    # list all pods in a certain namespace
    def get_pods( self ):
        pods_json = self.run_kubectl("get pods -o json --all-namespaces")
        return pods_json
    
    # Translate Kubernete state to fleet state
    def translate_state( self, pod_status, container_state, restart_count):
        if pod_status == "Running" or pod_status=="Succeeded":
            return "active"
        elif pod_status == "Pending" or pod_status=="Failed":
            return "inactive"
        else:
            return "Unknown"

    # Translate Kubernete state to fleet loadState
    def translate_loadstate( self, pod_status, container_state, restart_count):
        return container_state
    
    # Translate Kubernete state to fleet substate
    def translate_substate( self, pod_status, container_state, restart_count):
        if pod_status == "Running" or pod_status=="Succeeded":
            return "running"
        elif pod_status == "Pending":
            return "inactive"
        elif pod_status == "Failed":
            return "dead"

    # assemble hostStatusPerMachineMap
    def retrieve(self):
        #namespaces = self.get_namespaces()
        if True:
            pod_json = self.get_pods( )
            if "items" in pod_json:
                for one_pod in pod_json["items"]:
                    pod_name = self.fetch_dictionary( one_pod, [ "metadata", "generateName"])
                    if pod_name is None: 
                        pod_name = self.fetch_dictionary( one_pod, [ "metadata", "name"] )
                    else:
                        pod_name = pod_name[:-1]
                    nodeName = self.fetch_dictionary( one_pod, [ "spec", "nodeName"] )
                    
                    if nodeName is None:
                        continue
                    # possible pod status are: "Pending", "Running", "Succeeded", "Failed", "Unknown"
                    # see https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-phase
                    pod_status = self.fetch_dictionary( one_pod, [ "status", "phase"] )
                    restart_count = self.fetch_dictionary( one_pod, [ "status", "containerStatuses", "restartCount"] )
                    container_state_dic = self.fetch_dictionary( one_pod, [ "status", "containerStatuses", "state"] )
                    if container_state_dic is None:
                        container_state = "Pending" if restart_count <=0 else "Restarting"
                    else:
                        for key in container_state_dic:
                            container_state = key
                    if self.verbose:
                        print("Node %s, pod %s, container %s (%d) " %( nodeName, pod_name,  container_state,  restart_count))
                        
                    if not nodeName in self.hostStatusPerMachineMap:
                        self.hostStatusPerMachineMap[nodeName] = HostStatus(nodeName)
                    
                    hostStatus = self.hostStatusPerMachineMap[nodeName]
                    
                    if hostStatus.services == None:
                        hostStatus.services = {}
                    
                    service_state = self.translate_state( pod_status, container_state, restart_count)
                    service_loadstate = self.translate_loadstate( pod_status, container_state, restart_count)
                    service_substate = self.translate_substate( pod_status, container_state, restart_count)
                    hostStatus.services[pod_name] = ServiceStatus( pod_name, service_state, service_loadstate, service_substate )

if __name__ == '__main__':
    kubectl_prog = "./deploy/bin/kubectl"
    kubectl_opt = ("--certificate-authority=%s --client-key=%s --client-certificate=%s" % ( "./deploy/ssl/ca/ca.pem", "./deploy/ssl/kubelet/apiserver-key.pem", "./deploy/ssl/kubelet/apiserver.pem") )
    parser = argparse.ArgumentParser( prog='KuberneteClusterDataRetriever.py',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent('''\
Test harness to retrieve kubenete service status and return it in a data structure.
   
Usage:
   KuberneteClusterDataRetriever.py kubernete_master
''') )
    parser.add_argument("-t", "--time", 
        help = "Measure the execution time by [n] times",
        action="store", 
        default=0)
    parser.add_argument("-p", "--prog", 
        help = "Kubectl program",
        action="store", 
        default=kubectl_prog)
    parser.add_argument("-o", "--opt", 
        help = "Kubectl program option",
        action="store", 
        default=kubectl_opt)
    parser.add_argument('nargs', nargs=argparse.REMAINDER, 
        help="Additional command argument", 
        )
    args = parser.parse_args()
    kubectl_prog = args.prog
    kubectl_opt = args.opt
    nargs = args.nargs
    if len(nargs)>=1:
        kube_masternode = nargs[0]
    else:
        kube_masternode = None
    
    hostStatusPerMachineMap = {}
    retriever = KuberneteClusterDataRetriever(kubectl_prog, kube_masternode, kubectl_opt, hostStatusPerMachineMap)

    inprepeat = int(args.time)
    repeat = 1 if inprepeat<=0 else inprepeat
    time0 = time.time()
    timing = []
    for i in range(repeat):
        hostStatusPerMachineMap.clear()
        retriever.retrieve()
        if inprepeat<=0:
            for node in hostStatusPerMachineMap:
                print("Node %s" % node)
                hostStatus = hostStatusPerMachineMap[node].services
                for service in hostStatus:
                    print("  Service: %s, state: %s" % ( service, hostStatus[service].state ))
        time1 = time.time()
        timing.append(time1-time0)
        time0 = time1
    if args.time >= 1:
        print("Execution time: " + str(timing))
