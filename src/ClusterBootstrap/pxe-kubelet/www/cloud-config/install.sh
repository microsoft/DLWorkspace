#!/bin/sh

wget http://192.168.1.20/pxe-cloud-config.yml

sudo coreos-cloudinit --from-file=pxe-cloud-config.yml

sudo mkdir -p /etc/kubernetes
sudo mkdir -p /srv/kubernetes

wget -q -O - http://192.168.1.20/kubeconfig | base64 -d > "kubeconfig.json"
sudo mv kubeconfig.json /srv/kubernetes/kubeconfig.json

wget http://192.168.1.20/hyperkube.tar.gz
docker load < hyperkube.tar.gz


wget http://192.168.1.20/docker_kubelet.sh
sudo bash docker_kubelet.sh

#sudo coreos-install -d /dev/sda -c pxe-cloud-config.yml -b http://192.168.1.20/coreos

#sudo reboot
