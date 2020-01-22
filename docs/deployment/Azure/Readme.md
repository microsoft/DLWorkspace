# Deploy DL Workspace cluster on Azure. 

This document describes the procedure to deploy a DL Workspace cluster on Azure. With autoscale enabled DL Workspace, VM will be created (and released) on demand when you launch DL jobs ( e.g., TensorFlow, Pytorch, Caffe2), thus save your money in operation.

Please note that the procedure below doesn't deploy HDFS/Spark on DLWorkspace cluster on Azure (Spark job execution is not available on Azure Cluster).

Prerequisite steps:
First require the manager to add you into a subscription group., then either 
1. go to that group from Azure Portal and add ubuntu server from resources, this virtual server is your devbox, or 
2. if you have a physical machine, install ubuntu server system(18.04) on that and use it as your devbox
then use the devbox to deploy node on cloud.

## Workflow:

First we need to setup the devbox that we use to operate on.

1. Change directory to src/ClusterBootstrap on devbox, and install prerequisite packages:
```
cd src/ClusterBootstrap/ 
sudo ./install_prerequisites.sh
```
2. Login to Azure, setup proper subscription and confirm
```
SUBSCRIPTION_NAME="<subscription name>" 
az login
az account set --subscription "${SUBSCRIPTION_NAME}" 
az account list | grep -A5 -B5 '"isDefault": true'
```

3. Go to work directiry "src/ClusterBootstrap"
```
cd src/ClusterBootstrap
```


4. [configure](configure.md) your azure cluster. Put config.yaml under src/ClusterBootstrap

5. run batch script to deploy the cluster

```./deploy.sh```



If you run into a deployment issue, please check [here](FAQ.md) first.

## Details in deploy.sh

We will explain the operations behind deploy.sh in this section. 

```
#!/bin/bash
rm -rf deploy/* cloudinit* az_complementary.yaml
```

This line cleans all existing binaries/certificates etc. and complementary yaml files.

```# # render
./cloud_init_deploy.py clusterID
./cloud_init_aztools.py -cnf config.yaml -o az_complementary.yaml prerender
```

These lines generate complementary yaml files based on given configuration of a cluster. Machine names would also be generated if not specified.

```
# # render templates and prepare binaries
./cloud_init_deploy.py -cnf config.yaml -cnf az_complementary.yaml render
```

Renders templates, generate certificates and prepare binaries that later would be used for setting up the cluster.

```
# # pack, push dockers, generate az cli commands to add machines
./cloud_init_deploy.py -cnf config.yaml -cnf az_complementary.yaml pack
```

Pack all the files generated in last step into a tar file.

```
# # push dockers
./cloud_init_deploy.py -cnf config.yaml -cnf az_complementary.yaml docker servicesprerequisite
```

Push dockers that are required by services specied in configuration.

```
# # # generate
./cloud_init_aztools.py -cnf config.yaml -cnf az_complementary.yaml deploy
```

Generate scripts that later would be executed to deploy a cluster.

```
# # deploy
./scripts/deploy_framework.sh
./scripts/add_machines.sh
./cloud_init_aztools.py -cnf config.yaml -cnf az_complementary.yaml interconnect
```

Deploy a cluster.

```
# # get status
./cloud_init_aztools.py -cnf config.yaml -o brief.yaml listcluster

```

Generate a yaml file that would later be used to maintain the cluster.
