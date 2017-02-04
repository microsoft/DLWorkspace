#!/bin/bash
# start Kubernete worker (used by deploy.py updateworker)

sudo systemctl daemon-reload

#sudo systemctl start bootstrap
sudo systemctl start flanneld
sudo systemctl start docker

sudo systemctl start kubelet

sudo systemctl start reportcluster
sudo systemctl enable reportcluster
sudo systemctl enable kubelet

sudo journalctl -u kubelet
