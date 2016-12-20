FROM ubuntu:14.04

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

COPY tftpd-hpa /etc/default/tftpd-hpa
COPY dhcpd.conf /etc/dhcp/


RUN cp /usr/lib/syslinux/pxelinux.0 /var/lib/tftpboot/
RUN mkdir -p /var/lib/tftpboot/pxelinux.cfg
COPY default /var/lib/tftpboot/pxelinux.cfg/

RUN chmod -R 777 /var/lib/tftpboot




COPY copy_html_data.sh /
COPY start_pxe_service.sh /
RUN chmod +x /copy_html_data.sh

EXPOSE 80
EXPOSE 67
EXPOSE 68
EXPOSE 69

RUN /copy_html_data.sh

CMD /bin/bash -c "service tftpd-hpa start && service isc-dhcp-server restart && bash"
