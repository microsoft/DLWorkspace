#!/bin/sh

wget http://192.168.1.20/pxe-coreos-kube.yml
sudo coreos-cloudinit --from-file=pxe-coreos-kube.yml

sudo shutdown -h now

