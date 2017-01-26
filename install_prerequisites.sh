#!/bin/bash 

sudo apt-get update 
sudo apt-get install -y --no-install-recommends \
        python-pip \

# Install docker
curl -fsSL https://yum.dockerproject.org/gpg | apt-key add -
sudo add-apt-repository \
       "deb https://apt.dockerproject.org/repo/ \
       ubuntu-$(lsb_release -cs) \
       main"
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
    docker-engine

sudo echo "dockerd > /dev/null 2>&1 &" | sudo cat >> /etc/bash.bashrc

