FROM ubuntu:18.04
MAINTAINER Sanjeev Mehrotra <sanjeevm@microsoft.com>

RUN apt-get update 
RUN apt-get install -y --no-install-recommends \
        apt-utils \
        software-properties-common \
        git \
        curl \
        wget \
        cpio \
        mkisofs \
        apt-transport-https \
        openssh-client \
        ca-certificates \
        sshpass \
        ssh \
        build-essential \
        net-tools

RUN apt-get install -y --no-install-recommends \
    python3-pip \
    python3-yaml \
    python3-jinja2 \
    python3-setuptools \
    python3-pycurl

RUN wget https://repo.anaconda.com/archive/Anaconda3-5.2.0-Linux-x86_64.sh
RUN bash Anaconda3-5.2.0-Linux-x86_64.sh -b -p /usr/local/anaconda
RUN rm Anaconda3-5.2.0-Linux-x86_64.sh

ENV PATH="${PATH}:/usr/local/anaconda/bin"

RUN update-ca-certificates

RUN conda install pytorch torchvision -c pytorch

# Replace standard PIL (Python Image Library) with faster version
RUN pip uninstall -y pillow
RUN CC="cc -mavx2" pip install -U --force-reinstall pillow-simd

RUN pip install tensorboardX
RUN pip install tqdm

ENV LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:/usr/local/cuda/extras/CUPTI/lib64:/usr/local/nvidia/lib:/usr/local/nvidia/lib64"
ENV PATH="${PATH}:/usr/local/nvidia/bin:/usr/local/cuda/bin"
