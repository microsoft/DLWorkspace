#!/usr/bin/python 
import sys
sys.path
sys.path.append('../../ClusterBootstrap')
sys.path.append('../../utils')

import utils
import yaml
import os
import subprocess
import DockerUtils

if __name__ == '__main__':
    os.chdir(os.path.dirname(__file__))

    config = {}
    try:
        with open("config.yaml", "r") as fp :
            config = yaml.load(fp)
    except:
        sys.exit()

    print config
    os.system("mkdir -p deploy")
    utils.render_template("Dockerfile.template", "./deploy/Dockerfile", config)
    os.system("cp ./gittoken ./deploy/gittoken")

    # Get hash of branch
    curlCmd = ['curl', "https://api.github.com/repos/MSRCCS/kubernetes/branches/" + config["k8s-gitbranch"]]
    #print "Command: " + ' '.join(curlCmd)
    output = subprocess.check_output(curlCmd)
    #print "Output: " + output
    ret = yaml.load(output)
    #print ret
    sha = ret["commit"]["sha"]
    print "SHA of HEAD branch " + config["k8s-gitbranch"] + "is " + sha

    os.chdir("./deploy")
    #dockerBld = "docker build --build-arg NOCACHE=$(date +%s) -t " + config["k8s-bld"] + " ."
    dockerBld = "docker build --build-arg NOCACHE=" + sha + " -t" + config["k8s-bld"] + " ."
    print dockerBld
    os.system(dockerBld)

    os.system("mkdir -p bin")
    DockerUtils.copy_from_docker_image(config["k8s-bld"], "/hyperkube", "./bin/hyperkube")

    os.chdir("../../kubernetes")
    os.system("mkdir -p deploy/bin")
    os.system("cp ../kubernetes-build/deploy/bin/hyperkube ./deploy/bin/hyperkube")
    dockerBld = "docker build --no-cache -t " + config["k8s-pushto"] + " ."
    print dockerBld
    os.system(dockerBld)

    dockerPush = "docker push " + config["k8s-pushto"]
    print dockerPush
    os.system(dockerPush)

