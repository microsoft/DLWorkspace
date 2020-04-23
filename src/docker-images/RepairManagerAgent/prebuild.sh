#!/bin/bash 
# This command will be executed under directory 
# src/ClusterBootstrap/deploy/docker-images/.../
rm -rf RepairManagerAgent
cp -r ../../../../RepairManagerAgent RepairManagerAgent
