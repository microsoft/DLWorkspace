FROM ubuntu:16.04
MAINTAINER Hongzhi Li <Hongzhi.Li@microsoft.com>

# See https://stackoverflow.com/questions/37706635/in-docker-apt-get-install-fails-with-failed-to-fetch-http-archive-ubuntu-com
# It is a good practice to merge apt-get update with the following apt-get install
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

#RUN wget http://ccsdatarepo.westus.cloudapp.azure.com/data/tools/mysql-connector-python_2.1.5-1ubuntu14.04_all.deb  -O /mysql-connector-python_2.1.5-1ubuntu14.04_all.deb
#RUN dpkg -i /mysql-connector-python_2.1.5-1ubuntu14.04_all.deb
#RUN apt-get install -y mysql-connector-python


# Install python for Azure SQL

RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -

RUN curl https://packages.microsoft.com/config/ubuntu/16.04/prod.list > /etc/apt/sources.list.d/mssql-release.list

RUN apt-get update; 

RUN ACCEPT_EULA=Y apt-get install -y msodbcsql=13.1.1.0-1

RUN apt-get install -y unixodbc-dev-utf16

#RUN ln -sfn /opt/mssql-tools/bin/sqlcmd-13.0.1.0 /usr/bin/sqlcmd 
#RUN ln -sfn /opt/mssql-tools/bin/bcp-13.0.1.0 /usr/bin/bcp

# RUN apt-get install -y unixodbc unixodbc-dev
# RUN apt-get install -y python-scipy

RUN pip install pyodbc
RUN pip install tzlocal

COPY kubectl /usr/local/bin/kubectl
RUN chmod +x /usr/local/bin/kubectl
#COPY gittoken /root/.ssh/id_rsa
#RUN chmod 400 /root/.ssh/id_rsa
RUN apt-get install -y --no-install-recommends ssh


RUN apt-get install -y apache2 libapache2-mod-wsgi
RUN rm /etc/apache2/mods-enabled/mpm_*
COPY mpm_prefork.conf /etc/apache2/mods-available/mpm_prefork.conf
COPY 000-default.conf /etc/apache2/sites-available/000-default.conf
COPY ports.conf /etc/apache2/ports.conf
RUN ln -s /etc/apache2/mods-available/mpm_prefork.conf /etc/apache2/mods-enabled/mpm_prefork.conf
RUN ln -s /etc/apache2/mods-available/mpm_prefork.load /etc/apache2/mods-enabled/mpm_prefork.load

COPY dlws-restfulapi.wsgi /wsgi/dlws-restfulapi.wsgi


COPY runScheduler.sh /
RUN chmod +x /runScheduler.sh
COPY pullsrc.sh /
RUN chmod +x /pullsrc.sh
COPY run.sh /
RUN chmod +x /run.sh

ADD Jobs_Templete /DLWorkspace/src/Jobs_Templete
ADD utils /DLWorkspace/src/utils
ADD RestAPI /DLWorkspace/src/RestAPI
ADD ClusterManager /DLWorkspace/src/ClusterManager
CMD /run.sh
