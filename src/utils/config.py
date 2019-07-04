import yaml
import os
from Queue import Queue
import threading

try:
    f = open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.yaml"))
    config = yaml.full_load(f)
except Exception:
    config = {}
    ()

def GetWorkPath(workpath):
    workPath = "work/"+workpath
    return workPath

def GetStoragePath(jobpath, workpath, datapath):
    jobPath = "work/"+jobpath
    workPath = "work/"+workpath
    dataPath = "storage/"+datapath
    return jobPath,workPath,dataPath

global global_vars
global_vars={}
global_vars["sql_connections"] = Queue()
global_vars["sql_connection_num"] = 0
global_vars["sql_lock"] = threading.Lock()
