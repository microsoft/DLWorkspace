From sequenceiq/hadoop-docker:2.7.1
MAINTAINER Jin Li <jinlmsft@hotmail.com>

# CentOS 6.6 

RUN curl "https://bootstrap.pypa.io/get-pip.py" -o "get-pip.py"
RUN python get-pip.py
RUN pip install pyyaml jinja2 argparse logutils
RUN yum install -y attr


WORKDIR {{cnf["docker-run"]["hdfs"]["workdir"]}}

ADD core-site.xml /usr/local/hadoop/etc/hadoop/core-site.xml
ADD hdfs-site.xml.in-docker {{cnf["docker-run"]["hdfs"]["workdir"]}}
ADD logging.yaml.in-docker {{cnf["docker-run"]["hdfs"]["workdir"]}}
ADD bootstrap_hdfs.py {{cnf["docker-run"]["hdfs"]["workdir"]}}
ADD utils.py {{cnf["docker-run"]["hdfs"]["workdir"]}}
RUN chmod +x {{cnf["docker-run"]["hdfs"]["workdir"]}}/*.py

# All process in this docker needs to be run as a service. 
# Do not change the command, rewrite a service if need to 

# See information on https://stackoverflow.com/questions/19943766/hadoop-unable-to-load-native-hadoop-library-for-your-platform-warning
# the 3rd answer, you may ignore warning on NativeCodeLoader

CMD /bin/bash

