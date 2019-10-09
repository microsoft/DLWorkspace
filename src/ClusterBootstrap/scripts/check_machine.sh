#!/bin/bash

# need to read in config and render it here, maybe also requires python script 
# if want to check folder/disk/dns

# verify docker installation

# with below version, need to copy this script to all workers and run `./pssh_worker.sh "bash check_machine.sh"` on devbox
gpu=$(nvidia-smi -L | wc -l)
if [ $gpu==1 ]; then
	echo "Nvidia driver fine"
else
	exit 1	
fi;
docker=$(docker -v | wc -l)
if [ $docker==1 ]; then
	echo "docker fine"
else
	exit 1	
fi;
# verify nvidia-docker 
nvdadokr=$(nvidia-docker -v | wc -l)
if [ $nvdadokr==1 ]; then
	echo "nvdadokr fine"
else 
	exit 1
fi;


# set -ex

# ./pssh_worker.sh "mustbewrong -v | wc -l"


# ./pssh_worker.sh "docker -v | wc -l"
# # verify nvidia-docker 
# ./pssh_worker.sh "nvidia-docker -v | wc -l"