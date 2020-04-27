#!/bin/bash

stage=$1

declare -a infra=("k8s_weave-npc_weave-net" "k8s_weave_weave-net" "k8s_kube-proxy_kube-proxy" "k8s_kube-apiserver_kube-apiserver-" "k8s_kube-controller-manager_kube-controller-manager" "k8s_kube-scheduler_kube-scheduler" "etcd")
declare -a worker=("k8s_weave_weave-net" "k8s_kube-proxy_kube-proxy" "k8s_weave-npc_weave-net")
postlbl="k8s_nvidia-device-plugin-ctr_nvidia-device-plugin-daemonset"
declare -a services=("k8s_mysql_mysql" "k8s_jobmanager_jobmanager" "k8s_restfulapi_restfulapi" "k8s_dashboard_dashboard")

dockerps=`docker ps --format '{{.Names}}'`

if [ $stage == "infra" ]; then
	for i in "${infra[@]}"; do
		if [[ ! $dockerps =~ $i ]]; then
			echo "$i not found"
			exit 1
		fi
	done
elif [ $stage == "worker" ]; then
	for i in "${worker[@]}"; do
		if [[ ! $dockerps =~ $i ]]; then
			echo "$i not found"
			exit 1
		fi
	done
elif [ $stage == "postlbl" ]; then
	if [[ ! $dockerps =~ $postlbl ]]; then
		echo "$postlbl not found"
		exit 1
	fi
elif [ $stage == "services" ]; then
	for i in "${services[@]}"; do
		if [[ ! $dockerps =~ $i ]]; then
			echo "$i not found"
			exit 1
		fi
	done
fi
exit 0