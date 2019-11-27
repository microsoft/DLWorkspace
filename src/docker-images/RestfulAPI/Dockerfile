FROM dlws/restfulapi:v1.5
MAINTAINER Hongzhi Li <Hongzhi.Li@microsoft.com>

COPY kubectl /usr/local/bin/kubectl
RUN chmod +x /usr/local/bin/kubectl
#COPY gittoken /root/.ssh/id_rsa
#RUN chmod 400 /root/.ssh/id_rsa

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

COPY ClusterManager/requirements.txt /
# TODO refine later
# install requirements
RUN rm -rf /usr/lib/python2.7/dist-packages/yaml
RUN rm -rf /usr/lib/python2.7/dist-packages/PyYAML-*
RUN pip install -r /requirements.txt
RUN pip install MySQL-python
RUN pip install DBUtils

ADD Jobs_Templete /DLWorkspace/src/Jobs_Templete
ADD utils /DLWorkspace/src/utils
ADD RestAPI /DLWorkspace/src/RestAPI
ADD ClusterManager /DLWorkspace/src/ClusterManager


CMD /run.sh
