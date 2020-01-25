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
cluster_name: imprvcnf

cloud-init: True
azure_cluster:
  # name_of_cluster should match cluster name used above.
  azure_location: eastus
  virtual_machines:
    - vm_size : Standard_B2s
      vm_image: Canonical:UbuntuServer:18.04-LTS:18.04.201910030
      role: 
        - infra
        - kubernetes_master
        - etcd
      managed_disks:
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
        - user-synchronizer
      # availability_set: <availability_set>
      number_of_instance: 1
    - vm_size : Standard_B2s
      role: 
        - nfs
      managed_disks:
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
          # VC: Ads
      number_of_instance: 1
      
    - vm_size : Standard_B2s
      vm_image: Canonical:UbuntuServer:18.04-LTS:18.04.201910030
      role: 
        - worker
      gpu_type: None
      number_of_instance: 1

master_token: <a master token used for front end>
activeDirectory:
  tenant: <tenant ID, usually associated with a corp, such as Microsoft>
  clientId: <AAD app ID>
  clientSecret: <AAD app secret>

repair-manager:
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
mysql_password: <pass word>
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
  <docker registry 1>:
    username: <docker username 1>
    password: <docker password 1>
  <docker registry 2>:
    username: <docker username 2>
    password: <docker password 2>
  ...
  
```

Each item in cnf["azure_cluster"]["virtual_machines"] means spec for a set of machines, and meaning of keys are explained as follows: 

* role: Functional role (DLTS-wise) of the set of machines
* managed_disks: storage setting of the set of machines
* kube_services: kubernetes-initiated services we want to run on the machines
* availability_set: availability set under which we want to put the machines, this is usually set for billing convenience
* number_of_instance: number of instances we want that go with this spec
* data_disk_mnt_path: the path that all data disks are mounted to
* private_ip_address: use to bind certain private IP to a machine. It's obvious that when this parameter is specified, number_of_instance should be 1
* fileshares: mounting paths for NFS service. `nfs_local_path` on NFS machines are mounted to `remote_mount_path`, then soft-linked to `remote_link_path`. NFS service might fail, which is inevitable. We use the soft-link trick because it guarantees that when NFS service fails, operations would also fail, and we could know. Before we fix it, attempted operations would fail, but no vital damage would be caused. To allow less user effort, we also support stem-leaves mode, where users specify "stem" of paths, (such as `nfs_local_path_root`), and probably VC if the NFS machine is for dedicated storage, then several sub paths under `leaves`, and then a joined path would be generated.
* gpu_type: specified for worker machines. Currently all workers in a cluster have the same type of GPU

Now we would explain other items that might be confusing.

* cluster_name: a name without underscore or numbers (purely consisting of lower case letters) is recommended.

* azure_location: azure location of the cluster

Please use the following to find all available azure locations. 
```
az account list-locations
```

* nfs_client_CIDR: used to specify IP ranges that NFS service on storage nodes open to, its field could be private IP 

* cloud_config_nsg_rules: specifies the Azure network security group rules, `dev_network` defines the IP ranges that have access (including ssh etc.) to the cluster, `nfs_share` defines IP ranges that could communicate with storage nodes, and `nfs_ssh` defines the IP ranges from where we can ssh to the storage nodes, and the IPs should be public IPs

* registry_credential: defines your access to certain dockers. A docker image name consists of three parts - registry name, image name, and image tag. If your job needs a certain private docker, then use 0. the registry name of that docker, 1. your user name and 2. your password to specify your access to it.
