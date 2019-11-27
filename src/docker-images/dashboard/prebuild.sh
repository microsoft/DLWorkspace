#!/bin/bash 
# This command will be executed under directory 
# src/ClusterBootstrap/deploy/docker-images/.../

rm -rf dashboard
cd ../../../
python deploy.py webui
cd deploy/docker-images/dashboard
cp -r ../../../../dashboard dashboard
