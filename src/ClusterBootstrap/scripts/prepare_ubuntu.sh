#!/bin/bash
# Install python on CoreOS base image
# Docker environment for development of DL workspace
sudo apt-get update 
sudo apt-get upgrade -y
sudo apt-get install -y --no-install-recommends \
        apt-utils \
        software-properties-common \
        build-essential \
        cmake \
        git \
        curl \
        wget \
        python-dev \
        python-pip \
        python-yaml \
        python-jinja2 \
        python-argparse \
        python-setuptools \
        apt-transport-https \
        ca-certificates \
        vim \
        sudo \
        nfs-common
        

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
# pip doesn't install python for root account, causing issues. 
# sudo pip install setuptools
# sudo pip install pyyaml jinja2 argparse

sudo usermod -aG docker $USER

if [ -f /etc/NetworkManager/NetworkManager.conf ]; then
        sed "s/^dns=dnsmasq$/#dns=dnsmasq/" /etc/NetworkManager/NetworkManager.conf > /tmp/NetworkManager.conf && sudo mv /tmp/NetworkManager.conf /etc/NetworkManager/NetworkManager.conf
        sudo service network-manager restart
fi

sudo service apache2 stop

if  lspci | grep -qE "[0-9a-fA-F][0-9a-fA-F]:[0-9a-fA-F][0-9a-fA-F].[0-9] (3D|VGA compatible) controller: NVIDIA Corporation.*" ; then

        NVIDIA_VERSION=381.22
        # make the script reexecutable after a failed download
        rm /tmp/NVIDIA-Linux-x86_64-$NVIDIA_VERSION.run
        wget -P /tmp http://us.download.nvidia.com/XFree86/Linux-x86_64/$NVIDIA_VERSION/NVIDIA-Linux-x86_64-$NVIDIA_VERSION.run
        chmod +x /tmp/NVIDIA-Linux-x86_64-$NVIDIA_VERSION.run
        sudo bash /tmp/NVIDIA-Linux-x86_64-$NVIDIA_VERSION.run -a -s

        sudo apt install -y nvidia-modprobe

        sudo rm -r /opt/nvidia-driver || true

        # Install nvidia-docker and nvidia-docker-plugin
        rm /tmp/nvidia-docker*.deb
        wget -P /tmp https://github.com/NVIDIA/nvidia-docker/releases/download/v1.0.1/nvidia-docker_1.0.1-1_amd64.deb
        sudo dpkg -i /tmp/nvidia-docker*.deb && rm /tmp/nvidia-docker*.deb

        # Test nvidia-smi
        sudo nvidia-docker run --rm nvidia/cuda:8.0 nvidia-smi


        sudo mkdir -p /opt/nvidia-driver/
        sudo cp -r /var/lib/nvidia-docker/volumes/nvidia_driver/* /opt/nvidia-driver/
        NV_DRIVER=/opt/nvidia-driver/$NVIDIA_VERSION
        sudo ln -s $NV_DRIVER /opt/nvidia-driver/current
fi