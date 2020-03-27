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

You may provide/change the specification of the deployed Azure cluster by editing the config.yaml, here's an example:

```
cluster_name: <unique cluster name, e.g. useanothername>

azure_cluster:
    infra_node_num: 1
    infra_vm_size : <az vm size, such as Standard_B2s>
    azure_location: eastus
    worker_node_num: 2
    nfs_node_num: 1
    nfs_data_disk_sz : 31
    nfs_data_disk_num: 2
    worker_vm_size: <az vm size, such as Standard_B2s>
    nfs_vm_size: <az vm size, such as Standard_B2s>
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

datasource: MySQL    
mysql_password: <password, e.g. useanotherpw!>
WinbindServers: []

priority: regular

nfs_client_CIDR:
  node_range:
    - "192.168.0.0/16"
  samba_range:
    - "s.a.m.0/24"

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
  latency_rule:
    alert_expiry: 4 # In hours

smtp:
  smtp_url: <smtp, like xxx.com:587>
  smtp_from: <email address that is used to send alert emails>
  smtp_auth_username: <username used for authentication, e.g. same as smtp_from>
  smtp_auth_password: <password for the username above>
  default_recipients: <email address that would receive alert email>
  cc: <email address that alert email would be cc to>

WebUIregisterGroups:
- MicrosoftUsers

WebUIauthorizedGroups : []
WebUIadminGroups : ["CCSAdmins"]
WebUIregisterGroups: [ "MicrosoftUsers" ]

DeployAuthentications : ["Corp"]

webuiport: 80

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

prometheus:
  cluster_name: <the unique cluster name> # will be used in link to job detail page

watchdog:
  vc_url: <url used for listing vc, e.g. http://localhost:5000/ListVCs?userName=Administrator>

prometheus:
  cluster_name: <the unique cluster name> # will be used in link to job detail page

job-manager:
  notifier:
    cluster: <cluster name>
    alert-manager-url: <url like http://localhost:9093/alert-manager>

registry_credential:
  <docker registry name 1>:
    username: <docker registry username 1>
    password: <docker registry password 1>
  <docker registry name 2>:
    username: <docker registry username 2>
    password: <docker registry password 2>
```

* cluster_name: A name without underscore or numbers (purely consisting of lower case letters) is recommended.

* infra_node_num: Should be odd (1, 3 or 5), number of infrastructure node for the deployment. 3 infrastructure nodes tolerate 1 failure, and 5 infrastructure nodes tolerate 2 failures. However, more infrastructure nodes (and more failure tolerance) will reduce performance of the node. 

* worker_node_num: Number of worker node used for deployment. 

* vm_image: Used to fix the image version if the changing LTS is breaking the consistency of the deployment.

* nfs_vm: each item identified by `suffix` specs would describe an NFS node, and this item would overwrite default NFS specs. A `server_suffix` entry in `nfs_mnt_setup` should map to this item.

* azure_location: azure location of the cluster.

Please use the following to find all available azure locations. 
```
az account list-locations
```

* infra_vm_size, worker_vm_size: infrastructure and worker VM size. 

Usually, a CPU VM will be used for infra_vm_size, and a GPU VM will be used for worker_vm_size. Please find all available Azure VM size in a specific region, e.g. West US 2 in the below command: 
```
az vm list-sizes --location <location, e.g. westus2>
```

* registry_credential: defines your access to certain dockers. A docker image name consists of three parts - registry name, image name, and image tag. If your job needs a certain private docker, then use 0. the registry name of that docker, 1. your user name and 2. your password to specify your access to it.