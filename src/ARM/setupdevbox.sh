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
# Run deploy.py commands requiring docker as separate script after adding to docker group so that new permissions take effect
#newgrp docker

sudo apt-get install -y --no-install-recommends python-yaml python-jinja2 python-setuptools python-tzlocal python-pycurl

git clone http://github.com/Microsoft/DLWorkspace /home/dlwsadmin/dlworkspace
cd /home/dlwsadmin/dlworkspace
git fetch --all
git checkout ARMTemplate

cd /home/dlwsadmin/dlworkspace/src/ClusterBootstrap
../ARM/createconfig.py genconfig --outfile /home/dlwsadmin/dlworkspace/src/ClusterBootstrap/config.yaml $@
./az_tools.py --noaz genconfig

# Generate SSH keys
./deploy.py -y build

# Copy ssh keys
../ARM/createconfig.py sshkey $@


