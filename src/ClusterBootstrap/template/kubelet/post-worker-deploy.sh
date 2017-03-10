#!/bin/bash
sudo cp /etc/kubernetes/ssl/ca.pem /etc/ssl/etcd/ca.pem
sudo cp /etc/kubernetes/ssl/worker.pem /etc/ssl/etcd/worker.pem
sudo cp /etc/kubernetes/ssl/worker-key.pem /etc/ssl/etcd/worker-key.pem
sudo chmod +x /opt/bin/kubelet 
sudo systemctl daemon-reload
sudo systemctl stop kubelet
sudo systemctl stop docker
sudo systemctl stop flanneld
sudo systemctl start flanneld
sudo systemctl start docker
sudo systemctl start kubelet
sudo systemctl start rpc-statd
sudo systemctl enable flanneld
sudo systemctl enable kubelet