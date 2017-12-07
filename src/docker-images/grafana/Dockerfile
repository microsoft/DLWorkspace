FROM          ubuntu:16.04

ENV           DEBIAN_FRONTEND noninteractive

RUN			apt-get update 
RUN			apt-get update 
RUN			apt-get install -y curl vim apt-transport-https


RUN			echo "deb https://packagecloud.io/grafana/stable/debian/ wheezy main" | tee /etc/apt/sources.list.d/grafana.list
RUN			curl https://packagecloud.io/gpg.key | apt-key add -
RUN			apt-get update && apt-get install -y grafana jq

RUN			mkdir -p /var/lib/grafana/data/dashboards
RUN			mkdir -p /etc/grafana
RUN			mkdir -p /var/lib/grafana/data/ds
ADD 		grafana.ini /etc/grafana/grafana.ini


ADD 		dashboard/dlworkspace.json /var/lib/grafana/data/dashboards/dlworkspace.json
ADD 		dashboard/gpu.json /var/lib/grafana/data/dashboards/gpu.json
ADD 		dashboard/jobgpuusage.json /var/lib/grafana/data/dashboards/jobgpuusage.json
ADD 		dashboard/kubernetes-cluster.json /var/lib/grafana/data/dashboards/kubernetes-cluster.json
ADD 		dashboard/kubernetes-pods.json /var/lib/grafana/data/dashboards/kubernetes-pods.json
ADD 		dashboard/app-metrics-web-monitoring.json /var/lib/grafana/data/dashboards/app-metrics-web-monitoring.json

ADD 		datasource/collectd.json /var/lib/grafana/data/ds/collectd.json
ADD 		datasource/k8s.json /var/lib/grafana/data/ds/k8s.json

ADD           init.sh /usr/bin/init.sh
RUN           chmod +x /usr/bin/init.sh

ADD           start /usr/bin/start
RUN           chmod +x /usr/bin/start

CMD           start