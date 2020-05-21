#!/bin/bash

set -ex

# This script assume code repo and config repo are clean

CODE_BASE_DIR="/mnt/dev/dlts"
CODE_UPSTREAM_REMOTE="upstream"
CONFIG_DIR="$HOME/dev/Deployment"

if [ $# != 2 ] ; then
    echo Usage: $0 cluster_name version branch
    exit 1
fi

cluster_name=$1
version=$2

#(cd $CONFIG_DIR ; git fetch origin ; git merge origin/master)

cd $CODE_BASE_DIR/$cluster_name

git checkout . # make code path clean

git fetch --all ; git checkout $CODE_UPSTREAM_REMOTE/$version -b $version

cd src/ClusterBootstrap

./ctl.py restorefromdir $CONFIG_DIR/$cluster_name

# start to deploy

for i in `echo restfulapi storagemanager repairmanager dashboard`
do
    ./ctl.py svc configupdate $i
done

./ctl.py kubectl label node `grep infra01: status.yaml  | sed 's/ *:*//g'` job-insighter=active

for i in `echo RestfulAPI azure-blob-adapter dashboard email-sender gpu-reporter grafana init-container job-exporter job-insighter reaper RepairManager RepairManagerAgent RepairManagerEtcd StorageManager user-synchronizer watchdog`
do
    ./ctl.py docker push $i
done

for i in `echo restfulapi jobmanager monitor dashboard job-insighter logging repairmanager repairmanageragent storagemanager `
do
    ./ctl.py svc render $i
    ./ctl.py svc stop $i
    ./ctl.py svc start $i
done

watch -d -n 1 './ctl.py kubectl get pod --all-namespaces | grep -v Running'
watch -d -n 1 './ctl.py kubectl get pod --all-namespaces | grep manager'
