FROM ubuntu:16.04
MAINTAINER Jin Li <jinlmsft@hotmail.com>

RUN apt-get -y update && \
    apt-get -y install \
      vim \
      wget \
      curl \
      jq \
      gawk \
      openssh-client \
      git \
      rsync 

RUN apt-get update -y && \
    apt-get -y install tftpd-hpa inetutils-inetd syslinux isc-dhcp-server apache2

RUN wget http://releases.ubuntu.com/16.04/ubuntu-16.04.2-server-amd64.iso

RUN mkdir -p /var/www/html/ubuntu/16.04.2

COPY tftpd-hpa /etc/default/tftpd-hpa
COPY dhcpd.conf /etc/dhcp/


# RUN cp /usr/lib/syslinux/pxelinux.0 /var/lib/tftpboot/
# RUN mkdir -p /var/lib/tftpboot/pxelinux.cfg

# COPY www /var/www/html
COPY tftp /var/lib/tftpboot/


RUN chmod -R 777 /var/lib/tftpboot

COPY copy_html_data.sh /
COPY start_pxe_service.sh /
RUN chmod +x /copy_html_data.sh
RUN chmod +x /start_pxe_service.sh
RUN /copy_html_data.sh

EXPOSE 80
EXPOSE 67
EXPOSE 68
EXPOSE 69

# Need to run privileged mode
CMD /bin/bash -c "mount -o loop ubuntu-16.04.2-server-amd64.iso /var/www/html/ubuntu/16.04.2 && service tftpd-hpa start && service isc-dhcp-server restart && bash"
