#!/bin/bash
# Install python on CoreOS base image
# Docker environment for development of DL workspace
sudo apt-get update -y
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
sudo apt-get remove docker docker-engine docker.io
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"
sudo apt-get update
sudo apt-get install -y docker-ce
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

        # https://askubuntu.com/questions/481414/install-nvidia-driver-instead-of-nouveau
        # Start from 10/05/2017 the following is needed. 
        if ! grep -q "blacklist nouveau" -F /etc/modprobe.d/blacklist.conf; then 
                echo "blacklist vga16fb" | sudo tee --append /etc/modprobe.d/blacklist.conf > /dev/null
                echo "blacklist nouveau" | sudo tee --append /etc/modprobe.d/blacklist.conf > /dev/null
                echo "blacklist rivafb" | sudo tee --append /etc/modprobe.d/blacklist.conf > /dev/null
                echo "blacklist nvidiafb" | sudo tee --append /etc/modprobe.d/blacklist.conf > /dev/null
                echo "blacklist rivatv" | sudo tee --append /etc/modprobe.d/blacklist.conf > /dev/null
                sudo apt-get remove -y --purge nvidia-*
                sudo update-initramfs -u
        fi


 #       NVIDIA_VERSION=384.98
 #       # make the script reexecutable after a failed download
 #       rm /tmp/NVIDIA-Linux-x86_64-$NVIDIA_VERSION.run
 #       wget -P /tmp http://us.download.nvidia.com/XFree86/Linux-x86_64/$NVIDIA_VERSION/NVIDIA-Linux-x86_64-$NVIDIA_VERSION.run
 #       chmod +x /tmp/NVIDIA-Linux-x86_64-$NVIDIA_VERSION.run
 #       sudo bash /tmp/NVIDIA-Linux-x86_64-$NVIDIA_VERSION.run -a -s

	sudo apt-get purge -y nvidia*
	sudo apt-get install -y nvidia-384
	


        sudo apt install -y nvidia-modprobe

        sudo rm -r /opt/nvidia-driver || true

        # Install nvidia-docker and nvidia-docker-plugin
        rm /tmp/nvidia-docker*.deb
        wget -P /tmp https://github.com/NVIDIA/nvidia-docker/releases/download/v1.0.1/nvidia-docker_1.0.1-1_amd64.deb
        sudo dpkg -i /tmp/nvidia-docker*.deb && rm /tmp/nvidia-docker*.deb

        # Test nvidia-smi
        sudo nvidia-docker run --rm dlws/cuda nvidia-smi


        sudo mkdir -p /opt/nvidia-driver/
        sudo cp -r /var/lib/nvidia-docker/volumes/nvidia_driver/* /opt/nvidia-driver/
        NVIDIA_VERSION=`/usr/bin/nvidia-smi -x -q | grep driver_version | sed -e 's/\t//' | sed -e 's/\ //' | sed -e 's/<driver_version>//' | sed -e 's/<\/driver_version>//'`
        NV_DRIVER=/opt/nvidia-driver/$NVIDIA_VERSION
        sudo ln -s $NV_DRIVER /opt/nvidia-driver/current
fi

# https://github.com/kubernetes/kubeadm/issues/610
sudo swapoff -a