#!/bin/bash

# nv_peer_mem should be installed on machines supporting GPUDirect.

set -ex

export DEBIAN_FRONTEND=noninteractive
export STAGE_DIR=/tmp

sudo rm -rf ${STAGE_DIR}/nv_peer_memory
sudo mkdir -p ${STAGE_DIR}
sudo git clone https://github.com/Mellanox/nv_peer_memory.git ${STAGE_DIR}/nv_peer_memory
cd ${STAGE_DIR}/nv_peer_memory
sudo ./build_module.sh
cd ${STAGE_DIR}
sudo tar xzf ${STAGE_DIR}/nvidia-peer-memory_1.0.orig.tar.gz
cd ${STAGE_DIR}/nvidia-peer-memory-1.0
sudo apt-get install -y dkms
sudo dpkg-buildpackage -us -uc
sudo dpkg -i ${STAGE_DIR}/nvidia-peer-memory_1.0-8_all.deb
sudo dpkg -i ${STAGE_DIR}/nvidia-peer-memory-dkms_1.0-8_all.deb

sudo service nv_peer_mem restart
sudo service nv_peer_mem status
