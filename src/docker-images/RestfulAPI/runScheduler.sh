#!/bin/bash
rm /DLWorkspace/src/utils/config.yaml
ln -s /RestfulAPI/config.yaml /DLWorkspace/src/utils/config.yaml
# /pullsrc.sh &

cd /DLWorkspace/src/ClusterManager
python3 /DLWorkspace/src/ClusterManager/cluster_manager.py
