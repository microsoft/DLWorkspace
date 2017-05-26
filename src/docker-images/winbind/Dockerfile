FROM ubuntu:16.04
MAINTAINER Hongzhi Li  <Hongzhi.Li@microsoft.com>


ADD krb5.conf /etc/krb5.conf
ADD nsswitch.conf /etc/nsswitch.conf

RUN apt-get update && \
    apt-get install -y \
        samba \
        cifs-utils  \
        libnss-winbind \
        libpam-winbind \
        winbind \
        krb5-user \
        krb5-config 

 RUN apt-get install -y apache2 libapache2-mod-wsgi

 RUN apt-get install -y \
        python-dev \
        python-pip 

RUN pip install --upgrade pip; 

RUN pip install setuptools; 
RUN locale-gen en_US.UTF-8
RUN update-locale LANG=en_US.UTF-8

RUN pip install flask
RUN pip install flask.restful

ADD smb.conf /etc/samba/smb.conf

ADD run.sh /run.sh
RUN chmod +x /run.sh

ADD 000-default.conf /etc/apache2/sites-enabled/000-default.conf
ADD domaininfo /domaininfo

RUN ln -s /etc/apache2/mods-available/mpm_prefork.conf /etc/apache2/mods-enabled/mpm_prefork.conf
RUN ln -s /etc/apache2/mods-available/mpm_prefork.load /etc/apache2/mods-enabled/mpm_prefork.load
RUN rm /etc/apache2/mods-enabled/mpm_event.*


CMD /run.sh