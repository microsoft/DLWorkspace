#!/bin/bash
# Install python on CoreOS base image
# Docker environment for development of DL workspace
sudo apt-get update 

sudo apt-get install -y --no-install-recommends \
        apt-utils \
        software-properties-common \
        build-essential \
        cmake \
        git \
        curl \
        wget \
        protobuf-compiler \
        python-dev \
        python-numpy \
        python-pip \
        cpio \
        mkisofs \
        apt-transport-https \
        openssh-client \
        ca-certificates \
        vim \
        sudo 
        

sudo apt-get install -y bison curl parted

# Install docker
which docker
if [ $? -eq 0 ]
then 
docker --version
## docker already installed
else
curl -q https://get.docker.com/ | sudo bash
fi

sudo pip install --upgrade pip
sudo pip install setuptools
sudo pip install pyyaml jinja2 argparse

sudo usermod -aG docker core

