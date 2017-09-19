# Deploy DL workspace cluster on Ubuntu. 

This document describes the procedure to deploy DL workspace cluster on a Ubuntu Cluster that is on a VLAN with a initial node that is used as a PXE-server for prime the cluster. 

1. Please [create Configuration file](configuration/Readme.md) and build [the relevant deployment key](Build.md).
   Please copy config_azure.yaml.template to config.yaml, and fill in the necessary information of the cluster.

  You may add the configuration to either config.yaml, or cluster.yaml, with the following entry:

  ```
  network:
    domain: <<current_domain>>
  
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


2. Build Ubuntu PXE-server via:
  ```
  .\deploy.py -y build 
  .\deploy.py build pxe-ubuntu
  ```

3. Start Ubuntu PXE-server. You will need DHCP server to properly point to Ubuntu PXE-server. 
  ```
  .\deploy.py docker run pxe-ubuntu
  ```
  Reboot each machine to be deployed. In each boot screen, select to install Ubuntu 16.04. 

4. After the machines is reimaged to Ubuntu, install sshkey. (optional: If you ignore step 2,3 and choose to use an existing ubuntu cluster, you may put root username and password to files: ./deploy/sshkey/rootuser and ./deploy/sshkey/rootpasswd. In this case, the root user should be able to run "sudo" without password.)
  ```
  .\deploy.py sshkey install
  ```

5. Setup basic tools on the Ubuntu image. 
  ```
  ./deploy.py runscriptonall ./scripts/prepare_ubuntu.sh
  ./deploy.py execonall sudo usermod -aG docker core
  ```

6. Partition hard drive, if necessary. Please refer to section [Partition](Repartition.md) for details. 

7. Setup kubernetes
  ```
  ./deploy.py -y deploy
  ./deploy.py -y updateworker
  ./deploy.py -y kubernetes labels
  ```
  If you are running a small cluster, and need to run workload on the Kubernete master node (this choice may affect cluster stability), please use:
  ```
  ./deploy.py -y kubernetes uncordon
  ```
  Works now will be scheduled on the master node. 
  
8. [optional] Configure [GlusterFS](GlusterFS.md)

9. [Optional] Configure [HDFS](hdfs.md)

10. Mount appropriate network drive. 
  ```
  ./deploy.py mount
  ```

11. Build and deploy jobmanager, restfulapi, and webportal. Mount storage.
  ```
  ./deploy.py docker push restfulapi
  ./deploy.py docker push webui
  ./deploy.py webui
  ./deploy.py kubernetes start jobmanager
  ./deploy.py kubernetes start restfulapi
  ./deploy.py kubernetes start webportal
  ```




