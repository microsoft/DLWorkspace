#!/bin/bash
# Install python on CoreOS base image
# Docker environment for development of DL workspace
set -e

sudo apt-get update 
sudo apt-get upgrade -y
sudo apt-get -y dist-upgrade
sudo apt-get install -y linux-image-extra-virtual
sudo apt-get install -y --no-install-recommends \
        apt-utils \
        build-essential \
        cmake \
        git \
        curl \
        wget \
        python-dev \
        python-numpy \
        python-pip \
        apt-transport-https \
        ca-certificates \
        vim \
        nfs-common \
        ubiquity
        


sudo apt-get install -y bison curl 

# Install docker
curl -q https://get.docker.com/ | sudo bash


sudo usermod -aG docker core



sudo add-apt-repository -y ppa:graphics-drivers/ppa
sudo apt-get update
#sudo apt-get install -y --no-install-recommends nvidia-381
sudo apt-get install -y nvidia-381

sudo apt install -y nvidia-modprobe


sudo rm -r /opt/nvidia-driver || true

# should NOT install cuda, install cuda will automatically install a older version of nvidia driver
#sudo dpkg -i /dlwsdata/storage/sys/cuda-repo-ubuntu1604-8-0-local-ga2_8.0.61-1_amd64.deb
#sudo apt-get update
#sudo apt-get install -y --no-install-recommends cuda


# Install nvidia-docker and nvidia-docker-plugin
wget -P /tmp https://github.com/NVIDIA/nvidia-docker/releases/download/v1.0.1/nvidia-docker_1.0.1-1_amd64.deb
sudo dpkg -i /tmp/nvidia-docker*.deb && rm /tmp/nvidia-docker*.deb

# Test nvidia-smi
sudo nvidia-docker run --rm nvidia/cuda nvidia-smi

NVIDIA_VERSION=381.22
sudo mkdir -p /opt/nvidia-driver/
sudo cp -r /var/lib/nvidia-docker/volumes/nvidia_driver/* /opt/nvidia-driver/
NV_DRIVER=/opt/nvidia-driver/$NVIDIA_VERSION
sudo ln -s $NV_DRIVER /opt/nvidia-driver/current

if [ -f /etc/NetworkManager/NetworkManager.conf ]; then
        sed "s/^dns=dnsmasq$/#dns=dnsmasq/" /etc/NetworkManager/NetworkManager.conf > /tmp/NetworkManager.conf && sudo mv /tmp/NetworkManager.conf /etc/NetworkManager/NetworkManager.conf
        sudo service network-manager restart
fi