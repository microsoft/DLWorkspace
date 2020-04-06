#!/bin/bash

set -e

kubectl create priorityclass job-priority --value=1000 --description="job pod priority" --dry-run -o yaml | kubectl replace --force=true -f -
kubectl create priorityclass inference-job-priority --value=100 --description="inference job priority" --dry-run -o yaml | kubectl replace --force=true -f -

ln -s /RestfulAPI/config.yaml /DLWorkspace/src/utils/config.yaml

cd /DLWorkspace/src/ClusterManager
python3 /DLWorkspace/src/ClusterManager/cluster_manager.py
