FROM {{cnf["worker-dockerregistry"]}}{{cnf["dockerprefix"]}}restfulapi:{{cnf["dockertag"]}}
MAINTAINER Sanjeev Mehrotra <sanjeevm@microsoft.com>

# Get az
RUN echo "deb [arch=amd64] https://packages.microsoft.com/repos/azure-cli/ wheezy main" | tee /etc/apt/sources.list.d/azure-cli.list
RUN apt-key adv --keyserver packages.microsoft.com --recv-keys 417A0893
RUN apt-get install apt-transport-https
RUN apt-get update && apt-get install azure-cli     

RUN az acs kubernetes install-cli --install-location /usr/local/bin/kubectl
RUN chmod +x /usr/local/bin/kubectl

