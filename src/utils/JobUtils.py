import json
import os
import time
import argparse
import uuid
import subprocess
import sys
from jobs_tensorboard import GenTensorboardMeta

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../storage"))
from gen_pv_pvc import GenStorageClaims, GetStoragePath

import yaml
from jinja2 import Environment, FileSystemLoader, Template
from config import config
from DataHandler import DataHandler
import base64


def LoadJobParams(jobParamsJsonStr):
    return json.loads(jobParamsJsonStr)

def kubectl_create(jobfile,EXEC=True):
    if EXEC:
        try:
            output = subprocess.check_output(["bash","-c", config["kubelet-path"] + " create -f " + jobfile])
        except Exception as e:
            print e
            output = ""
    else:
        output = "Job " + jobfile + " is not submitted to kubernetes cluster"
    return output

def kubectl_exec(params):
    try:
        output = subprocess.check_output(["bash","-c", config["kubelet-path"] + " " + params])
    except Exception as e:
        print e
        output = ""
    return output

def cmd_exec(cmdStr):
    try:
        output = subprocess.check_output(["bash","-c", cmdStr])
    except Exception as e:
        print e
        output = ""
    return output

def SubmitRegularJob(jobParamsJsonStr):
    jobParams = LoadJobParams(jobParamsJsonStr)
    print jobParamsJsonStr

    dataHandler = DataHandler()

    if "id" not in jobParams or jobParams["id"] == "":
        #jobParams["id"] = jobParams["job-name"] + "-" + str(uuid.uuid4()) 
        # ToDo: Job ID is a combination of job-name and time.time(). Will that be enough to guarantee the job id to be unique?
        #     may be it will be helpful to add str(uuid.uuid4()) to the end of job ID?
        jobParams["id"] = jobParams["job-name"] + "-" + str(time.time())
    jobParams["id"] = jobParams["id"].replace("_","-").replace(".","-")

    if "cmd" not in jobParams:
        jobParams["cmd"] = ""
    if isinstance(jobParams["cmd"], basestring) and not jobParams["cmd"] == "":
        jobParams["cmd"] = "[\"" + jobParams["cmd"].replace(" ","\",\"") + "\"]"


    jobParams["pvc_job"] = "jobs-"+jobParams["id"]
    jobParams["pvc_work"] = "work-"+jobParams["id"]
    jobParams["pvc_data"] = "storage-"+jobParams["id"]
  

    if "job-path" in jobParams and len(jobParams["jobParams"].strip()) > 0: 
        jobPath = jobParams["job-path"]
    else:
        jobPath = time.strftime("%y%m%d")+"/"+jobParams["id"]

    if "work-path" not in jobParams or len(jobParams["work-path"].strip()) == 0: 
        raise Exception("ERROR: work-path cannot be empty")

    if "data-path" not in jobParams or len(jobParams["data-path"].strip()) == 0: 
        raise Exception("ERROR: data-path cannot be empty")


    jobPath,workPath,dataPath = GetStoragePath(jobPath,jobParams["work-path"],jobParams["data-path"])


    localJobPath = os.path.join(config["storage-mount-path"],jobPath)
    if not os.path.exists(localJobPath):
        os.makedirs(localJobPath)

    jobDir = os.path.join(os.path.dirname(config["storage-mount-path"]), "jobfiles")
    if not os.path.exists(jobDir):
        os.mkdir(jobDir)

    jobDir = os.path.join(jobDir,time.strftime("%y%m%d"))
    if not os.path.exists(jobDir):
        os.mkdir(jobDir)

    jobDir = os.path.join(jobDir,jobParams["id"])
    if not os.path.exists(jobDir):
        os.mkdir(jobDir)

    jobFilePath = os.path.join(jobDir, jobParams["id"]+".yaml")    

    ENV = Environment(loader=FileSystemLoader("/"))

    jobTempDir = os.path.join(config["root-path"],"Jobs_Templete")
    jobTemp= os.path.join(jobTempDir, "RegularJob.yaml.template")


    template = ENV.get_template(os.path.abspath(jobTemp))
    job_meta = template.render(job=jobParams)




    pv_meta_j,pvc_meta_j = GenStorageClaims(jobParams["pvc_job"],jobPath)
    pv_meta_u,pvc_meta_u = GenStorageClaims(jobParams["pvc_work"],workPath)
    pv_meta_d,pvc_meta_d = GenStorageClaims(jobParams["pvc_data"],dataPath)


    jobMetaList = []
    jobMetaList.append(pv_meta_j)
    jobMetaList.append(pvc_meta_j)
    jobMetaList.append(pv_meta_u)
    jobMetaList.append(pvc_meta_u)
    jobMetaList.append(pv_meta_d)
    jobMetaList.append(pvc_meta_d)
    jobMetaList.append(job_meta)



    if "interactive-port" in jobParams and len(jobParams["interactive-port"].strip()) > 0:
        jobParams["svc-name"] = "interactive-"+jobParams["id"]
        jobParams["app-name"] = jobParams["id"]
        jobParams["port"] = jobParams["interactive-port"]
        jobParams["port-name"] = "interactive"
        jobParams["port-type"] = "TCP"

        serviceTemplate = ENV.get_template(os.path.join(jobTempDir,"KubeSvc.yaml.template"))

        template = ENV.get_template(serviceTemplate)
        interactiveMeta = template.render(svc=jobParams)
        jobMetaList.append(interactiveMeta)


    jobMeta = "\n---\n".join(jobMetaList)


    with open(jobFilePath, 'w') as f:
        f.write(jobMeta)
    ret={}

    output = kubectl_create(jobFilePath)    
    #if output == "job \""+jobParams["id"]+"\" created\n":
    #    ret["result"] = "success"
    #else:
    #    ret["result"]  = "fail"


    ret["output"] = output
    
    ret["id"] = jobParams["id"]


    if "logdir" in jobParams and len(jobParams["logdir"].strip()) > 0:
        tensorboardParams = jobParams.copy()
        tensorboardParams["svc-name"] = "tensorboard-"+jobParams["id"]
        tensorboardParams["app-name"] = "tensorboard-"+jobParams["id"]
        tensorboardParams["port"] = "6006"
        tensorboardParams["port-name"] = "tensorboard"
        tensorboardParams["port-type"] = "TCP"        
        tensorboardParams["tensorboard-id"] = "tensorboard-"+jobParams["id"]
        
        tensorboardParams["id"] = tensorboardParams["svc-name"]
        tensorboardParams["job-name"] = tensorboardParams["svc-name"]
        tensorboardMeta = GenTensorboardMeta(tensorboardParams, os.path.join(jobTempDir,"KubeSvc.yaml.template"), os.path.join(jobTempDir,"TensorboardApp.yaml.template"))

        tensorboardMetaFilePath = os.path.join(jobDir, tensorboardParams["id"]+".yaml")

        with open(tensorboardMetaFilePath, 'w') as f:
            f.write(tensorboardMeta)
        output = kubectl_create(tensorboardMetaFilePath)
        tensorboardMetaFilePath["job-meta-path"] = tensorboardMetaFilePath
        tensorboardMetaFilePath["job-meta"] = base64.b64encode(tensorboardMeta)
        if "user-id" not in tensorboardMetaFilePath:
            tensorboardMetaFilePath["user-id"] = ""
        dataHandler.AddJob(tensorboardMetaFilePath)

    jobParams["job-meta-path"] = jobFilePath
    jobParams["job-meta"] = base64.b64encode(jobMeta)
    if "user-id" not in jobParams:
        jobParams["user-id"] = ""

    dataHandler.AddJob(jobParams)

    return ret


def SubmitDistJob(jobParamsJsonStr,tensorboard=False):
    

    jobTempDir = os.path.join(config["root-path"],"Jobs_Templete")
    workerJobTemp= os.path.join(jobTempDir, "DistTensorFlow_worker.yaml.template")
    psJobTemp= os.path.join(jobTempDir, "DistTensorFlow_ps.yaml.template")

    jobParams = LoadJobParams(jobParamsJsonStr)
    if "id" not in jobParams or jobParams["id"] == "":
        #jobParams["id"] = jobParams["job-name"] + "-" + str(uuid.uuid4()) 
        jobParams["id"] = jobParams["job-name"] + "-" + str(time.time())
    jobParams["id"] = jobParams["id"].replace("_","-").replace(".","-")

    if "cmd" not in jobParams:
        jobParams["cmd"] = ""


    if "job-path" in jobParams and len(jobParams["jobParams"].strip()) > 0: 
        jobPath = jobParams["job-path"]
    else:
        jobPath = time.strftime("%y%m%d")+"/"+jobParams["id"]

    if "work-path" not in jobParams or len(jobParams["work-path"].strip()) == 0: 
        raise Exception("ERROR: work-path cannot be empty")

    if "data-path" not in jobParams or len(jobParams["data-path"].strip()) == 0: 
        raise Exception("ERROR: data-path cannot be empty")


    if "worker-num" not in jobParams:
        raise Exception("ERROR: unknown number of workers")
    if "ps-num" not in jobParams:
        raise Exception("ERROR: unknown number of parameter servers")

    numWorker = int(jobParams["worker-num"])
    numPs = int(jobParams["ps-num"])

    jobPath,workPath,dataPath = GetStoragePath(jobPath,jobParams["work-path"],jobParams["data-path"])

    localJobPath = os.path.join(config["storage-mount-path"],jobPath)

    if not os.path.exists(localJobPath):
        os.makedirs(localJobPath)

    jobDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "jobfiles")
    if not os.path.exists(jobDir):
        os.mkdir(jobDir)

    jobDir = os.path.join(jobDir,time.strftime("%y%m%d"))
    if not os.path.exists(jobDir):
        os.mkdir(jobDir)

    jobDir = os.path.join(jobDir,jobParams["id"])
    if not os.path.exists(jobDir):
        os.mkdir(jobDir)

    jobFilePath = os.path.join(jobDir, jobParams["id"]+".yaml")    

    ENV = Environment(loader=FileSystemLoader("/"))


    jobTempList= []
    workerHostList = []
    psHostList = []
    for i in range(numWorker):
        workerHostList.append(jobParams["id"]+"-worker"+str(i)+":2222")


    for i in range(numPs):
        psHostList.append(jobParams["id"]+"-ps"+str(i)+":2222")


    workerHostStr = ",".join(workerHostList)
    psHostStr = ",".join(psHostList)

    cmdStr = jobParams["cmd"]


    jobParams["pvc_job"] = "jobs-"+jobParams["id"]
    jobParams["pvc_work"] = "work-"+jobParams["id"]
    jobParams["pvc_data"] = "storage-"+jobParams["id"]


    pv_meta_j,pvc_meta_j = GenStorageClaims(jobParams["pvc_job"],jobPath)
    pv_meta_u,pvc_meta_u = GenStorageClaims(jobParams["pvc_work"],workPath)
    pv_meta_d,pvc_meta_d = GenStorageClaims(jobParams["pvc_data"],dataPath)

    jobTempList.append(pv_meta_j)
    jobTempList.append(pvc_meta_j)
    jobTempList.append(pv_meta_u)
    jobTempList.append(pvc_meta_u)
    jobTempList.append(pv_meta_d)
    jobTempList.append(pvc_meta_d)

    for i in range(numWorker):
        jobParams["worker-id"]=str(i)

        cmdList = cmdStr.split(" ")
        cmdList.append("--worker_hosts="+workerHostStr)
        cmdList.append("--ps_hosts="+psHostStr)
        cmdList.append("--job_name=worker")
        cmdList.append("--task_index="+str(i))

        jobParams["cmd"] = "[ " + ",".join(["\""+s+"\"" for s in cmdList if len(s.strip())>0])+ " ]"

        template = ENV.get_template(os.path.abspath(workerJobTemp))
        jobTempList.append(template.render(job=jobParams))


    for i in range(numPs):
        jobParams["ps-id"]=str(i)

        cmdList = cmdStr.split(" ")
        cmdList.append("--worker_hosts="+workerHostStr)
        cmdList.append("--ps_hosts="+psHostStr)
        cmdList.append("--job_name=ps")
        cmdList.append("--task_index="+str(i))

        jobParams["cmd"] = "[ " + ",".join(["\""+s+"\"" for s in cmdList if len(s.strip())>0])+ " ]"


        template = ENV.get_template(os.path.abspath(psJobTemp))
        jobTempList.append(template.render(job=jobParams))



    jobMeta = "\n---\n".join(jobTempList)


    if "logdir" in jobParams and len(jobParams["logdir"].strip()) > 0:
        jobParams["svc-name"] = "tensorboard-"+jobParams["id"]
        jobParams["app-name"] = "tensorboard-"+jobParams["id"]
        jobParams["port"] = "6006"
        jobParams["port-name"] = "tensorboard"
        jobParams["port-type"] = "TCP"        
        jobParams["tensorboard-id"] = "tensorboard-"+jobParams["id"]

        tensorboardMeta = GenTensorboardMeta(jobParams, os.path.join(jobTempDir,"KubeSvc.yaml.template"), os.path.join(jobTempDir,"TensorboardApp.yaml.template"))

        tensorboardMetaFilePath = os.path.join(jobDir, "tensorboard-"+jobParams["id"]+".yaml")

        with open(tensorboardMetaFilePath, 'w') as f:
            f.write(tensorboardMeta)

        output = kubectl_create(tensorboardMetaFilePath)

    with open(jobFilePath, 'w') as f:
        f.write(jobMeta)

    output = kubectl_create(jobFilePath)    

    ret={}
    ret["output"] = output
    ret["id"] = jobParams["id"]


    jobParams["job-meta-path"] = jobFilePath
    jobParams["job-meta"] = base64.b64encode(jobMeta)
    if "user-id" not in jobParams:
        jobParams["user-id"] = ""
    dataHandler = DataHandler()
    dataHandler.AddJob(jobParams)

    return ret


def GetJobList():
    dataHandler = DataHandler()
    jobs =  dataHandler.GetJobList()
    return jobs


def GetJob(jobId):
    dataHandler = DataHandler()
    job =  dataHandler.GetJob(jobId)
    return job

def DeleteJob(jobId):
    dataHandler = DataHandler()
    jobs =  dataHandler.GetJob(jobId)
    if len(jobs) == 1:
        kubectl_exec(" delete -f "+jobs[0]["job_meta_path"])
        dataHandler.DelJob(jobId)
    return


def Split(text,spliter):
    return [x for x in text.split(spliter) if len(x.strip())>0]

def GetServiceAddress(jobId):
    ret = []

    output = kubectl_exec(" describe svc -l run="+jobId)
    svcs = output.split("\n\n\n")
    
    for svc in svcs:
        lines = [Split(x,"\t") for x in Split(svc,"\n")]
        port = None
        nodeport = None
        selector = None
        hostIP = None

        for line in lines:
            if len(line) > 1:
                if line[0] == "Port:":
                    port = line[-1]
                    if "/" in port:
                        port = port.split("/")[0]
                if line[0] == "NodePort:":
                    nodeport = line[-1]
                    if "/" in nodeport:
                        nodeport = nodeport.split("/")[0]

                if line[0] == "Selector:" and line[1] != "<none>":
                    selector = line[-1]

        if selector is not None:
            podInfo = GetPod(selector)
            if podInfo is not None and "items" in podInfo:
                for item in podInfo["items"]:
                    if "status" in item and "hostIP" in item["status"]:
                        hostIP = item["status"]["hostIP"]
        if port is not None and hostIP is not None and nodeport is not None:
            ret.append( (port,hostIP,nodeport))
    return ret


def GetTensorboard(jobId):
    output = kubectl_exec(" describe svc tensorboard-"+jobId)
    lines = [Split(x,"\t") for x in Split(output,"\n")]
    port = None
    nodeport = None
    selector = None
    hostIP = None

    for line in lines:
        if len(line) > 1:
            if line[0] == "Port:":
                port = line[-1]
                if "/" in port:
                    port = port.split("/")[0]
            if line[0] == "NodePort:":
                nodeport = line[-1]
                if "/" in nodeport:
                    nodeport = nodeport.split("/")[0]

            if line[0] == "Selector:" and line[1] != "<none>":
                selector = line[-1]

    if selector is not None:
        output = kubectl_exec(" get pod -o yaml -l "+selector)
        podInfo = yaml.load(output)

        
        for item in podInfo["items"]:
            if "status" in item and "hostIP" in item["status"]:
                hostIP = item["status"]["hostIP"]

    return (port,hostIP,nodeport)

def GetPod(selector):
    try:
        output = kubectl_exec(" get pod -o yaml --show-all -l "+selector)
        podInfo = yaml.load(output)
    except Exception as e:
        print e
        podInfo = None
    return podInfo

def GetLog(jobId):
    selector = "run="+jobId
    podInfo = GetPod(selector)
    podName = None
    if podInfo is not None and "items" in podInfo:
        for item in podInfo["items"]:
            if "metadata" in item and "name" in item["metadata"]:
                podName = item["metadata"]["name"]
    if podName is not None:
        output = kubectl_exec(" logs "+podName)
    else:
        output = "Do not have logs yet."
    return output


def GetJobStatus(jobId):
    pods = GetPod("run="+jobId)["items"]
    output = "unknown"
    detail = "Unknown Status"
    if len(pods) > 0:
        lastpod = pods[-1]
        if "status" in lastpod and "phase" in lastpod["status"]:
            output = lastpod["status"]["phase"]
            detail = yaml.dump(lastpod["status"], default_flow_style=False)
    return output, detail


if __name__ == '__main__':
    TEST_SUB_REG_JOB = False
    TEST_JOB_STATUS = True
    TEST_DEL_JOB = False
    TEST_GET_TB = False
    TEST_GET_SVC = False
    TEST_GET_LOG = False

    if TEST_SUB_REG_JOB:
        parser = argparse.ArgumentParser(description='Launch a kubernetes job')
        parser.add_argument('-f', '--param-file', required=True, type=str,
                            help = 'Path of the Parameter File')
        parser.add_argument('-t', '--template-file', required=True, type=str,
                            help = 'Path of the Job Template File')
        args, unknown = parser.parse_known_args()
        with open(args.param_file,"r") as f:
            jobParamsJsonStr = f.read()
        f.close()

        SubmitRegularJob(jobParamsJsonStr,args.template_file)

    if TEST_JOB_STATUS:
        print GetJobStatus(sys.argv[1])

    if TEST_DEL_JOB:
        print DeleteJob("tf-dist-1483504085-13")

    if TEST_GET_TB:
        print GetTensorboard("tf-resnet18-1483509537-31")

    if TEST_GET_SVC:
        print GetServiceAddress("tf-i-1483566214-12")

    if TEST_GET_LOG:
        print GetLog("tf-i-1483566214-12")
