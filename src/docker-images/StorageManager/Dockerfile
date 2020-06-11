FROM python:3.7

RUN pip3 install requests==2.22.0 pyyaml==5.2 flask prometheus_client flask-cors

ADD StorageManager /DLWorkspace/src/StorageManager

COPY run.sh /
RUN chmod +x /run.sh

CMD ["/run.sh"]
