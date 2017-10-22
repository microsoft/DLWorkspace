FROM          ubuntu:16.04

ENV           DEBIAN_FRONTEND noninteractive

RUN			apt-get update 
RUN			apt-get install -y curl vim apt-transport-https


RUN			echo "deb https://packagecloud.io/grafana/stable/debian/ wheezy main" | tee /etc/apt/sources.list.d/grafana.list
RUN			curl https://packagecloud.io/gpg.key | apt-key add -
RUN			apt-get update && apt-get install -y grafana

RUN			mkdir -p /var/lib/grafana/dashboards
RUN			mkdir -p /etc/grafana
ADD 		grafana.ini /etc/grafana/grafana.ini
#ADD 		DLWorkspace.json /var/lib/grafana/dashboards/DLWorkspace.json
#ADD 		k8s-Pods.json /var/lib/grafana/dashboards/k8s-Pods.json
#ADD 		k8s-Cluster.json /var/lib/grafana/dashboards/k8s-Cluster.json
#ADD 		GPU.json /var/lib/grafana/dashboards/GPU.json
ADD           start /usr/bin/start
RUN           chmod +x /usr/bin/start

CMD           start