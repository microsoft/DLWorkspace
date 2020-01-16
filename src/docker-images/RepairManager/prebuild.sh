#!/bin/bash 
# This command will be executed under directory 
# src/ClusterBootstrap/deploy/docker-images/.../

rm -rf RepairManager
cp -r ../../../../RepairManager RepairManager

# Render config file for email credentials
cd ../../../
./deploy.py rendertemplate ./deploy/docker-images/RepairManager/RepairManager/config/email-config.yaml ./deploy/docker-images/RepairManager/RepairManager/config/email-config.yaml
./deploy.py rendertemplate ./deploy/docker-images/RepairManager/RepairManager/config/rule-config.yaml ./deploy/docker-images/RepairManager/RepairManager/config/rule-config.yaml
./deploy.py rendertemplate ./deploy/docker-images/RepairManager/RepairManager/config/ecc-config.yaml ./deploy/docker-images/RepairManager/RepairManager/config/ecc-config.yaml
cd ./deploy/docker-images/RepairManager/

cp -r ../../../../ClusterBootstrap/deploy/bin/kubectl kubectl
