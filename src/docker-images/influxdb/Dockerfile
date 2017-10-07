FROM          ubuntu:16.04

ENV           DEBIAN_FRONTEND noninteractive

RUN			apt-get update
RUN			apt-get install -y curl vim apt-transport-https
RUN	   		curl -sL https://repos.influxdata.com/influxdb.key | apt-key add -
RUN			echo "deb https://repos.influxdata.com/ubuntu xenial stable" | tee /etc/apt/sources.list.d/influxdb.list
RUN			apt-get update && apt-get install -y influxdb
RUN			mkdir -p /opt/collectd/share/collectd
ADD			types.db /opt/collectd/share/collectd/types.db


ADD			influxdb.conf /etc/influxdb/influxdb.conf
ADD           start /usr/bin/start
RUN           chmod +x /usr/bin/start
ADD           types.db /usr/share/collectd/types.db


CMD           start