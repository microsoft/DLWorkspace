# Deploy DL workspace cluster on a cluster on an already deployed with CoreOS cluster

This document describes the procedure to deploy DL workspace on a prior deployed CoreOS cluster. This document is still evolving. Please contact the author for any question. Our latest deployment is more focused on Ubuntu, so this portion may be a bit outdated. 

1. [Configuration cluster](configuration/Readme.md).
  
  * Please copy src/ClusterBootstrap/config_coreos.yaml.template to src/ClusterBootstrap/config.yaml, fill in the cluster name, number of etcd server, domain, and the machines involved in the deployment. 
  ```
  cluster_name : <<your_cluster_name>>
  etcd_node_num : 3
  network:
    domain: <<your_cluster_domain>>
    container-network-iprange: "<<your_cluster_ip_range, in 10.109.x.x/24 format>>" 

  machines:
    <<infrastructure_machine_1>>:
      role: infrastructure
    <<infrastructure_machine_2>>:
      role: infrastructure
    <<worker_machine>>:
      role: worker
  ```

  * Configure and setup the [databased](../database/Readme.md) used in the cluster.
  
  * Please edit cluster.yaml generated in the step above, and remove/change :
  ```
  deploydockerETCD: true [change from false -> true]
  platform-scripts: coreos [change from ubuntu -> coreos]
  ```   
   
2. [Build deployment configuration] (Build.md).
  
  ```
  ./deploy.py -y build 
  ```

  If the machine is imaged through the [PXEServer](PXEServer) process, you can skip this step. If the machine is imaged and provided to you, please fill in config.yaml the installation username:
  ```
  admin_username: <<yourusername>>
  ```
  and put password in ./deploy/sshkey/rootpasswd. The run 
  ```
  ./deploy.py sshkey install
  ```
  After this step, you should be able to access the cluster via [Scripts](../Scripts/Readme.md). Please make sure that the user is in sudo and docker group.  

3. Partition hard drive, if necessary. Please refer to section [Partition](Repartition.md) for details. 

4. Setup kubernetes
  
  ```
  ./deploy.py download kubectl 
  ./deploy.py -y deploy
  ./deploy.py -y updateworker
  ./deploy.py -y kubernetes labels
  ```
  If you are running a small cluster, and need to run workload on the Kubernete master node (this choice may affect cluster stability), please use:
  ```
  ./deploy.py -y kubernetes uncordon
  ```
  Works now will be scheduled on the master node. If you stop here, you will have a fully functional kubernete cluster. Thus, part of DL Workspace setup can be considered automatic procedure to setup a kubernete cluster. You don't need shared file system or database for kubernete cluster operation. 
  
5. [optional] Configure, setup [GlusterFS](../Storage/GlusterFS.md)

6. [Optional] Configure, setup [HDFS](../Storage/hdfs.md)

7. [Optional] Setup [Spark](../Storage/spark.md)

8. Mount shared file system, please note that CoreOS can only mount NFS, you cannot mount CIFS 
  
  ```
  ./deploy.py mount
  ```

9. Start webUI service. 
  
  ```
  ./deploy.py webui
  ./deploy.py docker build restfulapi
  ./deploy.py docker build webui
  ./deploy.py kubernetes start jobmanager
  ./deploy.py kubernetes start restfulapi
  ./deploy.py kubernetes start webportal
  ```
