#FROM mlcloudreg.westus.cloudapp.azure.com:5000/dlworkspace/hyperkube:v1.5.0_coreos.multigpu
FROM ubuntu:16.04
MAINTAINER Sanjeev Mehrotra <sanjeevm0@hotmail.com>

RUN apt-get update; apt-get install -y --no-install-recommends apt-transport-https \
        wget \
        vim \
        curl \
        net-tools \
        iptables \
        apt-utils

COPY ./hyperkube /hyperkube
COPY ./kubelet /kubelet
COPY ./kubectl /kubectl
COPY ./crishim /crishim
COPY ./kube-scheduler /kube-scheduler
COPY ./nvidiagpuplugin.so /nvidiagpuplugin.so
RUN mkdir -p /schedulerplugins
COPY ./gpuschedulerplugin.so /schedulerplugins/gpuschedulerplugin.so

