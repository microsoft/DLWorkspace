FROM ubuntu:16.04
MAINTAINER Hongzhi Li <Hongzhi.Li@microsoft.com>

# See https://stackoverflow.com/questions/37706635/in-docker-apt-get-install-fails-with-failed-to-fetch-http-archive-ubuntu-com
# It is a good practice to merge apt-get update with the following apt-get install
RUN apt-get update;
RUN apt-get update; apt-get install -y --no-install-recommends apt-transport-https \
        build-essential \
        cmake \
        git \
        wget \
        vim \
        python-dev \
        python-pip \
        python-yaml \
        locales \
        python-pycurl \
        bison \
        curl \
        nfs-common \
        apt-utils


RUN pip install --upgrade pip;

RUN pip install setuptools;
RUN locale-gen en_US.UTF-8
RUN update-locale LANG=en_US.UTF-8

RUN pip install flask
RUN pip install flask.restful
RUN pip install requests

RUN wget http://ccsdatarepo.westus.cloudapp.azure.com/data/tools/mysql-connector-python_2.1.7-1ubuntu16.04_all.deb -O /mysql-connector-python_2.1.7-1ubuntu16.04_all.deb
RUN dpkg -i /mysql-connector-python_2.1.7-1ubuntu16.04_all.deb
RUN apt-get install -y libmysqlclient-dev mysql-connector-python


# Install python for Azure SQL

RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -

RUN curl https://packages.microsoft.com/config/ubuntu/16.04/prod.list > /etc/apt/sources.list.d/mssql-release.list

RUN apt-get update; ACCEPT_EULA=Y apt-get install -y msodbcsql=13.1.4.0-1 unixodbc-dev


RUN pip install pyodbc
RUN pip install tzlocal
RUN apt-get update; apt-get install -y --no-install-recommends ssh apache2 libapache2-mod-wsgi sudo
RUN usermod -a -G sudo www-data
RUN echo "\nwww-data ALL=(ALL) NOPASSWD:ALL\n" > /etc/sudoers

RUN pip install subprocess32
RUN pip install requests

