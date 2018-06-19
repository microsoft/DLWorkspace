#!/usr/bin/python 
import sys
sys.path
sys.path.append('../../..')
sys.path.append('../../../../utils')

import utils
import yaml
import os
import subprocess
import DockerUtils
import git_utils
import uuid

if __name__ == '__main__':
    os.chdir(os.path.dirname(__file__))

    # config = {}
    # try:
    #     with open("config.yaml", "r") as fp :
    #         config = yaml.load(fp)
    # except:
    #     sys.exit()

    # print config
    # os.system("mkdir -p deploy")
    # utils.render_template("Dockerfile.template", "./deploy/Dockerfile", config)
    # os.system("cp ./gittoken ./deploy/gittoken")

    # Get hash of branch
    sha = git_utils.github_hash("{{cnf["k8s-gitrepo"]}}", "{{cnf["k8s-gitbranch"]}}")
    
    # private repo, don't know how to get hash, use random sha for now to force rebuild
    #shacri = str(uuid.uuid4())
    shacri = git_utils.github_hash("{{cnf["k8scri-gitrepo"]}}", "{{cnf["k8scri-gitbranch"]}}")

    print "SHA of HEAD branch " + "{{cnf["k8s-gitbranch"]}}" + "is " + sha
    print "SHA of HEAD branch for CRI " + "{{cnf["k8scri-gitbranch"]}}" + "is " + shacri

    #os.chdir("./deploy")
    #dockerBld = "docker build --build-arg NOCACHE=$(date +%s) -t " + "{{cnf["k8s-bld"]}}"" + " ."
    dockerBld = "docker build --build-arg NOCACHE=" + sha + " --build-arg NOCACHE_CRI=" + shacri + " -t " + "{{cnf["k8s-bld"]}}" + " ."
    print dockerBld
    os.system(dockerBld)

    # hyperkube is all-in-one binary, can get specific ones as needed for size
    os.system("mkdir -p ../../bin")
    print "Copy file hyperkube"
    # gets kube-scheduler, kube-apiserver
    DockerUtils.copy_from_docker_image("{{cnf["k8s-bld"]}}", "/hyperkube", "../kubernetes/hyperkube") 
    print "Copy file kubelet"
    DockerUtils.copy_from_docker_image("{{cnf["k8s-bld"]}}", "/kubelet", "../kubernetes/kubelet")
    print "Copy file kubectl"
    DockerUtils.copy_from_docker_image("{{cnf["k8s-bld"]}}", "/kubectl", "../kubernetes/kubectl")
    print "Copy file crishim"
    DockerUtils.copy_from_docker_image("{{cnf["k8s-bld"]}}", "/crishim", "../kubernetes/crishim")
    print "Copy file kube-scheduler"
    DockerUtils.copy_from_docker_image("{{cnf["k8s-bld"]}}", "/kube-scheduler", "../kubernetes/kube-scheduler")
    print "Copy nvidiagpuplugin"
    DockerUtils.copy_from_docker_image("{{cnf["k8s-bld"]}}", "/nvidiagpuplugin.so", "../kubernetes/nvidiagpuplugin.so")
    print "Copy gpuschedulerplugin"
    DockerUtils.copy_from_docker_image("{{cnf["k8s-bld"]}}", "/gpuschedulerplugin.so", "../kubernetes/gpuschedulerplugin.so")

    # os.chdir("../../kubernetes")
    # dockerBld = "docker build --no-cache -t " + config["k8s-pushto"] + " ."
    # print dockerBld
    # os.system(dockerBld)

    # dockerPush = "docker push " + config["k8s-pushto"]
    # print dockerPush
    # os.system(dockerPush)

