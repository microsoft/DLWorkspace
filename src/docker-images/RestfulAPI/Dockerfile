FROM ubuntu:16.04
MAINTAINER Hongzhi Li <Hongzhi.Li@microsoft.com>

RUN apt-get update 
RUN apt-get install -y --no-install-recommends apt-transport-https
RUN apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
        wget \
        vim \
        python-dev \
        python-pip \
        python-yaml 
        

RUN apt-get install -y bison curl nfs-common
RUN pip install --upgrade pip; 

RUN pip install setuptools; 
RUN locale-gen en_US.UTF-8
RUN update-locale LANG=en_US.UTF-8

RUN pip install flask
RUN pip install flask.restful

RUN wget http://ccsdatarepo.westus.cloudapp.azure.com/data/tools/mysql-connector-python_2.1.5-1ubuntu14.04_all.deb  -O /mysql-connector-python_2.1.5-1ubuntu14.04_all.deb
RUN dpkg -i /mysql-connector-python_2.1.5-1ubuntu14.04_all.deb
RUN apt-get install -y mysql-connector-python


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

RUN pip install --upgrade pip; 

RUN pip install setuptools; 

RUN pip install pyodbc



RUN wget http://ccsdatarepo.westus.cloudapp.azure.com/data/kube/kubelet/kubectl -O /usr/local/bin/kubectl
RUN chmod +x /usr/local/bin/kubectl
RUN mkdir /root/.kube
COPY config /root/.kube
COPY 000-default.conf /etc/apache2/sites-available/000-default.conf
COPY id_rsa /root/.ssh/id_rsa
RUN chmod 400 /root/.ssh/id_rsa
RUN apt-get install -y --no-install-recommends ssh


COPY run.sh /
RUN chmod +x /run.sh
COPY runScheduler.sh /
RUN chmod +x /runScheduler.sh
CMD /run.sh
