# Deploy DL Workspace cluster on Azure. 

This document describes the procedure to deploy a DL Workspace cluster on Azure. With autoscale enabled DL Workspace, VM will be created (and released) on demand when you launch DL jobs ( e.g., TensorFlow, Pytorch, Caffe2), thus save your money in operation.

Please note that the procedure below doesn't deploy HDFS/Spark on DLWorkspace cluster on Azure (Spark job execution is not available on Azure Cluster).

Prerequisite steps:
First require the manager to add you into a subscription group., then either 
1. go to that group from Azure Portal and add ubuntu server from resources, this virtual server is your devbox, or 
2. if you have a physical machine, install ubuntu server system(18.04) on that and use it as your devbox
then use the devbox to deploy node on cloud.

Workflow:
1. Please [configure](configure.md) your azure cluster. Put config.yaml under src/ClusterBootstrap

2. Change directory to src/ClusterBootstrap on devbox, and install prerequisite packages:
```
cd src/ClusterBootstrap/ 
sudo ./install_prerequisites.sh
```
3. Login to Azure, setup proper subscription and confirm
```
SUBSCRIPTION_NAME="<subscription name>" 
az login
az account set --subscription "${SUBSCRIPTION_NAME}" 
az account list | grep -A5 -B5 '"isDefault": true'
```
Configure your location, should be the same as you specified in config.yaml file:
```AZ_LOCATION="<your location>"```
Execute this command, log out(exit) and log in back
```sudo usermod -aG docker zhe_ms```

After these devbox configuration steps (one-time effort) and setting up a config.yaml src/ClusterBootstrap, execute
```./step_by_step.sh <platform>```  
to deploy a cluster. `<platform>` here could be `azure` if you want a cluster on Azure, or `onpremise` if you want to deploy it on your own machines. Currently we don't support deploying DLTS on existing Kubernetes clusters.


4.  To manually connect to the node, run:
```./deploy.py connect <role> [id]```

After finishing deploying the cluster, we need to further configure it. 
Connect to infra node, and use following command to enter the mysql docker container:

Login to infra node by `./deploy.py connect master`, then on infra node,

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

5. If you run into a deployment issue, please check [here](FAQ.md) first.


# Adding more machines
To add more nodes to the cluster, re-configure `config.yaml`, delete `azure_cluster_config.yaml` if it exists.
If the nodes you want to add are worker nodes, invoke `az_tools.py addworkers`,

Sometimes you might also want to add a new NFS node, that's considered a cluster change. Contact us for more details.

# Detail of `step_by_step.sh`

Here's the detail of `step_by_step.sh`, which might be helpful in figuring out failures during deployment:

compared to cloud-init deployment, this pipeline works in a synchronous manner. A typical step in this pipeline generates files/binaries used for a certain function module on devbox, copies them to all applicable machines in the cluster, and then executes scripts on all those machines.

If the cluster is deployed on Azure, we have some automation to simplify the procedure:

1. Initiate cluster and generate certificates and keys
```./deploy.py -y build```

2. Create Azure Cluster
```./az_tools.py create```

3. Generate cluster config file
```./az_tools.py genconfig```

4. partition and label disks of 
```./deploy.py runscriptonroles infra worker ./scripts/prepare_vm_disk.sh```

Otherwise -- if a on-premise cluster is to be deployed, ```./deploy.py build``` should be executed and the deployer should set up config.yaml manually(configure parameters like worker_node_num, network_domain)

Then we have following steps that are necessary regardless of the platform:

5. set up NFS-server
```./deploy.py nfs-server create```

6. install packages and set up rules on infra and worker machines.
```./deploy.py runscriptonroles infra worker ./scripts/prepare_ubuntu.sh```
```./deploy.py runscriptonroles infra worker ./scripts/disable_kernel_auto_updates.sh```
```./deploy.py runscriptonroles infra worker ./scripts/docker_network_gc_setup.sh```
```./deploy.py runscriptonroles infra worker ./scripts/disable_mlocate.sh```

7. Configure DNS for infra and worker
```./deploy.py genscripts```
```./deploy.py runscriptonroles infra worker ./scripts/dns.sh```

8. Deploy master node 
```./deploy.py -y deploy```

9. Deploy worker nodes
```./deploy.py -y updateworkerinparallel```

10. Label nodes
```
./deploy.py -y kubernetes labels
./deploy.py -y gpulabel
./deploy.py labelsku
```

11. Render RestfulAPI and front end related files
```./deploy.py webui```

12. Push docker images
```
./deploy.py docker push restfulapi
./deploy.py docker push webui
./deploy.py docker push watchdog
./deploy.py docker push gpu-reporter
./deploy.py docker push reaper
./deploy.py docker push job-exporter
./deploy.py docker push init-container
./deploy.py docker push dashboard
./deploy.py docker push user-synchronizer
```

13. Mount NFS storage to infra and worker nodes
```./deploy.py mount```

14. start kubernetes services
```
./deploy.py kubernetes start nvidia-device-plugin
./deploy.py kubernetes start flexvolume
./deploy.py kubernetes start mysql
./deploy.py kubernetes start jobmanager
./deploy.py kubernetes start restfulapi
./deploy.py kubernetes start monitor
./deploy.py kubernetes start dashboard
./deploy.py kubernetes start user-synchronizer
```

15. Login to necessary docker registries corresponding to training jobs that would be submitted by users of the cluster
```./deploy.py --sudo runscriptonrandmaster ./scripts/pass_secret.sh```

16. Predownload specified training job docker images
```./deploy.py runscriptonroles worker scripts/pre_download_images.sh```