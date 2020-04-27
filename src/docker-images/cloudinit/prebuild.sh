#!/bin/bash 
# This command will be executed under directory 
# src/ClusterBootstrap/deploy/docker-images/.../

# commented because we want to make it compatible with deployment pipeline v2.0
# rm -rf worker_cld_init.tar
# cd ../../../
# python deploy.py packcloudinit
# cd deploy/docker-images/cloudinit
cp ../../../cloudinit.tar .