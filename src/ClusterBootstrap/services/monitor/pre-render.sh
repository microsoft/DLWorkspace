#!/bin/bash

dir=`dirname $0`

kill_idle_rule=${dir}/alerting/kill-idle.rules

grafana_file_name=${dir}/grafana-config.yaml
alert_tmpl_file_name=${dir}/alert-templates.yaml
prometheus_file_name=${dir}/prometheus-alerting.yaml

rm $kill_idle_rule $grafana_file_name $alert_tmpl_file_name $prometheus_file_name 2> /dev/null

# config kill rules
${dir}/config_alerting.py "${dir}/../../config.yaml" > $kill_idle_rule

# generate extra grafana-config from ./grafana-config-raw
for i in `find ${dir}/grafana-config-raw/ -type f -regex ".*json" ` ; do
    ${dir}/gen_grafana-config.py ${i} ${dir}/grafana-config
done

# create configmap
for i in `find ${dir}/grafana-config/ -type f -regex ".*json" ` ; do
    echo --from-file=$i
done | xargs ${dir}/../../deploy/bin/kubectl --namespace=kube-system create configmap grafana-configuration --dry-run -o yaml >> $grafana_file_name

${dir}/../../deploy/bin/kubectl --namespace=kube-system create configmap alert-templates --from-file=${dir}/alert-templates --dry-run -o yaml > $alert_tmpl_file_name

${dir}/../../deploy/bin/kubectl --namespace=kube-system create configmap prometheus-alert --from-file=${dir}/alerting --dry-run -o yaml > $prometheus_file_name
