#!/bin/bash


tbip=`kubectl describe pods -l run=$1 | grep Node | awk '{print $2}'`
tpport=`kubectl describe svc interactive-$1 | grep NodePort: | awk '{print $3}'`
echo $tbip:$tpport 
