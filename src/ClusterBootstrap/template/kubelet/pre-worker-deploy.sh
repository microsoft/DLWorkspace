#!/bin/bash
sudo systemctl stop kubelet
sudo docker rm -f $(docker ps -a | grep 'k8s_kube\|k8s_POD' | awk '{print $1}')
sudo systemctl stop docker
sudo systemctl stop flanneld

sudo rm /etc/systemd/system/flanneld.service.d/40-ExecStartPre-symlink.conf
sudo rm /etc/systemd/system/docker.service.d/40-flannel.conf
sudo rm /etc/flannel/options.env
sudo systemctl disable kubelet
sudo systemctl disable reportcluster
sudo systemctl disable bootstrap
sudo systemctl disable checkinternet
sudo systemctl disable nvidia-docker
sudo systemctl disable nvidia-driver

sudo rm /etc/systemd/system/kubelet.service
sudo rm /etc/systemd/system/reportcluster.service
sudo rm /etc/systemd/system/bootstrap.service
sudo rm /etc/systemd/system/checkinternet.service
sudo rm /etc/systemd/system/nvidia-docker.service
sudo rm /etc/systemd/system/nvidia-driver.service


sudo rm -r /etc/kubernetes
sudo rm /opt/kubelet.sh
sudo rm /opt/bin/kubelet
sudo rm -r /etc/kubernetes
sudo rm -r /etc/systemd/system/reportcluster.service

sudo mkdir -p /etc/kubernetes
sudo mkdir -p /etc/systemd/system/flanneld.service.d
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo mkdir -p /etc/flannel
sudo mkdir -p /etc/kubernetes/manifests
sudo mkdir -p /etc/kubernetes/ssl/
sudo mkdir -p /etc/ssl/etcd
sudo mkdir -p /opt/bin
{{'sudo mkdir -p '~cnf["kubeletlogdir"]~'/kubelet' if "kubeletlogdir" in cnf}}

