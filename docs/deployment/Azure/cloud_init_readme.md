# Deploy DLTS(deep learning training service) cluster on Azure 

This document describes the procedure to deploy a DL Workspace cluster on Azure. With autoscale enabled DL Workspace, VM will be created (and released) on demand when you launch DL jobs ( e.g., TensorFlow, Pytorch, Caffe2), thus save your money in operation.

Please note that the procedure below doesn't deploy HDFS/Spark on DLWorkspace cluster on Azure (Spark job execution is not available on Azure Cluster).

Prerequisite steps:
First require the manager to add you into a subscription group., then either 
1. go to that group from Azure Portal and add ubuntu server from resources, this virtual server is your devbox, or 
2. if you have a physical machine, install ubuntu server system(18.04) on that and use it as your devbox
then use the devbox to deploy node on cloud.

## Workflow:

First we need to setup the devbox that we use to operate on.

1. Change directory to src/ClusterBootstrap on devbox, and install prerequisite packages:
    ```
    cd src/ClusterBootstrap/ 
    ./install_prerequisites.sh
    ```
2. Login to Azure, setup proper subscription and confirm
    ```
    SUBSCRIPTION_NAME="<subscription name>" 
    az login
    az account set --subscription "${SUBSCRIPTION_NAME}" 
    az account list | grep --color -A5 -B5 '"isDefault": true'
    ```
3. Go to work directiry `src/ClusterBootstrap`
    ```
    cd src/ClusterBootstrap
    ```
4. [configure](cloud_init_configure.md) your azure cluster. Put `config.yaml` under `src/ClusterBootstrap`

5. Run below script to deploy the cluster
    ```
    ./deploy.sh
    ```

6. Further steps required if you want to submit job to confirm that the deployment is successful. 

After finishing deploying the cluster, we need to further configure it. 
Connect to infra node, and use following command to enter the mysql docker container:

Login to infra node by `./ctl.py connect infra 0`, then on infra node,

```docker exec -it $(sudo docker ps | grep mysql_mysql | awk '{print $1}') bash```

to enter the mysql docker container.

Enter the mysql container, run (-u -p according to your own setting in config):
`mysql -u <user name> -<password>`

Enter mysql, use `show databases` to list db, and run:
`use <DLWS-initiated db>;`

Add following entries for users:

INSERT INTO \`acl\` (\`id\`, \`identityName\`, \`identityId\`, \`resource\`, \`permissions\`, \`isDeny\`) VALUES (2, '<user account>', <uid>, 'Cluster', <3 for general users, 7 for cluster managers who is maintaining the cluster>, 0);

INSERT INTO \`identity\` (\`id\`, \`identityName\`, \`uid\`, \`gid\`, \`groups\`) VALUES (2, '<user account>', <uid>, <gid>, < group info, e.g. `"[\"CCSAdmins\", \"MicrosoftUsers\"]"`);

Then after existing the mysql docker container, we need to refresh the RestfulAPI cache:
`kubectl get pods` to get RestfulAPI pod, then run
```kubectl exec -it <RestfulAPI> bash```
and execute `apachectl restart` in the pod.

`vc` table would be setup with a default `platform` vc(virtual cluster). To assign a certain user/sg to a vc, the corresponding `resource` field should be filled with `Cluster/VC:<vc name>`

After all these configurations, you should be able to submit jobs.
If you run into a deployment issue, please check [here](FAQ.md) first.

# Admin tools and Maintanence

`./ctl.py` is the main file used for maintaining a cluster. It provides several handy tools that provide more convenient interface for developers. We introduce some commands below:

## back up and restore cluster information
```
./ctl.py backuptodir <path> (e.g., ./ctl.py backuptodir ~/Deployment/Azure-EASTUS-V100)
./ctl.py restorefromdir <path> (e.g., ./ctl.py restorefromdir ~/Deployment/Azure-EASTUS-V100)
```
Rendered files and binaries would often occupy quite some space on disk. We don't need most of those files after the deployment. We backup several yaml files: 
  1. config.yaml, which describes the "fixed and firm" configuration of a cluster, such as NSG rules, alert email addresses, docker registry etc.
  2. action.yaml, which describes one-time deployment action.
  3. status.yaml, which describes the up-to-date machine info of the cluster. Whoever changed the cluster(added/removed machines, etc.) last would be responsible of updating this file and backup/let colleagues know.
besides yamls, we also need a cluster ID, sshkey and k8s basic authentication. These are all fixed, and independent of later deployment.

## adding more machines
This might be the only maintain task where need `cloud_init_aztools.py` instead of `ctl.py`.
To add more machines(multi-infra not supported now), either 
1. re-configure `azure_cluster.virtual_machines` in `config.yaml`, (leave/uncomment only the items corresponding to machines you want to add, delete/comment previously existing items that were used to generate machine list for previous deployment/maintanence) and use below command:
```
./cloud_init_aztools.py prerender
```
or 
2.
Edit `action.yaml` directly, keep only the machine items that you want to deploy for this time.
You may want to save the previous config files in advance.

After reconfiguration, you may use below commands to finish the new deployment of several nodes to the existing cluster:

if you are adding NFS node, need to run these lines in advance:

```
./cloud_init_deploy.py render
./cloud_init_deploy.py pack
./cloud_init_deploy.py docker push cloudinit
```

then run below lines. (start from here if you are adding workers only)
```
./cloud_init_deploy.py render
./cloud_init_aztools.py -v addmachines
./cloud_init_aztools.py listcluster
./cloud_init_aztools.py interconnect
```

Sometimes you might also want to add a new NFS node, which currently has not been automated. Any change to infra node would be considered a cluster change, as for now, we redeploy the whole cluster instead of adding a infra node. Contact us for more details.

## dynamically scaling up/down # or workers
specify "dynamic_worker_num" in config.yaml, 
and use `./cloud_init_aztools.py dynamic_around`.
the monitoring frequency is specified by "monitor_again_after" in config.yaml

## connect to nodes
```
./ctl.py connect <role> <index> (e.g. ./ctl.py connect infra 0)
./ctl.py connect <nodename> (e.g. ./ctl.py connect azure-eastus-worker-ranstr)
```

## invoke kubectl
```
./ctl.py kubectl get nodes
```
pretty much the same as you use kubectl, just add `./ctl.py` at the beginning. Also, `./ctl.py download` might be necessary to download some binaries including kubectl itself to the proper paths.

## run scripts or command in parallel
```
./ctl.py [-s] [-v] [-r <role1> [-r <role2>] ...] [-r <nodename1> [-r <nodename2>]] runscripts <script path>
./ctl.py [-s] [-v] [-r <role1> [-r <role2>] ...] [-r <nodename1> [-r <nodename2>]] runcmd <command>
e.g.
./ctl.py -v -r infra runscript scripts/mytest.sh
./ctl.py -v -r infra -r zxgdv-worker-frog runcmd "touch testfile"
```
Notice that here the script path cannot be src/ClusterBootstrap since it contains too many files, while the environment folder -- or parent path -- of the script that is to be executed would be copied to target machine when run `runscripts`, so it's recommended to put the scripts under `scripts` or `deploy/scripts` etc before execute it remotely.

## copy files to remote nodes
```
./ctl.py [-s] [-v] [-r <role1> [-r <role2>] ...] [-r <nodename1> [-r <nodename2>]] copy2 <source path> <destination path>
```

## start/stop service
If you need to update service config of an already deployed node, edit status.yaml, not config.yaml
```
./ctl.py svc stop <service1, service2, ...> (e.g., ./ctl.py svc stop monitor)
./ctl.py svc start <service1, service2, ...> (e.g., ./ctl.py svc start monitor)
```
when you use `svc start`, the services would be rendered first, then kubectl would start a service

## render a service
```
./ctl.py svc render <service1, service2, ...> (e.g., ./ctl.py svc render monitor)
```
useful when you don't want to actually restart a service, just wander how you edition to config.yaml would come to effect

## update remote config file used by a service
```
./ctl.py svc configupdate [dashboard | restfulapi | storagemanager]
```
this subcommand would retire after we use configmap to configure parameters for the 3 listed services

## options
Some advanced tricks are possible if you are familiar with options.
In general, `-cnf` specifies what config files to use, we try our best to eliminating overlapping content, but if there's any confilict, the later loaded configuration would override the previous ones. `-s` specifies sudo mode, which should be used when you want to copy a certain file to sub directory of `/etc/` etc. on remote machines. `-v` is set to enable verbose mode. `-d` would mean `dryrun` -- az cli wouldn't be executed, only render some files. Dryrun mode would usually be used together when `-o` option is on so you can dump the commands to a file without actually executing them. For instance:
```
./cloud_init_aztools.py -v -cnf config.yaml -cnf action.yaml -d -o scripts/addmachines.sh addmachines
```

# Details in deploy.sh

We will explain the operations behind `deploy.sh` in this section. 

Clean up existing binaries/certificates etc. and action yaml files:
```
shopt -s extglob
rm -rf deploy/!(bin) cloudinit* !(config).yaml
```

Generate action yaml file `action.yaml` based on given configuration file `config.yaml` of a cluster (machine names are generated if not specified):
```
./cloud_init_deploy.py clusterID
./cloud_init_aztools.py prerender
```

Deploy the framework of a cluster, including everything but VMs.
```
./cloud_init_aztools.py -v deployframework
```

Render templates, generate certificates and prepare binaries for cluster setup:
```
./cloud_init_deploy.py render
```

Pack all the generated files in the previous step into a tar file:
```
./cloud_init_deploy.py pack
```

Push docker images that are required by services specified in configuration:
```
./cloud_init_deploy.py docker servicesprerequisite
```

Deploy VMs in the cluster:
```
./cloud_init_aztools.py -v addmachines
```

List VMs in the cluster:
```
./cloud_init_aztools.py listcluster
```

Generate a yaml file `status.yaml` for cluster maintenance:
```
./cloud_init_aztools.py interconnect
```
