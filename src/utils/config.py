import yaml
import os

try:
    f = open(os.path.join(os.path.dirname(os.path.realpath(__file__)),"config.yaml"))
    config = yaml.load(f)
except Exception:
    config = {}
    ()

def GetStoragePath(jobpath, workpath, datapath):
    jobPath = "work/"+jobpath
    workPath = "work/"+workpath
    dataPath = "storage/"+datapath
    return jobPath,workPath,dataPath