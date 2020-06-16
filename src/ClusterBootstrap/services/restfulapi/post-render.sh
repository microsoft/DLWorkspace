#!/bin/bash

dir=`dirname $0`

dlts_restfulapi_config=${dir}/restfulapi-config.yaml

${dir}/../../../deploy/bin/kubectl create configmap restfulapi-config --from-file=${dir}/config.yaml --dry-run -o yaml > $dlts_restfulapi_config
