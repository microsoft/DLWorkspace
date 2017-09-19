# Configuration: Azure Container Service. 

For more customized configuration, please refer to the [Configuration Section](../configuration/Readme.md). 

## ACS specific configuration

Please go into directory src/ClusterBootstrap inside the repo directory, and create a configuration file called "config.yaml"

```
cluster_name: [your cluster name]
cluster_location : [your cluster location - e.g., northcentralus]
worker_node_num : [number of agent nodes for the ACS cluster]
master_node_num : [number of master nodes for the ACS cluster]
acsagentsize : [size of VM for agent nodes - e.g., Standard_NC12]
azstoragesku: [sku for Azure storage account - e.g., Standard_LRS]
azfilesharequota: [quota for fileshare in GB - e.g., 2048]
```

More information is as follows:

* cluster_name: should be unique. 

* master_node_num: should be odd (1, 3 or 5), and specify the number of infrastructure node for the deployment. 3 infrastructure nodes tolerate 1 failure, and 5 infrastructure nodes tolerate 2 failures. However, more infrastructure nodes (and more failure tolerance) will reduce performance of the node. 

* worker_node_num: number of worker node used for deployment. 

* cluster_location: 

Please use the following to find all available azure locations. 
```
az account list-locations
```

* acsagentsize: worker VM size. 

Please use the following to find all available Azure VM size. It is recommended to use a GPU SKU for agent. 
```
az vm list-sizes --location westus2
```

* azstoragesku: recommend "Standard_LRS". 

* azfilesharequota: recommend "5120". 

## Authentication

If you are not building a cluster for Microsoft employee usage, you will also need to configure [Authentication](../authentication/Readme.md). 