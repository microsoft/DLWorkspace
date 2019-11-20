FROM dlws/restfulapi:v1.5

ADD utils /DLWorkspace/src/utils
ADD StorageManager /DLWorkspace/src/StorageManager

COPY run.sh /
RUN chmod +x /run.sh

CMD /run.sh