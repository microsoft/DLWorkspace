#!/usr/bin/python 

import subprocess
import yaml

def getresp(url, verbose):
    curlCmd = ['curl']
    curlCmd.append("https://api.github.com/" + url)
    if verbose:
        print "Command: {0}".format(" ".join(curlCmd))
    output = subprocess.check_output(curlCmd)
    if verbose:
        print "Output: {0}".format(output)
    return yaml.load(output)

def github_hash(repo, branch, verbose=True) :
    ret = getresp("repos/" + repo + "/branches/" + branch, verbose)
    sha = ""
    if ("commit" in ret and "sha" in ret["commit"]):
        sha = ret["commit"]["sha"]
    else:
        # try as tag
        retObj = getresp("repos/" + repo + "/git/refs/tags/" + branch, verbose)
        if ("object" in retObj and "sha" in retObj["object"]):
            ret = getresp("repos/" + repo + "/git/tags/" + retObj["object"]["sha"], verbose)
            if ("object" in ret and "sha" in ret["object"]):
                sha = ret["object"]["sha"]

    return sha
