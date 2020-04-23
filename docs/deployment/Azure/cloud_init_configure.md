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
        - logging
      number_of_instance: 1

    - number_of_instance: 1
      name: lustclean-lustre-mdt
      vm_size : Standard_B2s
      vm_image: OpenLogic:CentOS-CI:7-CI:7.7.20190920
      role: 
        - lustre
        - mdt
      managed_disks:
        - sku: Premium_LRS
          is_os: True
          size_gb: 64
          disk_num: 1
        - sku: Premium_LRS
          size_gb: 64
          disk_num: 1
      fileshares:
      - server_path: /lustrefs
        client_mount_root: /mntdlws/lustre
        # if exist, dsts join(linkroot, vc, leaf)
        client_link_root: /dlwslustre
        client_links:
          - src: jobfiles
            dst: jobfiles
          - src: storage
            dst: storage
          - src: work
            dst: work
      data_disk_mnt_path: /lustre
      private_ip: 192.168.249.1

    - number_of_instance: 2
      vm_size : Standard_B2s
      vm_image: OpenLogic:CentOS-CI:7-CI:7.7.20190920
      role: 
        - lustre
        - oss
      managed_disks:
        - sku: Premium_LRS
          is_os: True
          size_gb: 64
          disk_num: 1
        - sku: Premium_LRS
          size_gb: 128
          disk_num: 3

    - number_of_instance: 1  
      name: lustclean-nfs-storage
      vm_size : Standard_B2s
      vm_image: Canonical:UbuntuServer:18.04-LTS:18.04.202001210
      role: 
        - nfs
      managed_disks:
        - sku: Premium_LRS
          is_os: True
          size_gb: 64
          disk_num: 1
        - sku: Premium_LRS
          size_gb: 64
          disk_num: 2
      data_disk_mnt_path: /data
      private_ip: 192.168.254.1
      fileshares:
        - server_path: /data/share
          client_mount_root: /mntdlws/nfs
          # if exist, dsts join(linkroot, vc, leaf)
          client_link_root: /dlwsdata
          client_links:
            - src: jobfiles
              dst: jobfiles
            - src: storage
              dst: storage
            - src: work
              dst: work
      storage_manager:
        rest_url: http://192.168.255.1:5000
        scan_points:
          - path: /data/share/work
            alias: /home
          - path: /data/share/storage
            alias: /data
          - path: /data/share/storage/aether
            alias: /data/aether
            expired_rule: True
            expired_to_delete_rule: True
            days_to_delete_after_expiry: 1
          - path: /data/share/storage/local
            alias: /data/local
            expired_rule: True
            expired_to_delete_rule: True
            days_to_delete_after_expiry: 1
      
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

domain-offset:
  <url1>: <value1>
  <url2>: <value2>
  <can also set '*'>: <value0>


repair-manager:
  portal_url:  <a domain name, e.g. dltshub.mydomain.com>
  ecc_rule:
    cordon_dry_run: False
    reboot_dry_run: True
    alert_job_owners: True
    days_until_node_reboot: 5
    time_sleep_after_pausing: 30
    attempts_for_pause_resume_jobs: 10
  rest_url: http://localhost:5000
  restore_from_rule_cache_dump: True
  rule_cache_dump: /etc/RepairManager/rule-cache.json
  job_owner_email_domain: <an email domain name like microsoft.com>
  etcd:
    data-dir: /etc/RepairManager/etcd
    peer-port: 2381
    client-port: 2382

smtp:
  smtp_url: <smtp, like xxx.com:587>
  smtp_from: <email address that is used to send alert emails>
  smtp_auth_username: <username used for authentication, e.g. same as smtp_from>
  smtp_auth_password: <password for the username above>
  default_recipients: <email address that would receive alert email>
  cc: <email address that alert email would be cc to>

alert-manager:
  configured: True
  alert_users: False # True if we want to send out alert email to users, default False
  smtp_url: <smtp url>
  smtp_from: <email address used to send alert emails, e.g. 'dlts-bot@microsoft.com'>
  smtp_auth_username: <email account that would send email to receivers, such as 'dlts-bot@microsoft.com'>
  smtp_auth_password: <password for the email account above>
  receiver: <email address to send alert email to>

  reaper:
    dry-run: True # change to False if we want to kill idle job
    restful-url: http://localhost:5000

watchdog:
  vc_url: <url used for listing vc, e.g. http://localhost:5000/ListVCs?userName=Administrator>

prometheus:
  cluster_name: <cluster name>
  alerting:
    kill-idle:
      VC1: 4
      VC2: 12

job-manager:
  notifier:
    cluster: <cluster name>
    alert-manager-url: <url like http://localhost:9093/alert-manager>
  launcher: controller

datasource: MySQL
mysql_node: <could be fqdn of an integrated database, justanexample.westus2.cloudapp.azure.com>
mysql_username: <root if mysql_node option above is not configured>
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

private_docker_registry: 
  cloudinit: <docker registry for cloudinit, since that docker image contains some sensitive information>

private_docker_credential:
  <private docker registry>:
    username: <private docker username>
    password: <private docker password>

registry_credential:
  <docker registry name 1>:
    username: <docker registry username 1>
    password: <docker registry password 1>
  <docker registry name 2>:
    username: <docker registry username 2>
    password: <docker registry password 2>
  ...

infiniband_mounts:
  - name: rdma-cm
    hostPath: /dev/infiniband/rdma_cm
    containerPath: /dev/infiniband/rdma_cm
  - name: ib-uverbs0
    hostPath: /dev/infiniband/uverbs0
    containerPath: /dev/infiniband/uverbs0
  - name: ib-issm0
    hostPath: /dev/infiniband/issm0
    containerPath: /dev/infiniband/issm0
  - name: ib-umad0
    hostPath: /dev/infiniband/umad0
    containerPath: /dev/infiniband/umad0
  - name: ib-uverbs0
    hostPath: /dev/infiniband/uverbs0
    containerPath: /dev/infiniband/umad0

# Enable azure blobfuse
enable_blobfuse: True

# Local fast storage mountpoint
local_fast_storage: /mnt/local_fast_storage

# Enable custom docker registry secrets, this is for user of the cluster, not developers who deployed the cluster
enable_custom_registry_secrets: True

integration-test:
  azure-blob:
    account: <account>
    key: <key>
    container: <container>

```

# Azure general configuration

Each item in `cnf["azure_cluster"]["virtual_machines"]` means spec for a set of machines, the properties of which are explained as follows: 

* `vm_size`: vm_size that azure requires when specifying what type of node is to be used
Usually, CPU VMs will be used as infra node, and GPU VMs will be used for worker node. Please find all available Azure VM size in a specific region, e.g. West US 2 in the below command: 
```
az vm list-sizes --location <location, e.g. westus2>
```
* `role`: functional role (DLTS-wise) of the set of machines.
* `managed_disks`: storage setting of the set of machines.
* `kube_services`: kubernetes services to run on the machines.
* `availability_set`: optional availability set under which we create the machines.
* `number_of_instance`: number of machine instances with the current spec.
* `data_disk_mnt_path`: the path that all data disks are mounted to.
* `private_ip`: use to bind certain private IP to a machine. If this parameter is specified, number_of_instance should be 1.

Some other properties that worth mentioning:

* `cluster_name`: a name without underscore or numbers (purely consisting of lower case letters) is recommended.
* `azure_location`: azure location of the cluster.

Please use the following to find all available azure locations. 
```
az account list-locations
```

* `cloud_config_nsg_rules`: specifies the Azure network security group rules, `dev_network` defines the IP ranges that have access (including ssh etc.) to the cluster, `nfs_share` defines IP ranges that can communicate with storage nodes, and `nfs_ssh` defines the IP ranges from where we can ssh to the storage nodes, and the IPs should be public IPs.
* `registry_credential`: defines access to private docker registries.

# Storage Related configuration (mount and link, Lustre)
lustclean-nfs-storage example above would setup up mounting as: 

mount `192.168.254.1`(the storage server IP):`/data/share` to `/mntdlws/nfs` on client,
link `/mntdlws/nfs/jobfiles` to `/dlwsdata/jobfiles` (link source and destination both on client)
link `/mntdlws/nfs/work` to `/dlwsdata/work`
link `/mntdlws/nfs/storage` to `/dlwsdata/storage`

* `fileshares`: mounting paths for NFS service. `server_path` on NFS machines are mounted to `client_mount_root`. Each link `src` under `client_links` would be soft-linked to corresponding `dst`. If `src` is a relative path, if would be prepended with `client_link_root`. If `vc` is specified for dedicated storage, vc name might be inserted to the paths. 

NFS service might fail. We use the soft-link trick because it guarantees that when NFS service fails, operations would also fail, and we could know. Before we fix it, attempted operations would fail, but no vital damage would be caused. 
* `nfs_client_CIDR`: specifies a list of IP ranges that can access NFS servers. Private IPs are allowed.

Currently, if Lustre support is desired, the only supported lustre server vm image is `OpenLogic:CentOS-CI:7-CI:7.7.20190920`, and the only supported client image is `Canonical:UbuntuServer:18.04-LTS:18.04.201912180`