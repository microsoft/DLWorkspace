#!/bin/bash 
# This command will be executed under directory 
# src/ClusterBootstrap/deploy/docker-images/.../

rm -rf worker_cld_init.tar
cd ../../../
python deploy.py packcloudinit
cd deploy/docker-images/cloudinit
cp ../../../worker_cld_init.tar .