#!/bin/bash
sudo systemctl stop kubelet
sudo docker rm -f $(docker ps -a | grep 'k8s_kube\|k8s_POD' | awk '{print $1}')

sudo systemctl disable kubelet

sudo rm /etc/systemd/system/kubelet.service

sudo rm -r /etc/kubernetes
sudo rm /opt/kubelet.sh
sudo rm /opt/bin/kubelet
sudo rm -r /etc/kubernetes
sudo rm -rf /opt/cni

sudo mkdir -p /etc/kubernetes
sudo mkdir -p /etc/kubernetes/manifests
sudo mkdir -p /etc/kubernetes/ssl/
sudo mkdir -p /etc/ssl/etcd
sudo mkdir -p /opt/bin
sudo mkdir -p /opt/cni/bin
{{'sudo mkdir -p '~cnf["kubeletlogdir"]~'/kubelet' if "kubeletlogdir" in cnf}}
