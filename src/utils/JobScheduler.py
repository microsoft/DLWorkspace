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

import re

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

def kubectl_delete(jobfile,EXEC=True):
    if EXEC:
        try:
            cmd = "bash -c '" + config["kubelet-path"] + " delete -f " + jobfile +"'"
            print cmd
            output = os.system(cmd)
        except Exception as e:
            print e
            output = -1
    else:
        output = -1
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





def Split(text,spliter):
    return [x for x in text.split(spliter) if len(x.strip())>0]

def GetServiceAddress(jobId):
    ret = []

    output = kubectl_exec(" describe svc -l run="+jobId)
    svcs = output.split("\n\n\n")
    
    for svc in svcs:
        lines = [Split(x,"\t") for x in Split(svc,"\n")]
        containerPort = None
        hostPort = None
        selector = None
        hostIP = None

        for line in lines:
            if len(line) > 1:
                if line[0] == "Port:":
                    containerPort = line[-1]
                    if "/" in containerPort:
                        containerPort = containerPort.split("/")[0]
                if line[0] == "NodePort:":
                    hostPort = line[-1]
                    if "/" in hostPort:
                        hostPort = hostPort.split("/")[0]

                if line[0] == "Selector:" and line[1] != "<none>":
                    selector = line[-1]

        if selector is not None:
            podInfo = GetPod(selector)
            if podInfo is not None and "items" in podInfo:
                for item in podInfo["items"]:
                    if "status" in item and "hostIP" in item["status"]:
                        hostIP = item["status"]["hostIP"]
        if containerPort is not None and hostIP is not None and hostPort is not None:
            svcMapping = {}
            svcMapping["containerPort"] = containerPort
            svcMapping["hostIP"] = hostIP
            svcMapping["hostPort"] = hostPort
            ret.append(svcMapping)
    return ret



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
        output = ""
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




def SubmitJob(job):
    jobParams = json.loads(base64.b64decode(job["jobParams"]))

    dataHandler = DataHandler()



    jobParams["pvc_job"] = "jobs-"+jobParams["jobId"]
    jobParams["pvc_work"] = "work-"+jobParams["jobId"]
    jobParams["pvc_data"] = "storage-"+jobParams["jobId"]
  

    if "jobPath" in jobParams and len(jobParams["jobPath"].strip()) > 0: 
        jobPath = jobParams["jobPath"]
    else:
        jobPath = time.strftime("%y%m%d")+"/"+jobParams["jobId"]
        jobParams["jobPath"] = jobPath

    if "workPath" not in jobParams or len(jobParams["workPath"].strip()) == 0: 
        dataHandler.SetJobError(jobParams["jobId"],"ERROR: work-path does not exist")
        return False

    if "dataPath" not in jobParams or len(jobParams["dataPath"].strip()) == 0: 
        dataHandler.SetJobError(jobParams["jobId"],"ERROR: data-path does not exist")
        return False


    jobPath,workPath,dataPath = GetStoragePath(jobPath,jobParams["workPath"],jobParams["dataPath"])


    localJobPath = os.path.join(config["storage-mount-path"],jobPath)
    if not os.path.exists(localJobPath):
        os.makedirs(localJobPath)


    jobParams["LaunchCMD"] = ""
    if "cmd" not in jobParams:
        jobParams["cmd"] = ""
        
    if isinstance(jobParams["cmd"], basestring) and not jobParams["cmd"] == "":
        launchScriptPath = os.path.join(localJobPath,"launch-%s.sh" % jobParams["jobId"])
        with open(launchScriptPath, 'w') as f:
            f.write(jobParams["cmd"] + "\n")
        f.close()        
        jobParams["LaunchCMD"] = "[\"bash\", \"/job/launch-%s.sh\"]" % jobParams["jobId"]


    jobParams["jobDescriptionPath"] = "jobfiles/" + time.strftime("%y%m%d") + "/" + jobParams["jobId"] + "/" + jobParams["jobId"]+".yaml"

    jobDescriptionPath = os.path.join(os.path.dirname(config["storage-mount-path"]), jobParams["jobDescriptionPath"])
    if not os.path.exists(os.path.dirname(os.path.realpath(jobDescriptionPath))):
        os.makedirs(os.path.dirname(os.path.realpath(jobDescriptionPath)))



    ENV = Environment(loader=FileSystemLoader("/"))

    jobTempDir = os.path.join(config["root-path"],"Jobs_Templete")
    jobTemp= os.path.join(jobTempDir, "RegularJob.yaml.template")


    template = ENV.get_template(os.path.abspath(jobTemp))
    job_description = template.render(job=jobParams)




    pv_description_j,pvc_description_j = GenStorageClaims(jobParams["pvc_job"],jobPath)
    pv_description_u,pvc_description_u = GenStorageClaims(jobParams["pvc_work"],workPath)
    pv_description_d,pvc_description_d = GenStorageClaims(jobParams["pvc_data"],dataPath)


    jobDescriptionList = []
    jobDescriptionList.append(pv_description_j)
    jobDescriptionList.append(pvc_description_j)
    jobDescriptionList.append(pv_description_u)
    jobDescriptionList.append(pvc_description_u)
    jobDescriptionList.append(pv_description_d)
    jobDescriptionList.append(pvc_description_d)
    jobDescriptionList.append(job_description)

    if ("interactivePort" in jobParams and len(jobParams["interactivePort"].strip()) > 0):
        ports = [p.strip() for p in re.split(",|;",jobParams["interactivePort"]) if len(p.strip()) > 0 and p.strip().isdigit()]
        for portNum in ports:
            jobParams["serviceId"] = "interactive-"+jobParams["jobId"]+"-"+portNum
            jobParams["port"] = portNum
            jobParams["port-name"] = "interactive"
            jobParams["port-type"] = "TCP"

            serviceTemplate = ENV.get_template(os.path.join(jobTempDir,"KubeSvc.yaml.template"))

            template = ENV.get_template(serviceTemplate)
            interactiveMeta = template.render(svc=jobParams)
            jobDescriptionList.append(interactiveMeta)


    jobDescription = "\n---\n".join(jobDescriptionList)


    if os.path.isfile(jobDescriptionPath):
        output = kubectl_delete(jobDescriptionPath) 

    with open(jobDescriptionPath, 'w') as f:
        f.write(jobDescription)
    ret={}

       
    output = kubectl_create(jobDescriptionPath)    
    #if output == "job \""+jobParams["jobId"]+"\" created\n":
    #    ret["result"] = "success"
    #else:
    #    ret["result"]  = "fail"


    ret["output"] = output
    
    ret["jobId"] = jobParams["jobId"]


    if "userName" not in jobParams:
        jobParams["userName"] = ""

    dataHandler.UpdateJobTextField(jobParams["jobId"],"jobStatus","scheduling")
    dataHandler.UpdateJobTextField(jobParams["jobId"],"jobDescriptionPath",jobParams["jobDescriptionPath"])
    dataHandler.UpdateJobTextField(jobParams["jobId"],"jobDescription",base64.b64encode(jobDescription))


    jobMeta = {}
    jobMeta["jobDescriptionPath"] = jobParams["jobDescriptionPath"]
    jobMeta["pvc_data"] = jobParams["pvc_data"]
    jobMeta["pvc_work"] = jobParams["pvc_work"]
    jobMeta["pvc_job"] = jobParams["pvc_job"]
    jobMeta["pvc_job"] = jobParams["pvc_job"]
    jobMeta["LaunchCMD"] = jobParams["LaunchCMD"]

    jobMetaStr = base64.b64encode(json.dumps(jobMeta))
    dataHandler.UpdateJobTextField(jobParams["jobId"],"jobMeta",jobMetaStr)


    return ret


def KillJob(job):
    dataHandler = DataHandler()
    if "jobDescriptionPath" in job:
        jobDescriptionPath = os.path.join(os.path.dirname(config["storage-mount-path"]), job["jobDescriptionPath"])
        if os.path.isfile(jobDescriptionPath):
            if kubectl_delete(jobDescriptionPath) == 0:
                dataHandler.UpdateJobTextField(job["jobId"],"jobStatus","killed")
                return True
            else:
                dataHandler.UpdateJobTextField(job["jobId"],"errorMsg","Cannot delete job from Kubernetes Cluster!")
    else:
        dataHandler.UpdateJobTextField(job["jobId"],"errorMsg","Cannot find job description file!")

    dataHandler.UpdateJobTextField(job["jobId"],"jobStatus","error")
    return False



def ExtractJobLog(jobId,logPath):
    jobLogDir = os.path.dirname(logPath)
    dataHandler = DataHandler()
    if not os.path.exists(jobLogDir):
        os.makedirs(jobLogDir)

    log = GetLog(jobId)
    if len(log.strip()) > 0:
        dataHandler.UpdateJobTextField(jobId,"jobLog",log)
        with open(logPath, 'w') as f:
            f.write(log)
        f.close()



def UpdateJobStatus(job):
    dataHandler = DataHandler()
    jobParams = json.loads(base64.b64decode(job["jobParams"]))


    jobPath,workPath,dataPath = GetStoragePath(jobParams["jobPath"],jobParams["workPath"],jobParams["dataPath"])
    localJobPath = os.path.join(config["storage-mount-path"],jobPath)
    logPath = os.path.join(localJobPath,"joblog.txt")
    ExtractJobLog(job["jobId"],logPath)

    result, detail = GetJobStatus(job["jobId"])

    
    jobDescriptionPath = os.path.join(os.path.dirname(config["storage-mount-path"]), job["jobDescriptionPath"]) if "jobDescriptionPath" in job else None

    if result.strip() == "Succeeded":
        dataHandler.UpdateJobTextField(job["jobId"],"jobStatus","finished")
        if jobDescriptionPath is not None and os.path.isfile(jobDescriptionPath):
            kubectl_delete(jobDescriptionPath) 

    elif result.strip() == "Running":
        if job["jobStatus"] != "running":
            dataHandler.UpdateJobTextField(job["jobId"],"jobStatus","running")
        if "interactivePort" in jobParams:
            serviceAddress = GetServiceAddress(job["jobId"])
            serviceAddress = base64.b64encode(json.dumps(serviceAddress))
            dataHandler.UpdateJobTextField(job["jobId"],"endpoints",serviceAddress)

    elif result.strip() == "Failed":
        dataHandler.UpdateJobTextField(job["jobId"],"jobStatus","failed")
        dataHandler.UpdateJobTextField(job["jobId"],"errorMsg",detail)
        if jobDescriptionPath is not None and os.path.isfile(jobDescriptionPath):
            kubectl_delete(jobDescriptionPath) 

def ScheduleJob():
    while True:
        #try:
            dataHandler = DataHandler()
            pendingJobs = dataHandler.GetPendingJobs()
            print len(pendingJobs)

            for job in pendingJobs:
                #try:
                    print "Processing job: %s, status: %s" % (job["jobId"], job["jobStatus"])
                    if job["jobStatus"] == "queued":
                        SubmitJob(job)
                    elif job["jobStatus"] == "killing":
                        KillJob(job)
                    elif job["jobStatus"] == "scheduling" or job["jobStatus"] == "running" :
                        UpdateJobStatus(job)
                #except Exception as e:
                #    print e
        #except Exception as e:
        #    print e
            time.sleep(1)
















##################################################################################################################################

def SubmitRegularJob(jobParamsJsonStr):
    jobParams = LoadJobParams(jobParamsJsonStr)
    print jobParamsJsonStr

    dataHandler = DataHandler()

    if "jobId" not in jobParams or jobParams["jobId"] == "":
        #jobParams["jobId"] = jobParams["jobName"] + "-" + str(uuid.uuid4()) 
        #jobParams["jobId"] = jobParams["jobName"] + "-" + str(time.time())
        jobParams["jobId"] = str(uuid.uuid4()) 
    jobParams["jobId"] = jobParams["jobId"].replace("_","-").replace(".","-")

    if "cmd" not in jobParams:
        jobParams["cmd"] = ""
    if isinstance(jobParams["cmd"], basestring) and not jobParams["cmd"] == "":
        jobParams["cmd"] = "[\"" + jobParams["cmd"].replace(" ","\",\"") + "\"]"


    jobParams["pvc_job"] = "jobs-"+jobParams["jobId"]
    jobParams["pvc_work"] = "work-"+jobParams["jobId"]
    jobParams["pvc_data"] = "storage-"+jobParams["jobId"]
  

    if "jobPath" in jobParams and len(jobParams["jobPath"].strip()) > 0: 
        jobPath = jobParams["jobPath"]
    else:
        jobPath = time.strftime("%y%m%d")+"/"+jobParams["jobId"]

    if "workPath" not in jobParams or len(jobParams["workPath"].strip()) == 0: 
        raise Exception("ERROR: work-path cannot be empty")

    if "dataPath" not in jobParams or len(jobParams["dataPath"].strip()) == 0: 
        raise Exception("ERROR: data-path cannot be empty")


    jobPath,workPath,dataPath = GetStoragePath(jobPath,jobParams["workPath"],jobParams["dataPath"])


    localJobPath = os.path.join(config["storage-mount-path"],jobPath)
    if not os.path.exists(localJobPath):
        os.makedirs(localJobPath)

    jobDir = os.path.join(os.path.dirname(config["storage-mount-path"]), "jobfiles")
    if not os.path.exists(jobDir):
        os.mkdir(jobDir)

    jobDir = os.path.join(jobDir,time.strftime("%y%m%d"))
    if not os.path.exists(jobDir):
        os.mkdir(jobDir)

    jobDir = os.path.join(jobDir,jobParams["jobId"])
    if not os.path.exists(jobDir):
        os.mkdir(jobDir)

    jobFilePath = os.path.join(jobDir, jobParams["jobId"]+".yaml")    

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
        jobParams["svc-name"] = "interactive-"+jobParams["jobId"]
        jobParams["app-name"] = jobParams["jobId"]
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
    #if output == "job \""+jobParams["jobId"]+"\" created\n":
    #    ret["result"] = "success"
    #else:
    #    ret["result"]  = "fail"


    ret["output"] = output
    
    ret["jobId"] = jobParams["jobId"]


    if "logDir" in jobParams and len(jobParams["logDir"].strip()) > 0:
        tensorboardParams = jobParams.copy()
        tensorboardParams["svc-name"] = "tensorboard-"+jobParams["jobId"]
        tensorboardParams["app-name"] = "tensorboard-"+jobParams["jobId"]
        tensorboardParams["port"] = "6006"
        tensorboardParams["port-name"] = "tensorboard"
        tensorboardParams["port-type"] = "TCP"        
        tensorboardParams["tensorboard-id"] = "tensorboard-"+jobParams["jobId"]
        
        tensorboardParams["jobId"] = tensorboardParams["svc-name"]
        tensorboardParams["jobName"] = tensorboardParams["svc-name"]
        tensorboardMeta = GenTensorboardMeta(tensorboardParams, os.path.join(jobTempDir,"KubeSvc.yaml.template"), os.path.join(jobTempDir,"TensorboardApp.yaml.template"))

        tensorboardMetaFilePath = os.path.join(jobDir, tensorboardParams["jobId"]+".yaml")

        with open(tensorboardMetaFilePath, 'w') as f:
            f.write(tensorboardMeta)
        output = kubectl_create(tensorboardMetaFilePath)
        tensorboardParams["jobDescriptionPath"] = tensorboardMetaFilePath
        tensorboardParams["jobDescription"] = base64.b64encode(tensorboardMeta)
        if "userName" not in tensorboardParams:
            tensorboardParams["userName"] = ""
        dataHandler.AddJob(tensorboardParams)

    jobParams["jobDescriptionPath"] = jobFilePath
    jobParams["jobDescription"] = base64.b64encode(jobMeta)
    if "userName" not in jobParams:
        jobParams["userName"] = ""

    dataHandler.AddJob(jobParams)

    return ret


def SubmitDistJob(jobParamsJsonStr,tensorboard=False):
    

    jobTempDir = os.path.join(config["root-path"],"Jobs_Templete")
    workerJobTemp= os.path.join(jobTempDir, "DistTensorFlow_worker.yaml.template")
    psJobTemp= os.path.join(jobTempDir, "DistTensorFlow_ps.yaml.template")

    jobParams = LoadJobParams(jobParamsJsonStr)
    if "jobId" not in jobParams or jobParams["jobId"] == "":
        #jobParams["jobId"] = jobParams["jobName"] + "-" + str(uuid.uuid4()) 
        jobParams["jobId"] = jobParams["jobName"] + "-" + str(time.time())
    jobParams["jobId"] = jobParams["jobId"].replace("_","-").replace(".","-")

    if "cmd" not in jobParams:
        jobParams["cmd"] = ""


    if "jobPath" in jobParams and len(jobParams["jobParams"].strip()) > 0: 
        jobPath = jobParams["jobPath"]
    else:
        jobPath = time.strftime("%y%m%d")+"/"+jobParams["jobId"]

    if "workPath" not in jobParams or len(jobParams["workPath"].strip()) == 0: 
        raise Exception("ERROR: work-path cannot be empty")

    if "dataPath" not in jobParams or len(jobParams["dataPath"].strip()) == 0: 
        raise Exception("ERROR: data-path cannot be empty")


    if "worker-num" not in jobParams:
        raise Exception("ERROR: unknown number of workers")
    if "ps-num" not in jobParams:
        raise Exception("ERROR: unknown number of parameter servers")

    numWorker = int(jobParams["worker-num"])
    numPs = int(jobParams["ps-num"])

    jobPath,workPath,dataPath = GetStoragePath(jobPath,jobParams["workPath"],jobParams["dataPath"])

    localJobPath = os.path.join(config["storage-mount-path"],jobPath)

    if not os.path.exists(localJobPath):
        os.makedirs(localJobPath)

    jobDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "jobfiles")
    if not os.path.exists(jobDir):
        os.mkdir(jobDir)

    jobDir = os.path.join(jobDir,time.strftime("%y%m%d"))
    if not os.path.exists(jobDir):
        os.mkdir(jobDir)

    jobDir = os.path.join(jobDir,jobParams["jobId"])
    if not os.path.exists(jobDir):
        os.mkdir(jobDir)

    jobFilePath = os.path.join(jobDir, jobParams["jobId"]+".yaml")    

    ENV = Environment(loader=FileSystemLoader("/"))


    jobTempList= []
    workerHostList = []
    psHostList = []
    for i in range(numWorker):
        workerHostList.append(jobParams["jobId"]+"-worker"+str(i)+":2222")


    for i in range(numPs):
        psHostList.append(jobParams["jobId"]+"-ps"+str(i)+":2222")


    workerHostStr = ",".join(workerHostList)
    psHostStr = ",".join(psHostList)

    cmdStr = jobParams["cmd"]


    jobParams["pvc_job"] = "jobs-"+jobParams["jobId"]
    jobParams["pvc_work"] = "work-"+jobParams["jobId"]
    jobParams["pvc_data"] = "storage-"+jobParams["jobId"]


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
        jobParams["svc-name"] = "tensorboard-"+jobParams["jobId"]
        jobParams["app-name"] = "tensorboard-"+jobParams["jobId"]
        jobParams["port"] = "6006"
        jobParams["port-name"] = "tensorboard"
        jobParams["port-type"] = "TCP"        
        jobParams["tensorboard-id"] = "tensorboard-"+jobParams["jobId"]

        tensorboardMeta = GenTensorboardMeta(jobParams, os.path.join(jobTempDir,"KubeSvc.yaml.template"), os.path.join(jobTempDir,"TensorboardApp.yaml.template"))

        tensorboardMetaFilePath = os.path.join(jobDir, "tensorboard-"+jobParams["jobId"]+".yaml")

        with open(tensorboardMetaFilePath, 'w') as f:
            f.write(tensorboardMeta)

        output = kubectl_create(tensorboardMetaFilePath)

    with open(jobFilePath, 'w') as f:
        f.write(jobMeta)

    output = kubectl_create(jobFilePath)    

    ret={}
    ret["output"] = output
    ret["jobId"] = jobParams["jobId"]


    jobParams["jobDescriptionPath"] = jobFilePath
    jobParams["jobDescription"] = base64.b64encode(jobMeta)
    if "userName" not in jobParams:
        jobParams["userName"] = ""
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





if __name__ == '__main__':
    TEST_SUB_REG_JOB = False
    TEST_JOB_STATUS = False
    TEST_DEL_JOB = False
    TEST_GET_TB = False
    TEST_GET_SVC = False
    TEST_GET_LOG = False

    ScheduleJob()

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
