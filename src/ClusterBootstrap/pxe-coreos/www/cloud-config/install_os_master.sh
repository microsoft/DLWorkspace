#!/bin/sh
wget http://192.168.1.20/pxe-kubemaster.yml
sudo coreos-install -d /dev/sda -c pxe-kubemaster.yml -b http://192.168.1.20/coreos -V 1185.5.0
sudo shutdown -h now

