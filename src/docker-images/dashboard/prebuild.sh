#!/bin/bash 
# This command will be executed under directory 
# src/ClusterBootstrap/deploy/docker-images/.../

rm -rf dashboard
cd ../../../
# assuming that we already executed python deploy.py webui to render corresponding files
cd deploy/docker-images/dashboard
cp -r ../../../../dashboard dashboard
