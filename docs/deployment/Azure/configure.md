# Configuration: Azure Cluster

For more customized configuration, please refer to the [Configuration Section](../configuration/Readme.md) and [Azure doc](https://docs.microsoft.com/en-us/cli/azure/vm?view=azure-cli-latest). 

## Azure Cluster specific configuration

We have greatly simplified Azure Cluster Configuration. As a minimum, you will only need to create a config.yaml file under src/ClusterBootstrap, with the cluster name. 

### Cluster Name

Cluster name must be unique, and should be specified as:

```
cluster_name: <your cluster name>
```

### Authentication
If you are not building a cluster for Microsoft employee usage, you will also need to configure [Authentication](../authentication/Readme.md). 

### Additional configuration. 

You may provide/change the specification of the deployed Azure cluster by adding the following information on config.yaml file.
The details of configuration depend on the pipeline that is used for deployment.

## cloud-init deployment pipeline ##
For cloud-init based deployment, following entries need to be specified:
```
cluster_name: zxcldexample
cloud-init: True
azure_cluster:
  azure_location: eastus
  vm:
    - num: 1
      vm_size : Standard_B2s
      vm_image: Canonical:UbuntuServer:18.04-LTS:18.04.201910030
      role: 
        - infra
        - kubernetes_master
        - etcd
      storage:
        - sku: Premium_LRS
          is_os: True
          size_gb: 50
          disk_num: 1
        - sku: Premium_LRS
          size_gb: 50
          disk_num: 1
      kube_services:
        - nvidia-device-plugin
        - flexvolume
        - mysql
        - jobmanager
        - restfulapi
        - monitor
        - dashboard
      # availability_set: <availability_set>
    - num: 1
      vm_size : Standard_B2s
      role: 
        - nfs
      storage:
        - sku: Premium_LRS
          is_os: True
          size_gb: 50
          disk_num: 1
        - sku: Premium_LRS
          size_gb: 100
          disk_num: 1
      data_disk_mnt_path: /data
      private_ip_address: 192.168.0.9
      fileshares:
        - from: /data/share/ads/jobfiles
          to_mnt: /mntdlws/nfs/ads/jobfiles
          to_lnk: /dlwsdata/ads/jobfiles
        - from: /data/share/ads_not_expected_before/jobfiles
          to_mnt: /mntdlws/nfs/ads1/jobfiles
          to_lnk: /dlwsdata/ads1/jobfiles
        # below: /data/share/Ads/jobfiles --mount-to--> /mntdlws/nfs/Ads/jobfiles --link-to--> /dlwsdata/Ads/just;
        #        /data/share/Ads/storage --mount-to-->     /mntdlws/nfs/Ads/demo     --link-to--> /dlwsdata/Ads/demo;
        - from_root: /data/share/
          to_root_mnt: /mntdlws/nfs
          to_root_lnk: /dlwsdata
          leaves: 
            - from: jobfiles
              to_mnt: jobfiles
              to_lnk: jobfiles
            - from: storage
              to_mnt: storage
              to_lnk: storage
            - from: work
              to_mnt: work
              to_lnk: work  
          # VC: Ads

    - num: 1
      vm_size : Standard_B2s
      vm_image: Canonical:UbuntuServer:18.04-LTS:18.04.201910030
      role: 
        - worker
      gpu_type: None
```

for each item in cnf["azure_cluster"]["vm"], we specify a machine spec, including role(s), storage, how many instance we want that follow this spec etc. Depending on role specified, we could further configure mounting plan/kubernetes service we want to run etc.

## phase-focused deployment pipeline ##
for phase-focused deployment, start with config in following format instead.

```
cluster_name: {{cnf["cluster_name"]}}

azure_cluster:
    infra_node_num: 1
    infra_vm_size : Standard_B2s
    azure_location: eastus
    worker_node_num: 1
    nfs_node_num: 1
    nfs_data_disk_sz : 31
    nfs_data_disk_num: 2
    worker_vm_size: Standard_B2s
    nfs_vm_size: Standard_B2s
    nfs_local_storage_sz: 1023
    vm_image: Canonical:UbuntuServer:18.04-LTS:18.04.201910030
    nfs_vm:
    - suffix: toad
      data_disk_num: 2
      data_disk_sz_gb: 31
      data_disk_sku: Premium_LRS
      data_disk_mnt_path: /data

nfs_mnt_setup:
  - server_suffix: toad
    mnt_point:
      firstshare:
        curphysicalmountpoint: /mntdlws/nfs
        filesharename: /data/share
        mountpoints: ''
```
* cluster_name: A name without underscore or numbers (purely consisting of lower case letters) is recommended.

* infra_node_num: Should be odd (1, 3 or 5), number of infrastructure node for the deployment. 3 infrastructure nodes tolerate 1 failure, and 5 infrastructure nodes tolerate 2 failures. However, more infrastructure nodes (and more failure tolerance) will reduce performance of the node. 

* worker_node_num: Number of worker nodes used for deployment. 

* nfs_node_num: Number of worker nodes used for deployment. 

* vm_image: Used to fix the image version if the changing LTS is breaking the consistency of the deployment.

* azure_location: 

Please use the following to find all available azure locations. 
```
az account list-locations
```

* nfs_local_storage_sz: specifies size of the local storage (which won't be shared with infra/worker nodes) of nfs node.

* infra_vm_size, worker_vm_size, nfs_vm_size: infrastructure and worker VM size. 

Usually, a CPU VM will be used for infra_vm_size, and a GPU VM will be used for worker_vm_size. Please use the following to find all available Azure VM size. 
```
az vm list-sizes --location westus2
```
* nfs_data_disk_sz, nfs_data_disk_num: specify default data disk size/number of data disk of an NFS node, this would be overwritten by items in nfs_vm. 

* nfs_vm: specifies the specs of a certain NFS node, and we could further specify the suffix/name of the NFS machine that we want to apply this spec to, and it needs to be consistent with nfs_mnt_setup item

* nfs_mnt_setup: configures mounting source path (filesharename) and destination path (curphysicalmountpoint)


## remaining configuration items for both pipelines ##
No matter which pipeline is chosen, following items should be specified:

```
master_token: <a master token used for front end>
activeDirectory:
  tenant: <tenant ID, usually associated with a corp, such as Microsoft>
  clientId: <AAD app ID>
  clientSecret: <AAD app secret>

repair-manager:
  cluster_name: <clustername of a repair-manager>
  alert:
    smtp_url: <smtp_url>
    login: <email account that would send email to receivers, such as 'dlts-bot@microsoft.com'>
    password: <password for the email account above>
    sender: 'dlts-bot@microsoft.com'
    receiver:
    # list of recepients to be included in all alert emails
    - 'DLTSDRI@microsoft.com'
  # rule details
  ecc_rule:
    dry_run: False
    
datasource: MySQL    
mysql_password: msqpwd
WinbindServers: []

priority: regular
nfs_client_CIDR:
  node_range:
    - "192.168.0.0/16"
  samba_range:
    - "s.a.m.0/24"

WebUIregisterGroups:
- MicrosoftUsers

WebUIauthorizedGroups : []
WebUIadminGroups : ["CCSAdmins"]
WebUIregisterGroups: [ "MicrosoftUsers" ]

DeployAuthentications : ["Corp"]

webuiport: 80

cloud_config:
  default_admin_username: core
  dev_network:
    source_addresses_prefixes:
    # These are the dev box of the cluster, only the machine in the IP address below will have access to the cluster.
    - "b.a.0.0/16"
    - "z.x.0.0/16"
  nfs_share:
    source_ips: 
      # IPs that we want to share NFS storage to
      - "x.y.z.0/24"
      - "a.b.0.0/16"
  nfs_ssh:
    source_ips: 
      # IPs that that we want to use to ssh to NFS nodes
      - "q.w.e.0/24"
      - "r.f.0.0/16"
    port: "22"

prometheus:
  cluster_name: zxdashboard # will be used in link to job detail page

registry_credential:
  <docker registry 1>:
    username: <docker username 1>
    password: <docker password 1>
  <docker registry 2>:
    username: <docker username 2>
    password: <docker password 2>
  ...

```

```
cluster_name: exitedtoad
azure_cluster: 
  <your cluster name>:
    "infra_node_num": 1
    "worker_node_num": 2 
    "azure_location": "westus2"
    "infra_vm_size": "Standard_DS1_v2"
    "worker_vm_size": "Standard_NC6"
    "vm_image" : "Canonical:UbuntuServer:18.04-LTS:18.04.201907221"
datasource: MySQL
webuiport: 80
mysql_password: <your password>
cloud_config:
   default_admin_username: core
   dev_network:
     source_addresses_prefixes:
     # These are the dev box of the cluster, only the machine in the IP address below will have access to the cluster.
     - "<devbox IP>/32"
registry_credential:
  <docker image registry name 1>:
    username: <user name>
    password: <pass word>
``` 

* registry_credential: defines your access to certain dockers. A docker image name consists of three parts - registry name, image name, and image tag. If your job needs a certain private docker, then use 0. the registry name of that docker, 1. your user name and 2. your password to specify your access to it.