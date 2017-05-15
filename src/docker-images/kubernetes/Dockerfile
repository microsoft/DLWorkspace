#FROM mlcloudreg.westus.cloudapp.azure.com:5000/dlworkspace/hyperkube:v1.5.0_coreos.multigpu
FROM ubuntu:16.04
MAINTAINER Sanjeev Mehrotra <sanjeevm0@hotmail.com>

COPY ./deploy/bin/hyperkube /hyperkube
COPY ./deploy/bin/kubelet /kubelet
COPY ./deploy/bin/kubectl /kubectl
