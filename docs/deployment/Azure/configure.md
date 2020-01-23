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

for each item in cnf["azure_cluster"]["vm"], we specify a machine spec, including role(s), storage, how many instance we want that follow this spec etc. Depending on role specified, we could further configure mounting plan/kubernetes service we want to run etc.

* cluster_name: A name without underscore or numbers (purely consisting of lower case letters) is recommended.

* azure_location: 

Please use the following to find all available azure locations. 
```
az account list-locations
```

* registry_credential: defines your access to certain dockers. A docker image name consists of three parts - registry name, image name, and image tag. If your job needs a certain private docker, then use 0. the registry name of that docker, 1. your user name and 2. your password to specify your access to it.
