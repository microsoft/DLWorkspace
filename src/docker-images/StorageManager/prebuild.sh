#!/bin/bash 
# This command will be executed under directory 
# src/ClusterBootstrap/deploy/docker-images/.../

rm -rf utils
rm -rf StorageManager
cp -r ../../../../utils utils
cp -r ../../../../StorageManager StorageManager
