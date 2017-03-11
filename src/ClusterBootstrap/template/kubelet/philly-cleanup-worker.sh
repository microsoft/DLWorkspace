#!/bin/bash
# Stop and Cleanup Kubernete worker (used by deploy.py updateworker)
sudo systemctl stop kubelet
sudo docker rm -f $(docker ps -a | grep 'k8s_kube\|k8s_POD' | awk '{print $1}')
sudo systemctl disable kubelet

sudo rm /etc/systemd/system/kubelet.service
sudo rm -r /etc/kubernetes
sudo rm /opt/bin/kubelet
sudo rm -r /etc/kubernetes
