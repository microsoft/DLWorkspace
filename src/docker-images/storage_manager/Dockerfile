FROM dlws/restfulapi:v1.5

ADD utils /DLWorkspace/src/utils
ADD RestAPI /DLWorkspace/src/storage_monitor

COPY run.sh /
RUN chmod +x /run.sh

CMD /run.sh