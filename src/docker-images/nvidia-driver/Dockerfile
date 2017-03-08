##########################################################
#### THIS DOCKERFILE HAS TO BE BUILT IN COREOS SYSTEM#####
##########################################################

FROM ubuntu:14.04
MAINTAINER Hongzhi Li <Hongzhi.Li@microsoft.com>
RUN apt-get -y update && apt-get -y install git bc make dpkg-dev && mkdir -p /opt/kernels && mkdir -p /opt/nvidia/nvidia_installers
RUN apt-get -y install fakeroot build-essential crash kexec-tools makedumpfile kernel-wedge
#RUN apt-get -y build-dep linux
RUN apt-get -y install git-core libncurses5 libncurses5-dev libelf-dev binutils-dev pciutils
RUN apt-get -y install libssl-dev
RUN apt-get -y install gcc-4.7 g++-4.7 wget git make dpkg-dev
RUN update-alternatives --remove gcc /usr/bin/gcc-4.8
RUN update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-4.7 60 --slave /usr/bin/g++ g++ /usr/bin/g++-4.7
RUN update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-4.8 40 --slave /usr/bin/g++ g++ /usr/bin/g++-4.8
RUN mkdir -p /opt/kernels
WORKDIR /opt/kernels
RUN git clone https://github.com/coreos/linux.git && cd linux && git checkout v`uname -r | sed "s/-.*//"`-coreos
#RUN git clone https://github.com/coreos/linux.git && cd linux && git checkout v4.7.3-coreos
RUN zcat /proc/config.gz > /opt/kernels/linux/.config
WORKDIR /opt/kernels/linux
#RUN /opt/kernels/linux/scripts/config --disable CC_STACKPROTECTOR_STRONG
#RUN make modules_prepare
#RUN echo "#define UTS_RELEASE \""$(uname -r)"\"" > /opt/kernels/linux/include/generated/utsrelease.h
#RUN echo `uname -r` > /opt/kernels/linux/include/config/kernel.release
 



ENV NVIDIA_VERSION=375.20
ENV NV_DRIVER=/opt/nvidia-driver/$NVIDIA_VERSION
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$NV_DRIVER/lib:$NV_DRIVER/lib64
ENV PATH=$PATH:$NV_DRIVER/bin

ADD http://ccsdatarepo.westus.cloudapp.azure.com/data/nvidia_drivers/NVIDIA-Linux-x86_64-$NVIDIA_VERSION.run /opt/nvidia/nvidia_installers
WORKDIR /opt/nvidia/nvidia_installers
RUN chmod +x ./NVIDIA-Linux-x86_64-$NVIDIA_VERSION.run
RUN ./NVIDIA-Linux-x86_64-$NVIDIA_VERSION.run -a -x --ui=none
RUN rm ./NVIDIA-Linux-x86_64-$NVIDIA_VERSION.run



#EXPOSE 3476
RUN mkdir -p /opt/nvidia-docker-bin/
RUN wget -q -O - /opt https://github.com/NVIDIA/nvidia-docker/releases/download/v1.0.1/nvidia-docker_1.0.1_amd64.tar.xz | tar --strip-components=1 -C /opt/nvidia-docker-bin/ -Jxvf -
ADD install_drivers.sh /opt/
RUN chmod +x /opt/install_drivers.sh
ADD install_nvidia_driver.sh /opt/
RUN chmod +x /opt/install_nvidia_driver.sh
CMD /opt/install_drivers.sh

