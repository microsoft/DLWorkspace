FROM mlcloudreg.westus.cloudapp.azure.com:5000/{{cnf["cluster_name"]}}/gobld:latest
MAINTAINER Sanjeev Mehrotra <sanjeevm0@hotmail.com>

# Get Kubernetes
RUN mkdir /go/src/k8s.io
ARG NOCACHE=1
# RUN ssh-agent sh -c 'ssh-add /root/gittoken; git clone git@github.com:{{cnf["k8s-gitrepo"]}} /go/src/k8s.io/kubernetes'
RUN git clone https://github.com/{{cnf["k8s-gitrepo"]}} /go/src/k8s.io/kubernetes
WORKDIR /go/src/k8s.io/kubernetes
RUN git checkout {{cnf["k8s-gitbranch"]}}

RUN make

RUN cp /go/src/k8s.io/kubernetes/_output/bin/* /
WORKDIR /

