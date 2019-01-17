# Steps to deploy DL workspace cluster for a off-prem cluster Ubuntu. 

This document describes the procedure to deploy DL workspace cluster on a off-prem Clusters (VM or actual machine) that is already been imaged with Ubuntu OS.

1. On dev node (for simple cluster, the storage node can be used as dev node), 
* Enable password-less sudo, with ```sudo visudo```
* Generate ssh-key, and grant github access for the dev machine.
* Install git, if not installed yet.
* Find data partition, if any, use mkfs ext4 to make partition, and to prepare the partition for mount in fstab.
* use ```sudo mount -a``` to remount.
* check DNS setting, check if network is working. If shows TLS error message, network may not be stable. 

2. [Run Once] Setup [development environment](../../DevEnvironment/Readme.md).  

3. [Configuration the cluster](../configuration/Readme.md), and determine important information of the cluster (e.g., cluster name, number of Etcd servers used). Please refer to [Backup/Restore](../Backup.md) on instruction to backup/restore cluster configuration. 

4. Configure and setup the [databased](../database/Readme.md) used in the cluster. 

5. Config shared file system to be used in the cluster, following instructions in [Storage](../Storage/Readme.md) and the [configuration](../Storage/nfs.md).

6. Install sshkey to all nodes.
..* in config.yaml, insert entry of the admin_username of cluster 
    admin_username: <admin_user_name> 
..* insert admin password to 
    ./deploy/sshkey/rootpasswd
..* install sshkey via:
    ./deploy.py sshkey install

7. Configure the information of the servers used in the cluster. Please write the following entries in config.yaml. 

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

8. Build Ubuntu PXE-server via:
  ```
  ./deploy.py -y build 
  ./deploy.py build pxe-ubuntu
  ```

9. Start Ubuntu PXE-server. You will need to point DHCP server to the Ubuntu PXE-server. 
  ```
  ./deploy.py docker run pxe-ubuntu
  ```
  Reboot each machine to be deployed. In each boot screen, select to install Ubuntu 16.04. 

10. After the machines is reimaged to Ubuntu, install sshkey. (optional: If you ignore step 2,3 and choose to use an existing ubuntu cluster, you may put root username and password to files: ./deploy/sshkey/rootuser and ./deploy/sshkey/rootpasswd. In this case, the root user should be able to run "sudo" without password.)
  ```
  ./deploy.py sshkey install
  ```

11. Enable password less sudo priviledge, by adding following entry to `sudo visudo`
  ```
  <username> ALL=(ALL) NOPASSWD:ALL
  ```
  Please verify if password less sudo works on the remote machine. e.g., via,
  ```
  ./deploy.py execonall sudo ls -al
  ```
  
12. If apt-get gives a crash error, the issue is caused by:
  https://askubuntu.com/questions/942895/e-problem-executing-scripts-aptupdatepost-invoke-success
  ```
  ./deploy.py execonall sudo apt-get remove libappstream3
  ```


12. Setup basic tools on the Ubuntu image. 
  ```
  ./deploy.py runscriptonall ./scripts/prepare_ubuntu.sh
  ./deploy.py execonall sudo usermod -aG docker core
  ```
  Use nvidia-docker as default docker run time (included in kubelet startup)

13. Partition hard drive, if necessary. Please refer to section [Partition](Repartiuion.md) for details. 

14. Setup kubernetes
  If setup in the cluster in China, we tried to use dlws/pause-amd64:3.0 as --pod-infra-container-image, however, for some reason, this doesn't work. Temporary, please do:
  ```
  ./deploy.py execonall docker pull dlws/pause-amd64:3.0
  ./deploy.py execonall docker tag  dlws/pause-amd64:3.0 gcr.io/google_containers/pause-amd64:3.0
  ```
  On cloud (e.g., Azure), please make sure that the port specified in params.py, dev_network, udp_port_ranges and tcp_port_range are properly opened.
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

  Please note that the current kubernetes deployment use certificate to bind to the hostname deployed. If you change the hostname of the kubernete master node, the cluster needs to be redeployed.
  
15. [optional] Configure, setup and mount [GlusterFS](../Storage/GlusterFS.md)
16. [Optional] Configure, setup and mount [HDFS](../Storage/hdfs.md)
17. [Optional] Setup [Spark](../Storage/spark.md)

18. Mount shared file system
  ```
  ./deploy.py mount
  ```
19. Deploy nvidia-device plugin. 
  ```
  ./deploy.py kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v1.9/nvidia-device-plugin.yml
  ```

20. If the machines is put on a subdomain without the DNS search being able to resolv the subdomain (e.g., when deploying on aliyun, using an external DNS mapping), please at the master node:

* Modify /etc/resolvconf/resolv.conf.d/base, add entry "search <subdomain>"
* run 
```
sudo resolvconf -u 
```

20. Build and deploy jobmanager, restfulapi, and webportal. Mount storage.
  ```
  ./deploy.py webui
  ./deploy.py docker push restfulapi
  ./deploy.py docker push webui
  ./deploy.py nginx fqdn
  ./deploy.py nginx config
  ./deploy.py kubernetes start mysql jobmanager restfulapi webportal monitor nginx custommetrics
  ```
