#!/bin/bash

set -x

kubectl create priorityclass job-priority --value=1000 --description="non-preemptible job pod priority" --dry-run -o yaml | kubectl replace --force=true -f -
kubectl create priorityclass preemptible-job-priority --value=500 --description="preemptible job pod priority" --dry-run -o yaml | kubectl replace --force=true -f -
kubectl create priorityclass inference-job-priority --value=100 --description="inference job priority" --dry-run -o yaml | kubectl replace --force=true -f -

set -e

export KUBE_SERVER_VERSION=`kubectl version | gawk 'match($0, /Server Version:.*GitVersion:"v([^"]*)"/, a) {print a[1]}'`

ln -s /RestfulAPI/config.yaml /DLWorkspace/src/utils/config.yaml

cd /DLWorkspace/src/ClusterManager
python3 /DLWorkspace/src/ClusterManager/cluster_manager.py
