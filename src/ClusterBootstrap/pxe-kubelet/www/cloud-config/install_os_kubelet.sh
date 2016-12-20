#!/bin/sh

#wget http://192.168.1.20/pxe-cloud-config1.yml
wget http://192.168.1.20/pxe-coreos-kube.yml

sudo coreos-cloudinit --from-file=pxe-coreos-kube.yml


#sudo coreos-install -d /dev/sda -c pxe-cloud-config1.yml -b http://192.168.1.20/coreos
#sudo coreos-install -d /dev/sda -c pxe-coreos-kube.yml -b http://192.168.1.20/coreos


#sudo mount /dev/sda9 /mnt


#df -h

#sudo mkdir -p /mnt/etc/kubernetes
#sudo mkdir -p /mnt/srv/kubernetes

#wget -q -O - http://192.168.1.20/kubeconfig | base64 -d > "kubeconfig.json"
#sudo mv kubeconfig.json /mnt/srv/kubernetes/kubeconfig.json

#wget http://192.168.1.20/hyperkube.tar.gz
#sudo mkdir -p /mnt/opt/init
#sudo mv hyperkube.tar.gz /mnt/opt/init


#wget http://192.168.1.20/nvidia_driver.tar
#sudo mv nvidia_driver.tar /mnt/opt/init

#wget http://192.168.1.20/docker_kubelet.sh
#sudo mv docker_kubelet.sh /mnt/opt/init

#sudo reboot
#sudo shutdown -h now

