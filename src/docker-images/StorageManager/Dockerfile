FROM dlws/restfulapi:v1.5

RUN rm -rf /usr/lib/python2.7/dist-packages/yaml
RUN rm -rf /usr/lib/python2.7/dist-packages/PyYAML-*

RUN pip install faulthandler \
                prometheus-client==0.7.1 \
                PyYAML>=5.1.1

ADD utils /DLWorkspace/src/utils
ADD StorageManager /DLWorkspace/src/StorageManager

COPY run.sh /
RUN chmod +x /run.sh

CMD /run.sh
