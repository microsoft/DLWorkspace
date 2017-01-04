#!/bin/bash


podname=`kubectl describe pods -l run=$1 | grep "^Name:" | awk '{print $2}'`
log=`kubectl logs $podname`
echo $log
