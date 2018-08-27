FROM {{cnf["dockers"]["container"]["gobld"]["fullname"]}}
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
#COPY gittoken /root/gittoken
#RUN chmod 400 /root/gittoken
RUN mkdir -p /go/src/github.com/Microsoft
#RUN ssh-agent sh -c 'ssh-add /root/gittoken; git clone --recursive git@github.com:{{cnf["k8scri-gitrepo"]}} /go/src/github.com/Microsoft/KubeGPU'
RUN git clone https://github.com/{{cnf["k8scri-gitrepo"]}} /go/src/github.com/Microsoft/KubeGPU
WORKDIR /go/src/github.com/Microsoft/KubeGPU
RUN git checkout {{cnf["k8scri-gitbranch"]}}
WORKDIR /go/src/github.com/Microsoft/KubeGPU
# make the shim and scheduler
RUN make
# Copy binaries to root
RUN cp /go/src/github.com/Microsoft/KubeGPU/_output/* /
# # Build the CRI and copy file to root
# WORKDIR /go/src/github.com/Microsoft/KubeGPU/cri/kubegpucri
# RUN go install
# WORKDIR /go/src/github.com/Microsoft/KubeGPU/cmd/kube-scheduler
# RUN go install
# # Build the CRI and device advertiser - single binary for now
# RUN cp /go/bin/kubegpucri /
# # Build the scheduler
# RUN cp /go/bin/kube-scheduler /

# Change working directory to root
WORKDIR /

