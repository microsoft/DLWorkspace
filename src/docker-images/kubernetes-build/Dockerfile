FROM mlcloudreg.westus.cloudapp.azure.com:5000/{{cnf["dockerprefix"]}}gobld:latest
MAINTAINER Sanjeev Mehrotra <sanjeevm0@hotmail.com>

# Get Kubernetes
RUN mkdir -p /go/src/k8s.io
ARG NOCACHE=1
# RUN ssh-agent sh -c 'ssh-add /root/gittoken; git clone git@github.com:{{cnf["k8s-gitrepo"]}} /go/src/k8s.io/kubernetes'
RUN git clone https://github.com/{{cnf["k8s-gitrepo"]}} /go/src/k8s.io/kubernetes
WORKDIR /go/src/k8s.io/kubernetes
RUN git checkout {{cnf["k8s-gitbranch"]}}
# Get all git tags in main branch so that version number is correct after make
RUN git remote add kubernetes http://github.com/kubernetes/kubernetes
RUN git fetch kubernetes
# Build Kubernetes
RUN make
# Copy binaries to root
RUN cp /go/src/k8s.io/kubernetes/_output/bin/* /

# Custom CRI
ARG NOCACHE_CRI=1
COPY gittoken /root/gittoken
RUN chmod 400 /root/gittoken
RUN mkdir -p /go/src/github.com
RUN ssh-agent sh -c 'ssh-add /root/gittoken; git clone --recursive git@github.com:{{cnf["k8scri-gitrepo"]}} /go/src/github.com/KubeGPU'
WORKDIR /go/src/github.com/KubeGPU
RUN git checkout {{cnf["k8scri-gitbranch"]}}
# Build the CRI and copy file to root
WORKDIR /go/src/github.com/KubeGPU/cri/kubegpucri
RUN go install
RUN cp /go/bin/kubegpucri /
# Build the scheduler
# nothing for now

# Change working directory to root
WORKDIR /

