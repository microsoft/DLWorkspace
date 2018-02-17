#!/bin/bash
sudo mv /var/log /mnt/log
sudo ln -s /mnt/log /var/log
sudo mkdir -p /mnt/lib/docker 
sudo mkdir -p /mnt/lib/mysql
sudo mkdir -p /mnt/lib/influxdb
sudo ln -s /mnt/lib/docker /var/lib/docker
sudo ln -s /mnt/lib/mysql /var/lib/mysql
sudo ln -s /mnt/lib/influxdb /var/lib/influxdb


