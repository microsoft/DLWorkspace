FROM ubuntu:18.04
MAINTAINER Hongzhi Li  <Hongzhi.Li@microsoft.com>

RUN apt-get update && \
    apt-get --no-install-recommends install -y apache2 libapache2-mod-wsgi curl

RUN mkdir -p /data
ADD 000-default.conf /etc/apache2/sites-enabled/000-default.conf


RUN mkdir -p /data/cfssl/linux
RUN curl --retry 10 -L -o /data/cfssl/linux/cfssl https://pkg.cfssl.org/R1.2/cfssl_linux-amd64
RUN curl --retry 10 -L -o /data/cfssl/linux/cfssljson https://pkg.cfssl.org/R1.2/cfssljson_linux-amd64

RUN mkdir -p /data/easy-rsa
RUN curl --retry 10 -L -o /data/easy-rsa/v3.0.5.tar.gz https://github.com/OpenVPN/easy-rsa/archive/v3.0.5.tar.gz


RUN mkdir -p /data/cni
RUN curl --retry 10 -L -o /data/cni/cni-v0.7.1.tgz https://github.com/microsoft/DLWorkspace/releases/download/v1.2.0/cni-v0.7.1.tgz

CMD ["httpd-foreground"]