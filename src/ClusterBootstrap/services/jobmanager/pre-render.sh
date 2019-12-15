#!/bin/bash

dir=`dirname $0`

dlws_scripts_file_name=./deploy/${dir}/dlws-scripts.yaml
./deploy.py rendertemplatedirectory ../init-scripts ./deploy/init-scripts
${dir}/../../deploy/bin/kubectl create configmap dlws-scripts --from-file=./deploy/init-scripts --dry-run -o yaml > $dlws_scripts_file_name

