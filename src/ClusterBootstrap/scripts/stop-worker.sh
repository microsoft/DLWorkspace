#!/bin/bash
# Stop Kubernete worker (used by deploy.py updateworker)

sudo systemctl stop kubelet

# may have issue to clear all docker images. need other mechanism 
# sudo systemctl start docker
# docker rm -f $(docker ps -a -q)
sudo systemctl stop docker
sudo systemctl stop flanneld
sudo systemctl stop bootstrap
sudo systemctl stop reportcluster
sudo rm /etc/kubernetes/manifests/kube-proxy.yaml
sudo mkdir -p /etc/flannel
