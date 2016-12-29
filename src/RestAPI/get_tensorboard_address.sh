#!/bin/bash


tbip=`kubectl describe pods -l run=$1 | grep Node | awk '{print $2}'`
tpport=`kubectl describe svc $1 | grep NodePort: | awk '{print $3}'`
echo "tensorboard: $1 is running at: $tbip:$tpport" 
