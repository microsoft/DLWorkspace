#!/bin/bash
ln -s /RestfulAPI/config.yaml /DLWorkspace/src/utils/config.yaml

cd /DLWorkspace/src/ClusterManager
python3 /DLWorkspace/src/ClusterManager/cluster_manager.py
