#!/bin/bash
# Stop and Cleanup Kubernete worker (used by deploy.py updateworker)
sudo systemctl stop kubelet
sudo docker rm -f $(docker ps -a | grep 'k8s_kube\|k8s_POD' | awk '{print $1}')
sudo systemctl stop docker
sudo systemctl stop flanneld
sudo systemctl disable kubelet
sudo rm /etc/systemd/system/flanneld.service.d/40-ExecStartPre-symlink.conf
sudo rm /etc/systemd/system/docker.service.d/40-flannel.conf
sudo rm /etc/flannel/options.env
sudo rm /etc/systemd/system/kubelet.service
sudo rm -r /etc/kubernetes
sudo rm /opt/bin/kubelet
sudo rm -r /etc/kubernetes
sudo systemctl start docker
sudo reboot
