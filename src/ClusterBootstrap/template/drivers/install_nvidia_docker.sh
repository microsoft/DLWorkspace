#!/bin/bash
docker run --privileged -v /opt/nvidia-driver:/opt/nvidia-driver -v /opt/nvidia-docker:/opt/nvidia-docker -v /opt/bin:/opt/bin -v /dev:/dev mlcloudreg.westus.cloudapp.azure.com:5000/nvidia_driver:GeForce375.20 && \
sudo mkdir -p /etc/ld.so.conf.d/  && \
sudo tee /etc/ld.so.conf.d/nvidia-ml.conf <<< /opt/nvidia-driver/volumes/nvidia_driver/375.20/lib64  && \
sudo ldconfig  && \
sudo /opt/bin/nvidia-docker-plugin