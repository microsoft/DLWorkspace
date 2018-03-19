#!/bin/bash
sudo mv /var/log /mnt/log
sudo ln -s /mnt/log /var/log
sudo mkdir -p /mnt/lib/docker 
sudo mkdir -p /mnt/lib/mysql
sudo mkdir -p /mnt/lib/influxdb
if [ ! -L /var/lib/docker ]; then
   sudo ln -s /mnt/lib/docker /var/lib/docker
fi
if [ ! -L /var/lib/mysql ]; then
    # It is a symlink!
    # Symbolic link specific commands go here.
    sudo ln -s /mnt/lib/mysql /var/lib/mysql
fi
if [ ! -L /var/lib/influxdb ]; then 
    sudo ln -s /mnt/lib/influxdb /var/lib/influxdb
fi

