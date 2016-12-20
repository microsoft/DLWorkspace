#!/bin/bash
/bin/mkdir -p /opt

if [ ! -f /nvidia_driver.tar ]; then
    /bin/bash -c "until ping -c1 192.168.1.20; do sleep 1; done;"
    wget http://192.168.1.20/nvidia_driver.tar
    docker load < nvidia_driver.tar
fi


docker run --rm -v /var/lib/nvidia-docker:/opt/nvidia-docker-volume --privileged mlcloudreg.westus.cloudapp.azure.com:5000/nvidia_driver:GeForce375.20

#modprobe nvidia
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
 sudo wget -P /tmp http://192.168.1.20/nvidia-docker_1.0.0.rc.3_amd64.tar.xz && \
 sudo tar --strip-components=1 -C /opt/nvidia-docker/bin -xvf /tmp/nvidia-docker*.tar.xz && sudo rm /tmp/nvidia-docker*.tar.xz && \
 sudo mkdir -p /etc/ld.so.conf.d/ && \
 sudo tee /etc/ld.so.conf.d/nvidia-ml.conf <<< /var/lib/nvidia-docker/volumes/nvidia_driver/375.20/lib64 && \
 sudo ldconfig && \
 sudo -b nohup /opt/nvidia-docker/bin/nvidia-docker-plugin > /tmp/nvidia-docker.log && \
 cat /tmp/nvidia-docker.log  && \
 export PATH=$PATH:/opt/nvidia-docker/bin

