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
    ./install_prerequisites.sh
    ```
2. Login to Azure, setup proper subscription and confirm
    ```
    SUBSCRIPTION_NAME="<subscription name>" 
    az login
    az account set --subscription "${SUBSCRIPTION_NAME}" 
    az account list | grep --color -A5 -B5 '"isDefault": true'
    ```
3. Go to work directiry `src/ClusterBootstrap`
    ```
    cd src/ClusterBootstrap
    ```
4. [configure](cloud_init_configure.md) your azure cluster. Put `config.yaml` under `src/ClusterBootstrap`

5. run batch script to deploy the cluster
    ```
    ./deploy.sh
    ```

If you run into a deployment issue, please check [here](FAQ.md) first.

## Details in deploy.sh

We will explain the operations behind `deploy.sh` in this section. 

Clean up existing binaries/certificates etc. and complementary yaml files:
```
#!/bin/bash
rm -rf deploy/* cloudinit* az_complementary.yaml
```

Generate complementary yaml file `az_complementary.yaml` based on given configuration file `config.yaml` of a cluster (machine names are generated if not specified):
```
# render
./cloud_init_deploy.py clusterID
./cloud_init_aztools.py prerender
```

Render templates, generate certificates and prepare binaries for cluster setup:
```
./cloud_init_deploy.py render
```

Pack all the generated files in the previous step into a tar file:
```
./cloud_init_deploy.py pack
```

Push docker images that are required by services specified in configuration:
```
./cloud_init_deploy.py docker servicesprerequisite
```

Deploy a cluster:
```
./cloud_init_aztools.py interconnect
```

Generate a yaml file `brief.yaml` for cluster maintenance:
```
./cloud_init_aztools.py listcluster
```
