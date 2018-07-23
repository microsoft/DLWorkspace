#!/bin/bash 

sudo apt-get update 
sudo apt-get install -y --no-install-recommends \
        apt-utils \
        software-properties-common \
        git \
        curl \
        python-pip \
        wget \
        cpio \
        mkisofs \
        apt-transport-https \
        openssh-client \
        ca-certificates \
        sshpass

# Install docker
curl -fsSL https://yum.dockerproject.org/gpg | sudo apt-key add -
sudo add-apt-repository \
       "deb https://apt.dockerproject.org/repo/ \
       ubuntu-$(lsb_release -cs) \
       main"
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
    docker-engine

sudo gpasswd -a dlwsadmin docker
newgrp docker

sudo apt-get install -y --no-install-recommends python-yaml python-jinja2 python-setuptools python-tzlocal python-pycurl

git clone http://github.com/Microsoft/DLWorkspace /home/dlwsadmin/dlworkspace

pwd = $1
shift 1

#TODO - take in parameters from shell script and convert to config.yaml
python /home/dlwsadmin/dlworkspace/src/ARM/createconfig.py /home/dlwsadmin/dlworkspace/src/ClusterBootstrap/config.yaml $@

cd /home/dlwsadmin/dlworkspace/src/ClusterBootstrap

# Generate SSH keys
./deploy.py -y build

# Copy ssh keys
cat deploy/sshkey/id_rsa.pub | /usr/bin/sshpass -p $pwd ssh dlwsadmin@sanjeevmk8s7-worker01.northcentralus.cloudapp.azure.com "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"

