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

RUN apt-get -y update && apt-get -y install p7zip-full

RUN mkdir -p /var/www/html/ubuntu/16.04.2

RUN 7z x -o/var/www/html/ubuntu/16.04.2 ubuntu-16.04.2-server-amd64.iso

RUN rm ubuntu-16.04.2-server-amd64.iso

RUN apt-get update -y && apt-get install -y python-dev python-pip 
RUN pip install Flask
RUN pip install flask_restful
ENV APACHE_RUN_USER www-data
ENV APACHE_RUN_GROUP www-data
ENV APACHE_LOG_DIR /var/log/apache2

EXPOSE 80
EXPOSE 5000

COPY tftpd-hpa /etc/default/tftpd-hpa

COPY tftp /var/lib/tftpboot/
RUN chmod -R 777 /var/lib/tftpboot

RUN wget -q https://www.kernel.org/pub/linux/utils/boot/syslinux/syslinux-6.03.tar.gz
RUN tar -zxvf syslinux-6.03.tar.gz
RUN cp syslinux-6.03/bios/com32/chain/chain.c32 /var/lib/tftpboot/
RUN cp syslinux-6.03/bios/com32/elflink/ldlinux/ldlinux.c32 /var/lib/tftpboot/
RUN cp syslinux-6.03/bios/com32/lib/libcom32.c32 /var/lib/tftpboot/
RUN cp syslinux-6.03/bios/com32/libutil/libutil.c32 /var/lib/tftpboot/
RUN cp syslinux-6.03/bios/core/pxelinux.0 /var/lib/tftpboot/
RUN cp syslinux-6.03/bios/com32/menu/vesamenu.c32 /var/lib/tftpboot/
RUN rm -r syslinux-6.03
RUN rm syslinux-6.03.tar.gz


RUN cp -fr /var/www/html/ubuntu/16.04.2/install/netboot/ubuntu-installer/amd64/* /var/lib/tftpboot
RUN cp -f /var/www/html/ubuntu/16.04.2/install/netboot/ubuntu-installer/amd64/boot-screens/* /var/lib/tftpboot
RUN mkdir -p /var/lib/tftpboot/pxelinux.cfg



# COPY www /var/www/html



COPY preseed.cfg /var/www/html/preceed/preceed.cfg
COPY preseed.cfg /var/lib/tftpboot/preceed.cfg

COPY start_pxe_service.sh /
RUN chmod +x /start_pxe_service.sh


EXPOSE 80
EXPOSE 67
EXPOSE 68
EXPOSE 69

# Need to run privileged mode
# python /root/certificate-service/genkey-restapi.py && 
CMD /bin/bash -c "service apache2 start && service tftpd-hpa start && sleep infinity"
