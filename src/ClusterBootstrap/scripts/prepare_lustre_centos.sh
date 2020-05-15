#!/bin/bash

set -x

sudo yum install -y python3
sudo pip3 install pyyaml

distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.repo | \
  sudo tee /etc/yum.repos.d/nvidia-docker.repo

sudo yum install -y nvidia-docker2
sudo pkill -SIGHUP dockerd

