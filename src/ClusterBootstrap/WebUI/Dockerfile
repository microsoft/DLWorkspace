FROM ubuntu:16.04
MAINTAINER Hongzhi Li <Hongzhi.Li@microsoft.com>

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
        wget \
        vim \
        python-dev \
        python-numpy \
        python-pip \
        python-yaml 

RUN apt-get install -y \        
        apache2 \
        php \
        php-mysql \
        php-curl \
        libapache2-mod-php \
        nfs-common

RUN apt-get install -y bison curl golang-go
RUN pip install --upgrade pip; 

RUN pip install setuptools; 
RUN locale-gen en_US.UTF-8
RUN update-locale LANG=en_US.UTF-8

RUN pip install flask
RUN pip install flask.restful

RUN wget http://ccsdatarepo.westus.cloudapp.azure.com/data/tools/mysql-connector-python_2.1.5-1ubuntu14.04_all.deb  -O /mysql-connector-python_2.1.5-1ubuntu14.04_all.deb
RUN dpkg -i /mysql-connector-python_2.1.5-1ubuntu14.04_all.deb
RUN apt-get install -y mysql-connector-python

RUN wget http://ccsdatarepo.westus.cloudapp.azure.com/data/kube/kubelet/kubectl -O /usr/local/bin/kubectl
RUN chmod +x /usr/local/bin/kubectl
RUN mkdir /root/.kube
COPY config /root/.kube
COPY 000-default.conf /etc/apache2/sites-available/000-default.conf
COPY id_rsa /root/.ssh/id_rsa
RUN chmod 400 /root/.ssh/id_rsa
RUN apt-get install -y --no-install-recommends ssh
RUN ssh-keyscan github.com >> /root/.ssh/known_hosts
RUN ssh-agent bash -c 'ssh-add /root/.ssh/id_rsa; git clone -b webUI git@github.com:MSRCCS/DLWorkspace.git /DLWorkspace'

COPY run.sh /
RUN chmod +x /run.sh
COPY config.yaml /DLWorkspace/src/utils
CMD /run.sh
