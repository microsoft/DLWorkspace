#!/bin/bash
mv /var/log /mnt/log
ln -s /mnt/log /var/log
mkdir -p /mnt/lib/docker 
mkdir -p /mnt/lib/mysql
mkdir -p /mnt/lib/influxdb
ln -s /mnt/lib/docker /var/lib/docker
ln -s /mnt/lib/mysql /var/lib/mysql
ln -s /mnt/lib/influxdb /var/lib/influxdb


