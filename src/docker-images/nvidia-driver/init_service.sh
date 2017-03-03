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

nvidia-docker run --rm nvidia/cuda nvidia-smi

cp -r /var/lib/nvidia-docker/* /opt/nvidia-docker-volume
cp /opt/init_devices.sh /opt/nvidia-driver

/bin/lsmod | /bin/grep -i nvidia

# Count the number of NVIDIA controllers found.
NVDEVS=`/usr/sbin/lspci | /bin/grep -i NVIDIA`
N3D=`/bin/echo "$NVDEVS" | /bin/grep "3D controller" | /usr/bin/wc -l`
NVGA=`/bin/echo "$NVDEVS" | /bin/grep "VGA compatible controller" | /usr/bin/wc -l`
N=`/usr/bin/expr $N3D + $NVGA - 1`
for i in `/usr/bin/seq 0 $N`; do
/bin/mknod -m 666 /dev/nvidia$i c 195 $i
done
/bin/mknod -m 666 /dev/nvidiactl c 195 255

# Find out the major device number used by the nvidia-uvm driver
D=`/bin/grep nvidia-uvm /proc/devices | /usr/bin/awk '{print $1}'`
/bin/mknod -m 666 /dev/nvidia-uvm c $D 0

/bin/ls -alh /dev | /bin/grep -i nvidia

 sudo mkdir -p /opt/nvidia-docker/bin && \
 sudo wget -P /tmp https://github.com/NVIDIA/nvidia-docker/releases/download/v1.0.0-rc.3/nvidia-docker_1.0.0.rc.3_amd64.tar.xz && \
 sudo tar --strip-components=1 -C /opt/nvidia-docker/bin -xvf /tmp/nvidia-docker*.tar.xz && sudo rm /tmp/nvidia-docker*.tar.xz && \
 sudo mkdir -p /etc/ld.so.conf.d/ && \
 sudo tee /etc/ld.so.conf.d/nvidia-ml.conf <<< /var/lib/nvidia-docker/volumes/nvidia_driver/375.20/lib64 && \
 sudo ldconfig && \
 cat /tmp/nvidia-docker.log  && \
 export PATH=$PATH:/opt/nvidia-docker/bin

sudo mkdir -p /opt/cuda/cudatoolkit
cd /opt/cuda
sudo wget -O /opt/cuda/cuda_8.0.44_linux.run http://ccsdatarepo.westus.cloudapp.azure.com/data/cuda/cuda_8.0.44_linux.run
sudo chmod +x /opt/cuda/cuda_8.0.44_linux.run
sudo /opt/cuda/cuda_8.0.44_linux.run -silent --toolkit --toolkitpath=/opt/cuda/cudatoolkit



#fi
sleep infinity

