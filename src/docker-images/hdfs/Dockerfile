FROM williamyeh/java8
MAINTAINER Jin Li <jinlmsft@hotmail.com>

VOLUME /mnt/hadoop/
RUN apt-get update \
  && apt-get install -y jq curl 

RUN curl -s http://www.apache.org/dist/hadoop/common/hadoop-2.8.0/hadoop-2.8.0.tar.gz | tar -xz -C /usr/local/ \
  && cd /usr/local \
  && ln -s ./hadoop-2.8.0 hadoop 

ENV JAVA_HOME /usr/lib/jvm/java-8-oracle
ENV HADOOP_PREFIX /usr/local/hadoop
ENV HADOOP_COMMON_HOME /usr/local/hadoop
ENV HADOOP_HDFS_HOME /usr/local/hadoop
ENV HADOOP_MAPRED_HOME /usr/local/hadoop
ENV HADOOP_YARN_HOME /usr/local/hadoop
ENV HADOOP_CONF_DIR /usr/local/hadoop/etc/hadoop
ENV YARN_CONF_DIR $HADOOP_PREFIX/etc/hadoop

WORKDIR /usr/local/hadoop
RUN sed -i '/^export JAVA_HOME/ s:.*:export JAVA_HOME=/usr/lib/jvm/java-8-oracle\nexport HADOOP_PREFIX=/usr/local/hadoop\nexport HADOOP_HOME=/usr/local/hadoop\n:' $HADOOP_PREFIX/etc/hadoop/hadoop-env.sh  \
  && sed -i '/^export HADOOP_CONF_DIR/ s:.*:export HADOOP_CONF_DIR=/usr/local/hadoop/etc/hadoop/:' $HADOOP_PREFIX/etc/hadoop/hadoop-env.sh \
  && chmod +x /usr/local/hadoop/etc/hadoop/*-env.sh

# NameNode                Secondary NameNode  DataNode                     JournalNode  NFS Gateway    HttpFS         ZKFC
EXPOSE 8020 50070 50470   50090 50495         50010 1004 50075 1006 50020  8485 8480    2049 4242 111  14000 14001    8019

RUN apt-get update && apt-get install -y python-pip attr
RUN pip install pyyaml jinja2 argparse logutils


WORKDIR {{cnf["docker-run"]["hdfs"]["workdir"]}}

ADD core-site.xml /usr/local/hadoop/etc/hadoop/core-site.xml
ADD hdfs-site.xml.in-docker {{cnf["docker-run"]["hdfs"]["workdir"]}}
ADD hdfs-site-single.xml.in-docker {{cnf["docker-run"]["hdfs"]["workdir"]}}
ADD logging.yaml.in-docker {{cnf["docker-run"]["hdfs"]["workdir"]}}
ADD mapred-site.xml.in-docker {{cnf["docker-run"]["hdfs"]["workdir"]}}
ADD yarn-site.xml.in-docker {{cnf["docker-run"]["hdfs"]["workdir"]}}
ADD yarn-site-single.xml.in-docker {{cnf["docker-run"]["hdfs"]["workdir"]}}
ADD bootstrap_hdfs.py {{cnf["docker-run"]["hdfs"]["workdir"]}}
ADD utils.py {{cnf["docker-run"]["hdfs"]["workdir"]}}
RUN chmod +x {{cnf["docker-run"]["hdfs"]["workdir"]}}/*.py

# All process in this docker needs to be run as a service. 
# Do not change the command, rewrite a service if need to 

# See information on https://stackoverflow.com/questions/19943766/hadoop-unable-to-load-native-hadoop-library-for-your-platform-warning
# the 3rd answer, you may ignore warning on NativeCodeLoader

CMD /bin/bash



