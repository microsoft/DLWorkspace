FROM ubuntu:16.04
MAINTAINER Hongzhi Li <Hongzhi.Li@microsoft.com>

## Install python for Azure SQL
#
#RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
#
#RUN curl https://packages.microsoft.com/config/ubuntu/16.04/prod.list > /etc/apt/sources.list.d/mssql-release.list
#
#RUN apt-get update; ACCEPT_EULA=Y apt-get --no-install-recommends install -y msodbcsql=13.1.4.0-1 unixodbc-dev

RUN apt-get update && apt-get --no-install-recommends install -y apt-transport-https \
        python3-dev \
        python3-pip \
        python3-yaml \
        python3-pycurl \
        less \
        locales \
        curl \
        apt-utils \
        ssh \
        apache2 \
        libapache2-mod-wsgi-py3 \
        build-essential \
        libssl-dev \
        libmysqlclient-dev \
        sudo \
        gawk

RUN locale-gen en_US.UTF-8 && update-locale LANG=en_US.UTF-8

RUN curl -LO https://storage.googleapis.com/kubernetes-release/release/v1.15.2/bin/linux/amd64/kubectl && \
        chmod +x kubectl && \
        mv kubectl /usr/local/bin

RUN pip3 install setuptools wheel
RUN pip3 install mysql-connector-python flask flask-restful flask-cors requests tzlocal DBUtils mysqlclient

RUN usermod -a -G sudo www-data
RUN echo "\nwww-data ALL=(ALL) NOPASSWD:ALL\n" > /etc/sudoers

RUN rm /etc/apache2/mods-enabled/mpm_*
COPY mpm_prefork.conf /etc/apache2/mods-available/mpm_prefork.conf
COPY 000-default.conf /etc/apache2/sites-available/000-default.conf
COPY ports.conf /etc/apache2/ports.conf
RUN ln -s /etc/apache2/mods-available/mpm_prefork.conf /etc/apache2/mods-enabled/mpm_prefork.conf && \
        ln -s /etc/apache2/mods-available/mpm_prefork.load /etc/apache2/mods-enabled/mpm_prefork.load

COPY dlws-restfulapi.wsgi /wsgi/dlws-restfulapi.wsgi

COPY runScheduler.sh run.sh /

RUN chmod +x /runScheduler.sh && chmod +x /run.sh

COPY ClusterManager/requirements.txt /
RUN pip3 install -r /requirements.txt

ADD Jobs_Templete /DLWorkspace/src/Jobs_Templete
ADD utils /DLWorkspace/src/utils
ADD RestAPI /DLWorkspace/src/RestAPI
ADD ClusterManager /DLWorkspace/src/ClusterManager

ARG GIT_HASH
RUN printenv GIT_HASH > /DLWorkspace/GIT_HASH

CMD /run.sh
