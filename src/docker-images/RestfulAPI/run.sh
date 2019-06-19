#!/bin/bash
rm /DLWorkspace/src/utils/config.yaml
ln -s /RestfulAPI/config.yaml /DLWorkspace/src/utils/config.yaml
#python /DLWorkspace/src/RestAPI/dlws-restapi.py
# /pullsrc.sh &
chmod -R 0777 /var/log/apache2
echo "Change permission on /var/log/apache2"

#/usr/sbin/apache2ctl -D FOREGROUND
apachectl start
sleep infinity
#while true; do
#	sleep 1800
#	apachectl restart
#done