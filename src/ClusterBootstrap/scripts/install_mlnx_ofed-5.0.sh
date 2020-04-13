#!/bin/bash

# MLNX OFED Driver 5.0-1.0.0.0

set -ex

export DEBIAN_FRONTEND=noninteractive
export STAGE_DIR=/tmp

sudo mkdir -p ${STAGE_DIR}
cd ${STAGE_DIR}
sudo wget -q -O - http://www.mellanox.com/downloads/ofed/MLNX_OFED-5.0-1.0.0.0/MLNX_OFED_LINUX-5.0-1.0.0.0-ubuntu18.04-x86_64.tgz | sudo tar xzf -
cd MLNX_OFED_LINUX-5.0-1.0.0.0-ubuntu18.04-x86_64
sudo ./mlnxofedinstall --force
sudo /etc/init.d/openibd restart
