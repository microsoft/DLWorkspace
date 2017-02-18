#!/bin/sh
wget http://192.168.1.20/pxe-kubemaster.yml
sudo coreos-install -d /dev/sda -c pxe-kubemaster.yml -b http://192.168.1.20/coreos
sudo shutdown -h now

