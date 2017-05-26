import yaml
import os
f = open(os.path.join(os.path.dirname(os.path.realpath(__file__)),"config.yaml"))
config = yaml.load(f)


def GetStoragePath(jobpath, workpath, datapath):
    jobPath = "work/"+jobpath
    workPath = "work/"+workpath
    dataPath = "storage/"+datapath
    return jobPath,workPath,dataPath