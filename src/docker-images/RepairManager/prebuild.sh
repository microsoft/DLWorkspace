#!/bin/bash 
# This command will be executed under directory 
# src/ClusterBootstrap/deploy/docker-images/.../
rm -rf RepairManager
cp -r ../../../../RepairManager RepairManager
cp -r ../../../../ClusterBootstrap/deploy/bin/kubectl kubectl
# ./deploy/docker-images/RepairManager/RepairManager/config/email-config.yaml
# ./deploy/docker-images/RepairManager/RepairManager/config/rule-config.yaml
# ./deploy/docker-images/RepairManager/RepairManager/config/ecc-config.yaml