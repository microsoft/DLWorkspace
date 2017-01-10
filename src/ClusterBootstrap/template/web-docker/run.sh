#!/bin/bash
cd /root/certificate-service/
python /root/certificate-service/genkey-restapi.py &
#/usr/sbin/apache2 -D FOREGROUND 
service apache2 start
sleep infinity