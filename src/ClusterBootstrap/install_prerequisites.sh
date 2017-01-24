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
        ca-certificates 

# Install docker
curl -fsSL https://yum.dockerproject.org/gpg | apt-key add -
sudo add-apt-repository \
       "deb https://apt.dockerproject.org/repo/ \
       ubuntu-$(lsb_release -cs) \
       main"
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
    docker-engine

pip install --upgrade pip
pip install setuptools && pip install pyyaml && pip install jinja2

sudo echo "dockerd > /dev/null 2>&1 &" | cat >> /etc/bash.bashrc

