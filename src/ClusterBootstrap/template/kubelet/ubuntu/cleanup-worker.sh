#!/bin/bash
# Stop and Cleanup Kubernete worker (used by deploy.py updateworker)
sudo systemctl stop kubelet
sudo systemctl stop kubecri
sudo docker rm -f $(docker ps -a | grep 'k8s_kube\|k8s_POD' | awk '{print $1}')
sudo systemctl disable kubelet
sudo systemctl disable kubecri

sudo rm /etc/systemd/system/kubelet.service
sudo rm /etc/systemd/system/kubecri.service
sudo rm -r /etc/kubernetes
sudo rm /opt/bin/kubelet
sudo rm /opt/bin/crishim
sudo rm -r /usr/local/KubeExt/devices
sudo rm -r /etc/kubernetes
