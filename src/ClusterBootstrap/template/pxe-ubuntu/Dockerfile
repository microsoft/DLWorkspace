FROM ubuntu:16.04
MAINTAINER Jin Li <jinlmsft@hotmail.com>

RUN apt-get -y update && \
    apt-get --no-install-recommends install -y \
      vim \
      wget \
      curl \
      jq \
      gawk \
      openssh-client \
      git \
      rsync 

RUN apt-get update -y && \
    apt-get --no-install-recommends install -y tftpd-hpa inetutils-inetd syslinux isc-dhcp-server apache2

RUN wget {{cnf["ubuntuImageUrl"]}}

RUN apt-get -y update && apt-get --no-install-recommends install -y p7zip-full

RUN mkdir -p /var/www/html/ubuntu/install
RUN mkdir -p /tmp/ubuntu/

RUN 7z x -o/tmp/ubuntu {{cnf["ubuntuImageName"]}}
RUN rm {{cnf["ubuntuImageName"]}}
RUN cp -fr /tmp/ubuntu/install/* /var/www/html/ubuntu/install

RUN apt-get update -y && apt-get --no-install-recommends install -y python-dev python-pip 
RUN pip install Flask
RUN pip install flask_restful
ENV APACHE_RUN_USER www-data
ENV APACHE_RUN_GROUP www-data
ENV APACHE_LOG_DIR /var/log/apache2

EXPOSE 80
EXPOSE 5000

COPY tftpd-hpa /etc/default/tftpd-hpa

RUN chmod -R 777 /var/lib/tftpboot
RUN chmod -R 755 /var/www/html/


RUN wget -q https://www.kernel.org/pub/linux/utils/boot/syslinux/syslinux-6.03.tar.gz
RUN tar -zxvf syslinux-6.03.tar.gz
RUN cp syslinux-6.03/bios/com32/chain/chain.c32 /var/lib/tftpboot/
RUN cp syslinux-6.03/bios/com32/elflink/ldlinux/ldlinux.c32 /var/lib/tftpboot/
RUN cp syslinux-6.03/bios/com32/lib/libcom32.c32 /var/lib/tftpboot/
RUN cp syslinux-6.03/bios/com32/libutil/libutil.c32 /var/lib/tftpboot/
RUN cp syslinux-6.03/bios/core/pxelinux.0 /var/lib/tftpboot/
RUN cp syslinux-6.03/bios/com32/menu/vesamenu.c32 /var/lib/tftpboot/

RUN cp -fr /var/www/html/ubuntu/install/netboot/ubuntu-installer/amd64/* /var/lib/tftpboot
RUN cp -f /var/www/html/ubuntu/install/netboot/ubuntu-installer/amd64/boot-screens/* /var/lib/tftpboot
RUN cp syslinux-6.03/bios/core/pxelinux.0 /var/lib/tftpboot
RUN cp /var/www/html/ubuntu/install/filesystem.* /var/lib/tftpboot
COPY tftp /var/lib/tftpboot/
RUN mkdir -p /var/lib/tftpboot/pxelinux.cfg

RUN rm -r syslinux-6.03
RUN rm -rf /tmp/ubuntu
RUN rm syslinux-6.03.tar.gz

# COPY www /var/www/html



COPY preseed.cfg /var/www/html/preceed/preseed.cfg
COPY preseed.cfg /var/lib/tftpboot/preseed.cfg

COPY start_pxe_service.sh /
RUN chmod +x /start_pxe_service.sh


EXPOSE 80
EXPOSE 67
EXPOSE 68
EXPOSE 69

# Need to run privileged mode
# python /root/certificate-service/genkey-restapi.py && 
CMD /bin/bash -c "service apache2 start && service tftpd-hpa start && sleep infinity"
