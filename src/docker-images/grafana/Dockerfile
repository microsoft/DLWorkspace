FROM          dlws/grafana:v1.0

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
ADD 		datasource/WebUI.json /var/lib/grafana/data/ds/WebUI.json

ADD           init.sh /usr/bin/init.sh
RUN           chmod +x /usr/bin/init.sh

ADD           start /usr/bin/start
RUN           chmod +x /usr/bin/start

CMD           start