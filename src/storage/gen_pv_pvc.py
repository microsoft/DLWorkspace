import yaml
from jinja2 import Environment, FileSystemLoader, Template
import os
import sys


def GenStorageClaims(Id,storagePath):
    ENV = Environment(loader=FileSystemLoader(os.path.dirname(os.path.abspath(__file__))))
    pvtemplatePath="pv.yaml.template"
    pvctemplatePath="pvc.yaml.template"

    localPath = "/dlws-data/"+storagePath

    if not os.path.exists(localPath):
        raise ValueError("path does not exist on storage server, cannot create Persistent Volume")

    serverPath = "/mnt/data/"+storagePath

    pv={}
    pv["name"] = Id
    pv["capacity"] = "2Gi"
    pv["server"]="10.196.44.241"
    pv["path"]=serverPath

    pvmeta = ""
    pvcmeta = ""

    template = ENV.get_template(pvtemplatePath)
    pvmeta = template.render(pv=pv)


    template = ENV.get_template(pvctemplatePath)
    pvcmeta = template.render(pv=pv)
    return (pvmeta,pvcmeta)

def GetStoragePath(jobpath, workpath, datapath):
    jobPath = "jobs/"+jobpath
    workPath = "work/"+workpath
    dataPath = "storage/"+datapath
    return jobPath,workPath,dataPath

def main(argv):
    tag=argv[1]
    Id=argv[2]
    print GenStorageClaims(tag,Id)

if __name__ == "__main__":
    main(sys.argv)
