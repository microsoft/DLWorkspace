#!/bin/bash

dir=`dirname $0`

dlws_scripts_file_name=${dir}/dlws-scripts.yaml

${dir}/../../deploy/bin/kubectl create configmap dlws-scripts --from-file=${dir}/../../../init-scripts --dry-run -o yaml > $dlws_scripts_file_name