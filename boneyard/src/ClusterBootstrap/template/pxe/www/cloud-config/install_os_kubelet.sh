#!/bin/sh

wget http://192.168.1.20/pxe-coreos-kube.yml
sudo coreos-install -d /dev/sda -c pxe-coreos-kube.yml -b http://192.168.1.20/coreos -V 1185.5.0

sudo shutdown -h now

