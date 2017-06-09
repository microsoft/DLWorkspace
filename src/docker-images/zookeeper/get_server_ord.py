#!/usr/bin/python
import argparse
import socket
import os
import subprocess


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = "Identify the ordinary number of current zookeeper node in the server list. ")
    parser.add_argument("--ensemble", 
        help="list of zookeeper node", 
        action="store")
    parser.add_argument("--info", 
        help="print server list", 
        action="store", 
        default="" )
    args = parser.parse_args()
    nodename = subprocess.check_output( "hostname", shell=True ).strip()
    domain = subprocess.check_output( "hostname -d", shell=True ).strip()

    ensemble = args.ensemble.split(";")
    ensemble.sort()
    nservers = len(ensemble)
    info = args.info
    if len(info)>0:
        for i in range(nservers):
            print "server.%d=%s:%s" % (i+1, ensemble[i], info )
    else:
        for i in range(nservers):
            if ensemble[i].startswith(nodename):
                print i
                exit()
        print -1
        exit()
    


