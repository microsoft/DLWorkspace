FROM          ubuntu:16.04

ENV           DEBIAN_FRONTEND noninteractive

RUN			apt-get update
RUN			apt-get install -y curl vim apt-transport-https
RUN	   		curl -sL https://repos.influxdata.com/influxdb.key | apt-key add -
RUN			echo "deb https://repos.influxdata.com/ubuntu xenial stable" | tee /etc/apt/sources.list.d/influxdb.list
RUN			apt-get update && apt-get install -y influxdb
RUN			mkdir -p /opt/collectd/share/collectd
ADD			types.db /opt/collectd/share/collectd/types.db


RUN			echo "deb https://packagecloud.io/grafana/stable/debian/ wheezy main" | tee /etc/apt/sources.list.d/grafana.list
RUN			curl https://packagecloud.io/gpg.key | apt-key add -
RUN			apt-get update && apt-get install -y grafana

ADD			influxdb.conf /etc/influxdb/influxdb.conf
ADD           cuda_collectd.py /usr/lib/collectd/cuda_collectd.py
ADD           kubernetes_collectd.py /usr/lib/collectd/kubernetes_collectd.py
ADD           configs/ /etc/collectd/configs
ADD           start /usr/bin/start
RUN           chmod +x /usr/bin/start
ADD           types.db /usr/share/collectd/types.db


CMD           start