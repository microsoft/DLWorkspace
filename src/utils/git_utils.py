#!/usr/bin/python 

import subprocess
import yaml

def github_hash(repo, branch) :
    curlCmd = ['curl', "https://api.github.com/repos/" + repo + "/branches/" + branch]
    print "Command: " + ' '.join(curlCmd)
    output = subprocess.check_output(curlCmd)
    print "Output: " + output
    ret = yaml.load(output)
    #print ret
    sha = ret["commit"]["sha"]

    return sha
