#!/bin/bash 
# This command will be executed under directory 
# src/ClusterBootstrap/deploy/docker-images/.../

rm -r ClusterPortal
bash -c 'cd ../../../ ; ./deploy.py rendertemplate ./template/RestfulAPI/config.yaml ./deploy/RestfulAPI/config.yaml'

cp -r ../../../../ClusterPortal ClusterPortal
cp ../../../deploy/RestfulAPI/config.yaml ./ClusterPortal/config.yaml
