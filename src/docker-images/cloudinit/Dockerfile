FROM ubuntu:18.04

MAINTAINER Zhe Xu <zhexu@microsoft.com>

COPY worker_cld_init.tar /usr/
COPY run.sh /
RUN chmod +x /run.sh
CMD /run.sh