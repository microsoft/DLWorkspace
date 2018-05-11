# Configuration: Azure Cluster

For more customized configuration, please refer to the [Configuration Section](../configuration/Readme.md). 

## Azure Cluster specific configuration

We have greatly simplified Azure Cluster Configuration. As a minimum, you will only need to create a config.yaml file under src/ClusterBootstrap, with the cluster name. 

### Cluster Name

Cluster name must be unique, and should be specified as:

```
cluster_name: [your cluster name]
```


### Authentication
If you are not building a cluster for Microsoft employee usage, you will also need to configure [Authentication](../authentication/Readme.md). 

### Additional configuration. 

You may provide/change the specification of the deployed Azure cluster by adding the following information on config.yaml file:

```
azure_cluster: 
  <<your cluster name>>:
    "infra_node_num": 1, 
    "worker_node_num": 2, 
    "azure_location": "westus2",
    "infra_vm_size" : "Standard_D1_v2",
    "worker_vm_size": "Standard_NC6",
``` 

* infra_node_num: should be odd (1, 3 or 5), number of infrastructure node for the deployment. 3 infrastructure nodes tolerate 1 failure, and 5 infrastructure nodes tolerate 2 failures. However, more infrastructure nodes (and more failure tolerance) will reduce performance of the node. 

* worker_node_num: number of worker node used for deployment. 

* azure_location: 

Please use the following to find all available azure locations. 
```
az account list-locations
```

* infra_vm_size, worker_vm_size: infrastructure and worker VM size. 

Usually, a CPU VM will be used for infra_vm_size, and a GPU VM will be used for worker_vm_size. Please use the following to find all available Azure VM size. 
```
az vm list-sizes --location westus2
```

* Configure MySql as follows:

```
datasource: MySQL
mysql_password: <<mysql_password>>
```
