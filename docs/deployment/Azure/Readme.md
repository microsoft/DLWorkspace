# Deploy DL Workspace cluster on Azure. 

This document describes the procedure to deploy a DL Workspace cluster on Azure. With autoscale enabled DL Workspace, VM will be created (and released) on demand when you launch DL jobs ( e.g., TensorFlow, Pytorch, Caffe2), thus save your money in operation.

Please note that the procedure below doesn't deploy HDFS/Spark on DLWorkspace cluster on Azure (Spark job execution is not available on Azure Cluster).

Prerequisite steps:
First require the manager to add you into a subscription group., then either 
1. go to that group from Azure Portal and add ubuntu server from resources, this virtual server is your devbox, or 
2. if you have a physical machine, install ubuntu server system(18.04) on that and use it as your devbox
then use the devbox to deploy node on cloud.

Workflow:
1. Please [configure](configure.md) your azure cluster. Put config.yaml under src/ClusterBootstrap

2. Change directory to src/ClusterBootstrap on devbox, and install prerequisite packages:
```
cd src/ClusterBootstrap/ 
sudo ./install_prerequisites.sh
```
3. Login to Azure, setup proper subscription and confirm
```
SUBSCRIPTION_NAME="<subscription name>" 
az login
az account set --subscription "${SUBSCRIPTION_NAME}" 
az account list | grep -A5 -B5 '"isDefault": true'
```
Execute this command, log out (exit) and log in back
```sudo usermod -aG docker <your username>```

After these steps, there are two pipelines that could be used to deploy a cluster: phase-focused pipeline (v1) and cloud-init based pipeline(v2). v1 combines template rendering/file copying/remote command execution together, and a step usually focuses on one role-wise/functionality-wise phase, such as deploying master node, start a certain service etc., while v2 utilizes az cloud-init feature and explicitly seperates template rendering and command execution etc.

no matter which pipeline do you use, make sure you are at src/ClusterBootstrap/

#phase-focused pipeline#

invoke ```./step_by_step.sh azure``` to deploy a new cluster, use deploy.py to modify/check the cluster or connect to a certain machine etc.

#cloud-init based pipeline#

```./v2deploy.sh```, and use maintain.py to update cluster machine list / connect to a certain machine etc.

If you run into a deployment issue, please check [here](FAQ.md) first.
