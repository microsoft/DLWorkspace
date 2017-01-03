import json
import os
import time
import argparse
import uuid
import subprocess
import sys
from jobs_tensorboard import GenTensorboardMeta
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


def SubmitJob(jobParamsJsonStr,jobTemp="./RegularJob.yaml.template"):
    jobParams = LoadJobParams(jobParamsJsonStr)
    print jobParamsJsonStr
    if "id" not in jobParams or jobParams["id"] == "":
        #jobParams["id"] = jobParams["job-name"] + "-" + str(uuid.uuid4()) 
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

        jobTempDir = os.path.abspath(os.path.dirname(jobTemp))
        serviceTemplate = ENV.get_template(os.path.join(jobTempDir,"KubeSvc.yaml.template"))

        template = ENV.get_template(serviceTemplate)
        interactiveMeta = template.render(svc=jobParams)
        jobMetaList.append(interactiveMeta)


    jobMeta = "\n---\n".join(jobMetaList)


    with open(jobFilePath, 'w') as f:
        f.write(jobMeta)

    ret={}

    output = kubectl(jobFilePath)    
    #if output == "job \""+jobParams["id"]+"\" created\n":
    #    ret["result"] = "success"
    #else:
    #    ret["result"]  = "fail"


    ret["output"] = output
    
    ret["id"] = jobParams["id"]



    if "logdir" in jobParams and len(jobParams["logdir"].strip()) > 0:
        jobParams["svc-name"] = "tensorboard-"+jobParams["id"]
        jobParams["app-name"] = "tensorboard-"+jobParams["id"]
        jobParams["port"] = "6006"
        jobParams["port-name"] = "tensorboard"
        jobParams["port-type"] = "TCP"        
        jobParams["tensorboard-id"] = "tensorboard-"+jobParams["id"]

        jobTempDir = os.path.abspath(os.path.dirname(jobTemp))

        tensorboardMeta = GenTensorboardMeta(jobParams, os.path.join(jobTempDir,"KubeSvc.yaml.template"), os.path.join(jobTempDir,"TensorboardApp.yaml.template"))

        tensorboardMetaFilePath = os.path.join(jobDir, "tensorboard-"+jobParams["id"]+".yaml")

        with open(tensorboardMetaFilePath, 'w') as f:
            f.write(tensorboardMeta)

        output = kubectl(tensorboardMetaFilePath)
    return ret

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Launch a kubernetes job')
    parser.add_argument('-f', '--param-file', required=True, type=str,
                        help = 'Path of the Parameter File')
    parser.add_argument('-t', '--template-file', required=True, type=str,
                        help = 'Path of the Job Template File')
    args, unknown = parser.parse_known_args()
    with open(args.param_file,"r") as f:
        jobParamsJsonStr = f.read()
    f.close()

    SubmitJob(jobParamsJsonStr,args.template_file)
