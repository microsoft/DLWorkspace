#!/bin/bash
#GPU_num=`lspci | grep NVIDIA | wc -l`
#if [ $GPU_num -eq 0 ]; then
#    echo "No GPU"
#else
sudo rmmod nvidia_uvm
sudo rmmod nvidia_drm
sudo rmmod nvidia
cd /usr/src/kernels/linux && \
/usr/src/kernels/linux/scripts/config --disable CC_STACKPROTECTOR_STRONG && \
make modules_prepare && \
echo "#define UTS_RELEASE \""$(uname -r)"\"" > /usr/src/kernels/linux/include/generated/utsrelease.h && \
echo `uname -r` > /usr/src/kernels/linux/include/config/kernel.release && \
cd /opt/nvidia/nvidia_installers && \
service docker start && \
 ./NVIDIA-Linux-x86_64-375.20/nvidia-installer -q -a -n -s --kernel-source-path=/usr/src/kernels/linux/ && \
 insmod /opt/nvidia/nvidia_installers/NVIDIA-Linux-x86_64-375.20/kernel/nvidia.ko && \
 insmod /opt/nvidia/nvidia_installers/NVIDIA-Linux-x86_64-375.20/kernel/nvidia-uvm.ko && \
  tar --strip-components=1 -C /usr/bin -xvf /opt/nvidia-docker*.tar.xz && \
 sudo -b nohup nvidia-docker-plugin > /tmp/nvidia-docker.log

nvidia-docker run --rm nvidia/cuda nvidia-smi && \
cp -r /var/lib/nvidia-docker/* /opt/nvidia-driver && \
cp /opt/init_devices.sh /opt/nvidia-driver && \
sudo mkdir -p /opt/nvidia-docker/bin && \
sudo wget -P /tmp https://github.com/NVIDIA/nvidia-docker/releases/download/v1.0.0/nvidia-docker_1.0.0_amd64.tar.xz && \
sudo tar --strip-components=1 -C /opt/nvidia-docker/bin -xvf /tmp/nvidia-docker*.tar.xz && sudo rm /tmp/nvidia-docker*.tar.xz && \
sudo cp /opt/nvidia-docker/bin/* /opt/bin && \
/bin/lsmod | /bin/grep -i nvidia 