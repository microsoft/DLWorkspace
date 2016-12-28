import json
import os
import time
import argparse
import uuid
import subprocess
import sys
sys.path.append("../storage")
from gen_pv_pvc import GenStorageClaims

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


def SubmitJob(jobParamsJsonStr,workerJobTemp="./DistTensorFlow_worker.yaml.template",psJobTemp="./DistTensorFlow_ps.yaml.template",numWorker=2,numPs=1,tensorboard=False):
    jobParams = LoadJobParams(jobParamsJsonStr)
    if "id" not in jobParams or jobParams["id"] == "":
        #jobParams["id"] = jobParams["job-name"] + "-" + str(uuid.uuid4()) 
        jobParams["id"] = jobParams["job-name"] + "-" + str(time.time())
    jobParams["id"] = jobParams["id"].replace("_","-").replace(".","-")

    if "cmd" not in jobParams:
        jobParams["cmd"] = ""


    jobParams["pvc_job"] = "jobs-"+jobParams["id"]
    jobParams["pvc_scratch"] = "scratch-"+jobParams["id"]
    jobParams["pvc_data"] = "storage-"+jobParams["id"]
  

    jobPath = "jobs/"+jobParams["id"]
    scratchPath = "scratch/"+jobParams["scratch-path"]
    dataPath = "storage/"+jobParams["data-path"]

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


    pv_file_j,pvc_file_j = GenStorageClaims(jobParams["pvc_job"],jobPath,jobDir)
    pv_file_u,pvc_file_u = GenStorageClaims(jobParams["pvc_scratch"],scratchPath,jobDir)
    pv_file_d,pvc_file_d = GenStorageClaims(jobParams["pvc_data"],dataPath,jobDir)

    ret={}

 

    output = kubectl(pv_file_j)
    output = kubectl(pvc_file_j)

    output = kubectl(pv_file_u)
    output = kubectl(pvc_file_u)

    output = kubectl(pv_file_d)
    output = kubectl(pvc_file_d)


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

    SubmitJob(jobParamsJsonStr=jobParamsJsonStr,workerJobTemp=args.worker_template_file,psJobTemp=args.ps_template_file,numWorker=args.worker_num,numPs=args.ps_num,tensorboard=True)


