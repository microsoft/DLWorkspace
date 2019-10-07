#!/bin/bash

role=$1

cd ../ClusterBootstrap/
./deploy.py kubectl get nodes | awk '$2=="Ready" {print $1}' | grep $role | sort > ../ContinuousIntegration/${role}_ready
cd ../ContinuousIntegration

CLUSTER_NAME=$(grep cluster_name ../ClusterBootstrap/cluster.yaml | awk '{print $2}' | tr '[:upper:]' '[:lower:]')
if [ ! -e ${role}_name_list ];then
	grep -B3 "role: ${role}" ../ClusterBootstrap/cluster.yaml | grep ${CLUSTER_NAME}- | sed 's/://g' | awk '{print $1}' | sort > ${role}_name_list
fi;

nonready=`diff ${role}_ready ${role}_name_list`
echo $nonready
rm ${role}_ready
if [ ! -z "$nonready" ]; then
	echo "There're non-ready ${role} nodes: $nonready"
	exit 1
fi;