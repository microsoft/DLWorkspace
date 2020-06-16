#!/bin/bash

dir=`dirname $0`

dlts_scripts_file_name=${dir}/dlws-scripts.yaml
dlts_job_manager_config=${dir}/job-manager-config.yaml
dlts_job_manager_kubeconfig=${dir}/job-manager-kubeconfig.yaml

${dir}/../../../deploy/bin/kubectl create configmap dlws-scripts --from-file=${dir}/../../../../init-scripts --dry-run -o yaml > $dlts_scripts_file_name
${dir}/../../../deploy/bin/kubectl create configmap job-manager-config --from-file=${dir}/config.yaml --dry-run -o yaml > $dlts_job_manager_config
${dir}/../../../deploy/bin/kubectl create configmap job-manager-kubeconfig --from-file=${dir}/config --dry-run -o yaml > $dlts_job_manager_kubeconfig
