#!/bin/bash
rm /DLWorkspace/src/utils/config.yaml
ln -s /RestfulAPI/config.yaml /DLWorkspace/src/utils/config.yaml
#python /DLWorkspace/src/RestAPI/dlws-restapi.py
# /pullsrc.sh &

#/usr/sbin/apache2ctl -D FOREGROUND
apachectl start
while true; do
	sleep 1800
	apachectl restart
done