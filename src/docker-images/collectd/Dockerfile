FROM          nvidia/cuda:8.0-runtime

ENV           DEBIAN_FRONTEND noninteractive

RUN           echo "deb http://us.archive.ubuntu.com/ubuntu/ precise universe" >> /etc/apt/sources.list
RUN           echo "deb http://ppa.launchpad.net/vbulax/collectd5/ubuntu precise main" >> /etc/apt/sources.list
RUN           apt-key adv --recv-keys --keyserver keyserver.ubuntu.com 232E4010A519D8D831B81C56C1F5057D013B9839
RUN           apt-get -y update && apt-get -y install collectd curl vim python-pip python-yaml python-pycurl apt-transport-https 

EXPOSE        8125
RUN           pip install --upgrade pip
RUN           pip install envtpl

RUN	   		curl -sL https://repos.influxdata.com/influxdb.key | apt-key add -
RUN			echo "deb https://repos.influxdata.com/ubuntu xenial stable" | tee /etc/apt/sources.list.d/influxdb.list
RUN			apt-get update && apt-get install influxdb
RUN			mkdir -p /opt/collectd/share/collectd
ADD			types.db /opt/collectd/share/collectd/types.db



ADD           cuda_collectd.py /usr/lib/collectd/cuda_collectd.py
ADD           kubernetes_collectd.py /usr/lib/collectd/kubernetes_collectd.py
ADD           configs/ /etc/collectd/configs
ADD           start /usr/bin/start
RUN           chmod +x /usr/bin/start
ADD           types.db /usr/share/collectd/types.db


CMD           start