import yaml
from jinja2 import Environment, FileSystemLoader, Template
import os
import sys


def main(argv):
    ENV = Environment(loader=FileSystemLoader(os.path.dirname(os.path.abspath(__file__))))
    tag=argv[1]
    Id=argv[2]
    pvtemplatePath="pv.yaml.template"
    pvctemplatePath="pvc.yaml.template"

    outputPath=argv[3]
    localPath = "/dlws-data/"+tag+"/"+Id
    if not os.path.exists(localPath):
        os.makedirs(localPath)

    serverPath = "/mnt/data/"+tag+"/"+Id

    pv={}
    pv["name"] = "pv-"+tag+"-"+Id
    pv["capacity"] = "2Gi"
    pv["server"]="10.196.44.241"
    pv["path"]=serverPath



    template = ENV.get_template(pvtemplatePath)
    with open(outputPath+"/pv-"+Id+".yaml", 'w') as f:
        f.write(template.render(pv=pv))


    template = ENV.get_template(pvctemplatePath)
    with open(outputPath+"/pvc-"+Id+".yaml", 'w') as f:
        f.write(template.render(pv=pv))


if __name__ == "__main__":
    main(sys.argv)
