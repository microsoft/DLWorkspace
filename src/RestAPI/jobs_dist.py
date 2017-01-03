import json
import os
import time
import argparse
import uuid
import subprocess
import sys
sys.path.append("../storage")
from gen_pv_pvc import GenStorageClaims, GetStoragePath

import yaml
from jinja2 import Environment, FileSystemLoader, Template

def LoadJobParams(jobParamsJsonStr):
    return json.loads(jobParamsJsonStr)

def kubectl(jobfile,EXEC=True):
    if EXEC:
        output = subprocess.check_output(["bash","-c", "/usr/local/bin/kubectl create -f " + jobfile])
    else:
        output = "Job " + jobfile + " is not submitted to kubernetes cluster"
    print output
    return output


def SubmitDistJob(jobParamsJsonStr,workerJobTemp="./DistTensorFlow_worker.yaml.template",psJobTemp="./DistTensorFlow_ps.yaml.template",tensorboard=False):
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

    localJobPath = "/dlws-data/"+jobPath
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



    jobTempStr = "\n---\n".join(jobTempList)

    with open(jobFilePath, 'w') as f:
        f.write(jobTempStr)

    ret={}

 

    output = kubectl(jobFilePath)    
    if output == "job \""+jobParams["id"]+"\" created\n":
        ret["result"] = "success"
    else:
        ret["result"]  = "fail"


    ret["output"] = output
    
    ret["id"] = jobParams["id"]



    if tensorboard == True:
        jobParams["svc-name"] = "tensorboard-"+jobParams["id"]
        jobParams["app-name"] = "tensorboard-"+jobParams["id"]
        jobParams["port"] = "6006"
        jobParams["port-name"] = "tensorboard"
        jobParams["port-type"] = "TCP"        
        jobParams["tensorboard-id"] = "tensorboard-"+jobParams["id"]

        jobTempDir = os.path.abspath(os.path.dirname(workerJobTemp))

        template = ENV.get_template(os.path.join(jobTempDir,"KubeSvc.yaml.template"))
    
        tensorboardSvcFilePath = os.path.join(jobDir, "tensorboard-svc-"+jobParams["id"]+".yaml")
        with open(tensorboardSvcFilePath, 'w') as f:
            f.write(template.render(svc=jobParams))
 

        template = ENV.get_template(os.path.join(jobTempDir,"TensorboardApp.yaml.template"))

        tensorboardAppFilePath = os.path.join(jobDir, "tensorboard-app-"+jobParams["id"]+".yaml")
        with open(tensorboardAppFilePath, 'w') as f:
            f.write(template.render(job=jobParams))

        output = kubectl(tensorboardSvcFilePath)
        output = kubectl(tensorboardAppFilePath)
        print "tensorboard is running at: https://dlws-master/api/v1/proxy/namespaces/default/services/%s:tensorboard " % jobParams["svc-name"]
    return ret

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Launch a kubernetes job')
    parser.add_argument('-f', '--param-file', required=True, type=str,
                        help = 'Path of the Parameter File')
    parser.add_argument('-p', '--ps-template-file', required=True, type=str,
                        help = 'Path of the PS Job Template File')
    parser.add_argument('-w', '--worker-template-file', required=True, type=str,
                        help = 'Path of the Worker Job Template File')

    parser.add_argument('-np', '--ps-num', required=True, type=int,
                        help = 'Number of Parameter Servers')
    parser.add_argument('-nw', '--worker-num', required=True, type=int,
                        help = 'Number of Workers')



    args, unknown = parser.parse_known_args()
    with open(args.param_file,"r") as f:
        jobParamsJsonStr = f.read()
    f.close()

    SubmitDistJob(jobParamsJsonStr=jobParamsJsonStr,workerJobTemp=args.worker_template_file,psJobTemp=args.ps_template_file,numWorker=args.worker_num,numPs=args.ps_num,tensorboard=False)


