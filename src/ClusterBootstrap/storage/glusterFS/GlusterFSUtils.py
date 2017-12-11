import json
import os
import re
import math

import json

# GlusterFSYaml is a class used to assist the generation of the yaml file required to deploy a 
# GlusterFS. 
# nodesinfo: partition of nodes, e.g., from getPartitions() call in deploy.py
# arg: either an integer (1,2,..) , indicating which block device of each drive to use, 
#      or a regular expression used to match a particular device 
class GlusterFSJson:
    def __init__(self, ipToHostname, nodesinfo, arg):
        if isinstance( arg, (int,long) ):
            regexp = "/dev/[s|h]d[^a]"+str(arg)
        else:
            regexp = arg
        #print regexp
        regmatch = re.compile(regexp)
        self.nodesinfo = []
        cnt = -1; 
        for node in nodesinfo:
            alldeviceinfo = nodesinfo[node]
            nodeInfo = {}
            deviceList = []
            cnt += 1
            hostnamesInfo = {}
            hostnamesInfo["manage"] = node if ipToHostname is None else [ipToHostname[node]]
            hostnamesInfo["storage"] = [node.encode("ascii","ignore")]
            nodeInfo["hostnames"] = hostnamesInfo
            nodeInfo["zone"] = 1
            
            for bdevice in alldeviceinfo:
                deviceinfo = alldeviceinfo[bdevice] 
                for part in deviceinfo["parted"]:
                    bdevicename = deviceinfo["name"] + str(part)
                    #print bdevicename
                    match = regmatch.search(bdevicename)
                    if not ( match is None ):
                        deviceList.append(match.group(0))
            if len(deviceList) >= 1:
                oneNodeInfo = {}
                oneNodeInfo["node"] = nodeInfo
                oneNodeInfo["devices"] = deviceList
                self.nodesinfo.append(oneNodeInfo)
        if len(self.nodesinfo)<=0:
            print "Error: We can't find any device to deploy GlusterFS. Please check the device argument and/or regular expression to see if any block device on the target node can match with the current argument. "
            exit()
    # dump infrastructure information to a yaml file. 
    def dump(self, jsonfile):
        outjson = {}
        outjson["clusters"] = [ { "nodes":self.nodesinfo } ]
        dirname = os.path.dirname(jsonfile)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(jsonfile, "w") as fout:
            dump = json.dump( outjson, fout, ensure_ascii=True )
        fout.close()
