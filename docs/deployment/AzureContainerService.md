# Deploy DL workspace cluster on Azure Container Service (ACS)

This document describes the procedure to deploy DL workspace cluster on ACS. We are still improving the deployment procedure on ACS. Please contact the authors if you encounter any issues. 

0. Follow [this document](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest) to install Azure CLI and login to your Azure subscription on your dev machine. 

1. Clone this repo

2. Go into directory src/ClusterBootstrap inside the repo directory

3. Please create a configuration file called "config.yaml"

```
cluster_name: [your cluster name]
cluster_location : [your cluster location - e.g., northcentralus]
worker_node_num : [number of agent nodes for the ACS cluster]
master_node_num : [number of master nodes for the ACS cluster]
acsagentsize : [size of VM for agent nodes - e.g., Standard_NC12]
azstoragesku: [sku for Azure storage account - e.g., Standard_LRS]
azfilesharequota: [quota for fileshare in GB - e.g., 2048]
```

4. To start and deploy the cluster
```
./deploy.py acs
```

The deployment script executes the following commands (you do not need to run them if you directly run step 4)
1. Setup basic K8S cluster on ACS
```
./deploy.py acs deploy
```

2. Label nodels and deploy services:
```
./deploy.py acs postdeploy
```

3. Mount storage on nodes:
```
./deploy.py acs storagemount
```

4. Install GPU drivers on nodes (if needed):
```
./deploy.py acs gpudrivers
```

5. Install network plugin
```
./deploy.py acs freeflow
```

6. Build needed docker images and configuration files for restfulapi, jobmanager, and webui
```
./deploy.py acs bldwebui
```

7. Start DLWorkspace pods
```
./deploy.py acs restartwebui
```

