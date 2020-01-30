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
cluster_name: <your cluster name>

cloud-init: True
azure_cluster:
  # subscription: <your Azure subscription>
  # resource_group: <your resource group name. ${cluster_name}ResGrp if unspecified>
  azure_location: eastus
  virtual_machines:
    - vm_size: Standard_B2s
      vm_image: Canonical:UbuntuServer:18.04-LTS:18.04.201912180
      role: 
        - infra
        - kubernetes_master
        - etcd
      managed_disks:
        - sku: Premium_LRS
          is_os: True
          size_gb: 64
          disk_num: 1
        - sku: Premium_LRS
          size_gb: 64
          disk_num: 1
      kube_services:
        - nvidia-device-plugin
        - flexvolume
        - mysql
        - jobmanager
        - restfulapi
        - monitor
        - dashboard
        - user-synchronizer
      number_of_instance: 1

    - vm_size: Standard_B2s
      vm_image: Canonical:UbuntuServer:18.04-LTS:18.04.201912180
      role: 
        - nfs
      managed_disks:
        - sku: Premium_LRS
          is_os: True
          size_gb: 64
          disk_num: 1
        - sku: Premium_LRS
          size_gb: 128
          disk_num: 1
      data_disk_mnt_path: /data
      private_ip_address: 192.168.0.9
      fileshares:
        - nfs_local_path: /data/share/ads/jobfiles
          remote_mount_path: /mntdlws/nfs/ads/jobfiles
          remote_link_path: /dlwsdata/ads/jobfiles
        - nfs_local_path: /data/share/ads_not_expected_before/jobfiles
          remote_mount_path: /mntdlws/nfs/ads1/jobfiles
          remote_link_path: /dlwsdata/ads1/jobfiles
        - nfs_local_path_root: /data/share/
          remote_mount_path_root: /mntdlws/nfs
          remote_link_path_root: /dlwsdata
          leaves:
            - nfs_local_path: jobfiles
              remote_mount_path: jobfiles
              remote_link_path: jobfiles
            - nfs_local_path: storage
              remote_mount_path: storage
              remote_link_path: storage
            - nfs_local_path: work
              remote_mount_path: work
              remote_link_path: work  
          # vc: Ads
      number_of_instance: 1
      
    - vm_size: Standard_B2s
      vm_image: Canonical:UbuntuServer:18.04-LTS:18.04.201912180
      role:
        - worker
      gpu_type: None
      # availability_set: <availability set name>
      number_of_instance: 1

master_token: <DLTS master token for generating user passwords>
activeDirectory:
  tenant: <tenant ID, usually associated with a corp, such as Microsoft>
  clientId: <AAD app ID>
  clientSecret: <AAD app secret>

repair-manager:
  alert:
    smtp_url: <smtp url>
    login: <email account that would send email to receivers, such as 'dlts-bot@microsoft.com'>
    password: <password for the email account above>
    sender: 'dlts-bot@microsoft.com'
    receiver:
    # list of recepients to be included in all alert emails
    - DLTSDRI@microsoft.com
  # rule details
  ecc_rule:
    dry_run: False
    
datasource: MySQL
mysql_password: <password>
WinbindServers: []

priority: regular
nfs_client_CIDR:
  node_range:
    - "192.168.0.0/16"
  samba_range:
    - "s.a.m.0/24"

cloud_config_nsg_rules:
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

registry_credential:
  <docker registry name 1>:
    username: <docker registry username 1>
    password: <docker registry password 1>
  <docker registry name 2>:
    username: <docker registry username 2>
    password: <docker registry password 2>
  ...
```

Each item in `cnf["azure_cluster"]["virtual_machines"]` means spec for a set of machines, the properties of which are explained as follows: 

* `role`: functional role (DLTS-wise) of the set of machines.
* `managed_disks`: storage setting of the set of machines.
* `kube_services`: kubernetes services to run on the machines.
* `availability_set`: optional availability set under which we create the machines.
* `number_of_instance`: number of machine instances with the current spec.
* `data_disk_mnt_path`: the path that all data disks are mounted to.
* `private_ip_address`: use to bind certain private IP to a machine. If this parameter is specified, number_of_instance should be 1.
* `fileshares`: mounting paths for NFS service. `nfs_local_path` on NFS machines are mounted to `remote_mount_path`, then soft-linked to `remote_link_path`. NFS service might fail. We use the soft-link trick because it guarantees that when NFS service fails, operations would also fail, and we could know. Before we fix it, attempted operations would fail, but no vital damage would be caused. To allow less user effort, we also support stem-leaves mode, where users specify "stem" of paths, (such as `nfs_local_path_root`), and probably `vc` if the NFS machine is for dedicated storage, then several sub paths under `leaves`, and then a joined path would be generated.
* `gpu_type`: specified for worker machines. Currently all workers in a cluster have the same type of GPU

Some other properties that worth mentioning:

* `cluster_name`: a name without underscore or numbers (purely consisting of lower case letters) is recommended.
* `azure_location`: azure location of the cluster.

Please use the following to find all available azure locations. 
```
az account list-locations
```

* `nfs_client_CIDR`: specifies a list of IP ranges that can access NFS servers. Private IPs are allowed.
* `cloud_config_nsg_rules`: specifies the Azure network security group rules, `dev_network` defines the IP ranges that have access (including ssh etc.) to the cluster, `nfs_share` defines IP ranges that can communicate with storage nodes, and `nfs_ssh` defines the IP ranges from where we can ssh to the storage nodes, and the IPs should be public IPs.
* `registry_credential`: defines access to private docker registries.
