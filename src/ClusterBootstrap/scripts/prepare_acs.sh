#!/bin/bash

sudo apt-get update
sudo apt-get install -y gcc
sudo apt-get install -y make
sudo apt-get install -qqy linux-headers-`uname -r`

wget -P /tools http://us.download.nvidia.com/XFree86/Linux-x86_64/381.22/NVIDIA-Linux-x86_64-381.22.run
chmod +x /tools/NVIDIA-Linux-x86_64-381.22.run
sh /tools/NVIDIA-Linux-x86_64-381.22.run -a -s

sudo apt install -y nvidia-modprobe

sudo rm -r /opt/nvidia-driver || true

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

sudo systemctl restart kubelet.service

if [ -f /etc/NetworkManager/NetworkManager.conf ]; then
	sed "s/^dns=dnsmasq$/#dns=dnsmasq/" /etc/NetworkManager/NetworkManager.conf > /tmp/NetworkManager.conf && sudo mv /tmp/NetworkManager.conf /etc/NetworkManager/NetworkManager.conf
	sudo service network-manager restart
fi