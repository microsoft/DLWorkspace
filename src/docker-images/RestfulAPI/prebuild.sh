#!/bin/bash 
# This command will be executed under directory 
# src/ClusterBootstrap/deploy/docker-images/.../

rm -rf Jobs_Templete
rm -rf utils
rm -rf RestAPI
rm -rf ClusterManager
cp -r ../../../../Jobs_Templete Jobs_Templete
cp -r ../../../../utils utils
cp -r ../../../../RestAPI RestAPI
cp -r ../../../../ClusterManager ClusterManager
cp -r ../../../../ClusterBootstrap/deploy/bin/kubectl kubectl
