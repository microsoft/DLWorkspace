#!/bin/bash

dir=`dirname $0`

grafana_file_name=${dir}/grafana-config.yaml
alert_tmpl_file_name=${dir}/alert-templates.yaml
prometheus_file_name=${dir}/prometheus-alerting.yaml

# create configmap
for i in `find ${dir}/grafana-config/ -type f -regex ".*json" ` ; do
    echo --from-file=$i
done | xargs ${dir}/../../deploy/bin/kubectl --namespace=kube-system create configmap grafana-configuration --dry-run -o yaml >> $grafana_file_name

${dir}/../../deploy/bin/kubectl --namespace=kube-system create configmap alert-templates --from-file=${dir}/alert-templates --dry-run -o yaml > $alert_tmpl_file_name

${dir}/../../deploy/bin/kubectl --namespace=kube-system create configmap prometheus-alert --from-file=${dir}/alerting --dry-run -o yaml >> $prometheus_file_name
