# Deploy DL workspace cluster on Ubuntu. 

This document describes the procedure to deploy DL workspace cluster on a Ubuntu Cluster that is on a VLAN with a initial node that is used as a PXE-server for prime the cluster. 

1. [Run Once] Setup [development environment](../../DevEnvironment/Readme.md).  

2. [Configuration the cluster](../configuration/Readme.md), and determine important information of the cluster (e.g., cluster name, number of Etcd servers used). Please refer to [Backup/Restore](../Backup.md) on instruction to backup/restore cluster configuration. 

3. Configure and setup the [databased](../database/Readme.md) used in the cluster. 

4. Config shared file system to be used in the cluster, following instructions in [Storage](../Storage/Readme.md) and the [configuration](../Storage/configure.md).

5. Configure the information of the servers used in the cluster. Please write the following entries in config.yaml. 

  ```
  network:
    domain: <<current_domain>>
    container-network-iprange: "<<your_cluster_ip_range, in 10.109.x.x/24 format>>" 
  
  platform-scripts : ubuntu

  machines:
    <<machine1>>:
      role: infrastructure
    <<machine2>>:
      role: worker
    <<machine3>>:
      role: worker
    ....
  ```
  If you are building a high availability cluster, please include multiple infrastructure nodes. The number of infrastructure nodes should be odd, e.g., 1, 3, 5. 3 infrastructure nodes tolerate 1 failure. 5 infrastructure nodes tolerate 2 failures. 

6. Build Ubuntu PXE-server via:
  ```
  ./deploy.py -y build 
  ./deploy.py build pxe-ubuntu
  ```

7. Start Ubuntu PXE-server. You will need to point DHCP server to the Ubuntu PXE-server. 
  ```
  ./deploy.py docker run pxe-ubuntu
  ```
  Reboot each machine to be deployed. In each boot screen, select to install Ubuntu 16.04. 

8. After the machines is reimaged to Ubuntu, install sshkey. (optional: If you ignore step 2,3 and choose to use an existing ubuntu cluster, you may put root username and password to files: ./deploy/sshkey/rootuser and ./deploy/sshkey/rootpasswd. In this case, the root user should be able to run "sudo" without password.)
  ```
  ./deploy.py sshkey install
  ```

9. Setup basic tools on the Ubuntu image. 
  ```
  ./deploy.py runscriptonall ./scripts/prepare_ubuntu.sh
  ./deploy.py execonall sudo usermod -aG docker core
  ```

10. Partition hard drive, if necessary. Please refer to section [Partition](Repartition.md) for details. 

11. Setup kubernetes
  ```
  ./deploy.py -y deploy
  ./deploy.py -y updateworker
  ./deploy.py -y kubernetes labels
  ```
  If you are running a small cluster, and need to run workload on the Kubernete master node (this choice may affect cluster stability), please use:
  ```
  ./deploy.py -y kubernetes uncordon
  ```
  Works now will be scheduled on the master node. If you stop here, you will have a fully functional kubernete cluster. Thus, part of DL Workspace setup can be considered automatic procedure to setup a kubernete cluster. You don't need shared file system or database for kubernete cluster operation. 
  
12. [optional] Configure, setup and mount [GlusterFS](../Storage/GlusterFS.md)
13. [Optional] Configure, setup and mount [HDFS](../Storage/hdfs.md)
14. [Optional] Setup [Spark](../Storage/spark.md)

15. Mount shared file system
  ```
  ./deploy.py mount
  ```

16. Build and deploy jobmanager, restfulapi, and webportal. Mount storage.
  ```
  ./deploy.py webui
  ./deploy.py docker push restfulapi
  ./deploy.py docker push webui
  ./deploy.py kubernetes start jobmanager
  ./deploy.py kubernetes start restfulapi
  ./deploy.py kubernetes start webportal
  ```
