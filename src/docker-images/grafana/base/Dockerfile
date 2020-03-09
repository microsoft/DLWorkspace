FROM          ubuntu:16.04

ENV           DEBIAN_FRONTEND noninteractive

RUN			apt-get update 
RUN			apt-get update 
RUN			apt-get --no-install-recommends install -y curl vim apt-transport-https


RUN			echo "deb https://packagecloud.io/grafana/stable/debian/ wheezy main" | tee /etc/apt/sources.list.d/grafana.list
RUN			curl https://packagecloud.io/gpg.key | apt-key add -
RUN			apt-get update && apt-get --no-install-recommends install -y grafana jq

