FROM ubuntu:14.04
MAINTAINER Hongzhi Li <Hongzhi.Li@microsoft.com>
RUN apt-get -y update && apt-get -y install git bc make dpkg-dev && mkdir -p /usr/src/kernels && mkdir -p /opt/nvidia/nvidia_installers
RUN apt-get -y install fakeroot build-essential crash kexec-tools makedumpfile kernel-wedge
#RUN apt-get -y build-dep linux
RUN apt-get -y install git-core libncurses5 libncurses5-dev libelf-dev binutils-dev
RUN apt-get -y install libssl-dev
RUN apt-get -y install gcc-4.7 g++-4.7 wget git make dpkg-dev
RUN update-alternatives --remove gcc /usr/bin/gcc-4.8
RUN update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-4.7 60 --slave /usr/bin/g++ g++ /usr/bin/g++-4.7
RUN update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-4.8 40 --slave /usr/bin/g++ g++ /usr/bin/g++-4.8
RUN mkdir -p /usr/src/kernels
WORKDIR /usr/src/kernels
#RUN git clone https://github.com/coreos/linux.git && cd linux && git checkout v`uname -r | sed "s/-.*//"`-coreos
RUN git clone https://github.com/coreos/linux.git && cd linux && git checkout v4.7.3-coreos
RUN zcat /proc/config.gz > /usr/src/kernels/linux/.config
WORKDIR /usr/src/kernels/linux
#RUN /usr/src/kernels/linux/scripts/config --disable CC_STACKPROTECTOR_STRONG
#RUN make modules_prepare
#RUN echo "#define UTS_RELEASE \""$(uname -r)"\"" > /usr/src/kernels/linux/include/generated/utsrelease.h
#RUN echo `uname -r` > /usr/src/kernels/linux/include/config/kernel.release
 
ADD http://ccsdatarepo.westus.cloudapp.azure.com/data/nvidia_drivers/NVIDIA-Linux-x86_64-375.20.run /opt/nvidia/nvidia_installers
WORKDIR /opt/nvidia/nvidia_installers
RUN chmod +x ./NVIDIA-Linux-x86_64-375.20.run
RUN ./NVIDIA-Linux-x86_64-375.20.run -a -x --ui=none

RUN apt-get install -y apt-transport-https ca-certificates && \
    apt-key adv \
               --keyserver hkp://ha.pool.sks-keyservers.net:80 \
               --recv-keys 58118E89F3A912897C070ADBF76221572C52609D && \
    echo "deb https://apt.dockerproject.org/repo ubuntu-trusty main" | sudo tee /etc/apt/sources.list.d/docker.list && \
    apt-get update && \
#    apt-get install -y linux-image-extra-virtual && \
    apt-get update && \
    apt-get install -y docker-engine


#EXPOSE 3476
RUN wget -P /opt https://github.com/NVIDIA/nvidia-docker/releases/download/v1.0.1/nvidia-docker_1.0.1_amd64.tar.xz
ADD install_drivers.sh /opt/
RUN chmod +x /opt/install_drivers.sh
CMD /opt/install_drivers.sh

