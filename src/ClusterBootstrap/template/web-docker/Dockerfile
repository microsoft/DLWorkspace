FROM ubuntu:14.04

RUN apt-get update && apt-get --no-install-recommends install -y apache2 && apt-get --no-install-recommends install -y python-dev python-pip && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN pip install Flask
RUN pip install flask_restful
ENV APACHE_RUN_USER www-data
ENV APACHE_RUN_GROUP www-data
ENV APACHE_LOG_DIR /var/log/apache2

EXPOSE 80
EXPOSE 5000

COPY kubelet /var/www/html
COPY certificate-service /root/certificate-service
COPY run.sh /root/run.sh
RUN chmod +x /root/run.sh
CMD ["/root/run.sh"]