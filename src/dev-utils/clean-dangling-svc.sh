#!/bin/bash

# Used to clean dangling svc, should put this script in the same directory where ctl.py exist
# user should call this script with no args, if provided with 1 arg, it will print svc label if
# the svc is dangling.

set -e

NUM_PROC=20

if [ $# != 0 -a $# != 1 ] ; then
    echo "Usage: $0 [svc]"
    exit 1
fi

if [ $# == 0 ] ; then
    ./ctl.py kubectl get svc | grep "^e-" | cut -d " " -f 1 | xargs -n 1 -P $NUM_PROC ./$0 | uniq | \
        xargs -n 1 -P $NUM_PROC ./ctl.py kubectl delete svc -l
elif [ $# == 1 ] ; then
    svc_name=$1

    label=`./ctl.py kubectl describe svc $svc_name | grep jobId | cut -d : -f 2 | sed "s/ //g"`
    ./ctl.py kubectl get pod -l $label 2>&1 | grep "No resources found" > /dev/null
    rtn=$?
    if [ $rtn == 0 ] ; then
        echo $label
    fi
else
    echo "Usage: $0 [svc]"
    exit 1
fi
