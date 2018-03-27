#!/bin/bash

mkdir -p /var/log/apache2
chmod 0777 /var/log/apache2

# /pullsrc.sh &
#/usr/sbin/apache2ctl -D FOREGROUND
echo "Apache Server Start ..... "
apache2ctl start
cd /RecogServer/RecogServer
dotnet run --urls "http://*:1480"
while true; do
	sleep 1800
	apache2ctl restart
done
