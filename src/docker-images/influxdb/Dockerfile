FROM          ubuntu:16.04


ENV           DEBIAN_FRONTEND noninteractive

RUN			apt-get update && apt-get --no-install-recommends install -y curl vim apt-transport-https wget
#RUN	   		curl -sL https://repos.influxdata.com/influxdb.key | apt-key add -
#RUN			echo "deb https://repos.influxdata.com/ubuntu xenial stable" | tee /etc/apt/sources.list.d/influxdb.list
#RUN			apt-get update && apt-get --no-install-recommends install -y influxdb


RUN			wget https://dl.influxdata.com/influxdb/releases/influxdb_1.4.2_amd64.deb
RUN			dpkg -i influxdb_1.4.2_amd64.deb
RUN			apt-get update && apt-get --no-install-recommends install -y influxdb

RUN			mkdir -p /opt/collectd/share/collectd
ADD			types.db /opt/collectd/share/collectd/types.db


ADD			influxdb.conf /etc/influxdb/influxdb.conf
ADD           start /usr/bin/start
ADD           init.sh /usr/bin/init.sh
RUN           chmod +x /usr/bin/start
RUN           chmod +x /usr/bin/init.sh
ADD           types.db /usr/share/collectd/types.db


CMD           start