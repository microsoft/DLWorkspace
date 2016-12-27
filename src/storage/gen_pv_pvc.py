import yaml
from jinja2 import Environment, FileSystemLoader, Template
import os
import sys


def GenStorageClaims(Id,storagePath, outputPath):
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



    template = ENV.get_template(pvtemplatePath)
    with open(outputPath+"/pv-"+Id+".yaml", 'w') as f:
        f.write(template.render(pv=pv))


    template = ENV.get_template(pvctemplatePath)
    with open(outputPath+"/pvc-"+Id+".yaml", 'w') as f:
        f.write(template.render(pv=pv))
    return (outputPath+"/pv-"+Id+".yaml",outputPath+"/pvc-"+Id+".yaml")


def main(argv):
    tag=argv[1]
    Id=argv[2]
    outputPath=argv[3]
    GenStorageClaims(tag,Id,outputPath)

if __name__ == "__main__":
    main(sys.argv)
