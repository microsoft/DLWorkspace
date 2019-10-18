#!/bin/bash

# need to read in config and render it here, maybe also requires python script 
# if want to check folder/disk/dns

# verify docker installation

# with below version, need to copy this script to all workers and run `./pssh_worker.sh "bash check_machine.sh"` on devbox

type=$(echo "$1" | awk '{print tolower($0)}')

if [ $type == "gpu" ]; then
	gpu=$(nvidia-smi -L | wc -l)
	if [ $gpu == 1 ]; then
		echo "Nvidia driver fine"
	else
		exit 1
	fi;
	# verify nvidia-docker
	nvdadokr=$(nvidia-docker -v | wc -l)
	if [ $nvdadokr == 1 ]; then
		echo "nvdadokr fine"
	else
		exit 1
	fi;
fi;
docker=$(docker -v | wc -l)
if [ $docker == 1 ]; then
	echo "docker fine"
else
	exit 1
fi;
echo "machine level validation (docker and gpu driver) passed"
