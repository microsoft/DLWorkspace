#!/bin/bash

set -ex

# This script assume code repo and config repo are clean

CODE_BASE_DIR="/mnt/dev/dlts"
CODE_UPSTREAM_REMOTE="upstream"
CONFIG_DIR="$HOME/dev/Deployment"

if [ $# != 2 ] ; then
    echo Usage: $0 commit_hash cluster_name
    exit 1
fi

version=$1
cluster_name=$2

function update_config() {
    (
        cd $CONFIG_DIR
        git fetch origin
        git merge origin/master
    )
}

function update_code() {
    (
        cd $CODE_BASE_DIR/$cluster_name
        git checkout . # make code path clean
        git fetch --all ; git checkout $version
    )
}

function restore_config() {
    (
        cd $CODE_BASE_DIR/$cluster_name/src/ClusterBootstrap
        ./ctl.py restorefromdir $CONFIG_DIR/$cluster_name
    )
}


function update_service_config() {
    (
        cd $CODE_BASE_DIR/$cluster_name/src/ClusterBootstrap
        for i in $@ ; do
            ./ctl.py svc configupdate $i
        done
    )
}

function push_docker_images() {
    (
        cd $CODE_BASE_DIR/$cluster_name/src/ClusterBootstrap
        for i in $@ ; do
            ./ctl.py docker push $i
        done
    )
}

function restart_services() {
    (
        cd $CODE_BASE_DIR/$cluster_name/src/ClusterBootstrap
        for i in $@ ; do
            ./ctl.py svc render $i
            ./ctl.py svc stop $i
            ./ctl.py svc start $i
        done
    )
}

function check() {
    (
        cd $CODE_BASE_DIR/$cluster_name/src/ClusterBootstrap
        watch -d -n 1 './ctl.py kubectl get pod --all-namespaces | grep -v Running'
        watch -d -n 1 './ctl.py kubectl get pod --all-namespaces | grep manager'
    )
}

update_config

update_code

restore_config

update_service_config `cat <(cat << EOF
restfulapi
storagemanager
repairmanager
dashboard
EOF
) | grep -v '#' `

push_docker_images `cat <(cat << EOF
restfulapi
azure-blob-adapter
dashboard
email-sender
gpu-reporter
grafana
init-container
job-exporter
job-insighter
reaper
repairmanager
repairmanageragent
repairmanageretcd
storagemanager
user-synchronizer
watchdog
EOF
) | grep -v '#' `

restart_services `cat <(cat << EOF
restfulapi
jobmanager
monitor
dashboard
job-insighter
logging
repairmanager
repairmanageragent
storagemanager
EOF
) | grep -v '#' `

check
