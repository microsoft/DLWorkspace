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
import git_utils

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
    sha = git_utils.github_hash(config["k8s-gitrepo"], config["k8s-gitbranch"])
    print "SHA of HEAD branch " + config["k8s-gitbranch"] + "is " + sha

    os.chdir("./deploy")
    #dockerBld = "docker build --build-arg NOCACHE=$(date +%s) -t " + config["k8s-bld"] + " ."
    dockerBld = "docker build --build-arg NOCACHE=" + sha + " -t " + config["k8s-bld"] + " ."
    print dockerBld
    os.system(dockerBld)

    # hyperkube is all-in-one binary, can get specific ones as needed for size
    os.system("mkdir -p ../../kubernetes/deploy/bin")
    print "Copy file hyperkube"
    # gets kube-scheduler, kube-apiserver
    DockerUtils.copy_from_docker_image(config["k8s-bld"], "/hyperkube", "../../kubernetes/deploy/bin/hyperkube") 
    print "Copy file kubelet"
    DockerUtils.copy_from_docker_image(config["k8s-bld"], "/kubelet", "../../kubernetes/deploy/bin/kubelet")
    print "Copy file kubectl"
    DockerUtils.copy_from_docker_image(config["k8s-bld"], "/kubectl", "../../kubernetes/deploy/bin/kubectl")

    os.chdir("../../kubernetes")
    dockerBld = "docker build --no-cache -t " + config["k8s-pushto"] + " ."
    print dockerBld
    os.system(dockerBld)

    dockerPush = "docker push " + config["k8s-pushto"]
    print dockerPush
    os.system(dockerPush)

