#!/bin/bash

printf "o\nn\np\n1\n\n\nw\n" | sudo fdisk /dev/sdc
sudo mkfs.ext4 /dev/sdc1
sleep 10
sudo mkdir /data
uuid=$(ls -l /dev/disk/by-uuid/ | grep sdc1 | awk '{print $9}')
echo "UUID=$uuid       /data        ext4   defaults,discard        0 0" | sudo tee -a /etc/fstab
sudo mount /data

sudo mv /var/log /var/log.bak
sudo mkdir -p /data/log
sudo rm -r /var/log ; sudo ln -s /data/log /var/log
sudo mv /var/log.bak/* /data/log
sudo rm -r /var/log.bak
sudo mkdir -p /data/lib/docker
sudo mkdir -p /data/lib/mysql
sudo mkdir -p /data/lib/influxdb
if [ ! -L /var/lib/docker ]; then
   sudo ln -s /data/lib/docker /var/lib/docker
fi
if [ ! -L /var/lib/mysql ]; then
    # It is a symlink!
    # Symbolic link specific commands go here.
    sudo ln -s /data/lib/mysql /var/lib/mysql
fi
if [ ! -L /var/lib/influxdb ]; then
    sudo ln -s /data/lib/influxdb /var/lib/influxdb
fi


