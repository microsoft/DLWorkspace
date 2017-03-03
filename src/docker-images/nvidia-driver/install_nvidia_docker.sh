#!/bin/bash
docker run --privileged -v /opt/nvidia-driver:/opt/nvidia-driver -v /opt/nvidia-docker:/opt/nvidia-docker -v /opt/bin:/opt/bin -v /dev:/dev mlcloudreg.westus.cloudapp.azure.com:5000/nvidia_driver:GeForce375.20 && \
NVDEVS=`/usr/sbin/lspci | /bin/grep -i NVIDIA`  && \
N3D=`/bin/echo "$NVDEVS" | /bin/grep "3D controller" | /usr/bin/wc -l`  && \
NVGA=`/bin/echo "$NVDEVS" | /bin/grep "VGA compatible controller" | /usr/bin/wc -l`  && \
N=`/usr/bin/expr $N3D + $NVGA - 1`  && \
for i in `/usr/bin/seq 0 $N`; do  && \
/bin/mknod -m 666 /dev/nvidia$i c 195 $i  && \
done  && \
/bin/mknod -m 666 /dev/nvidiactl c 195 255  && \
D=`/bin/grep nvidia-uvm /proc/devices | /usr/bin/awk '{print $1}'`  && \
/bin/mknod -m 666 /dev/nvidia-uvm c $D 0  && \
/bin/ls -alh /dev | /bin/grep -i nvidia  && \
sudo LD_LIBRARY_PATH=/opt/nvidia-driver/volumes/nvidia_driver/375.20/lib64/ /opt/bin/nvidia-docker-plugin  && \
sudo mkdir -p /etc/ld.so.conf.d/  && \
sudo tee /etc/ld.so.conf.d/nvidia-ml.conf <<< /opt/nvidia-driver/volumes/nvidia_driver/375.20/lib64  && \
sudo ldconfig  && \
sudo /opt/bin/nvidia-docker-plugin