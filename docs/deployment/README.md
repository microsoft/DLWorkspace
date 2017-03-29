# Deployment of DL workspace cluster

DL workspace allows you to setup a cluster that you can run deep learning training job, interactive exploration job, and evaluation service. Please refer to docs/WhitePaper/ for more information. 

DL workspace cluster can be deployed in two forms: 1) [compact deployment](CompactDeployment.md) (target small cluster, as few as 1 machine), and 2) [large production deployment](LargeProductionDeployment.md). 

The document in this section describes the procedure to deploy a DL workspace cluster, as follows. You may want to change directory to the follows to perform the operations below.

  ```
  cd src/ClusterBootstrap
  ```
  
The 'deploy' folder contains important information to access the deployed DL workspace cluster (e.g., clusterID, access SSH key). Please do not remove the folder if you need to adminstrate your deployed cluster. 

0. [Run Once] The installation program needs certain utilities (such as docker and python). The simplest setup is to use the [development docker](../../DevDocker.md) and run the subsequent command in the development docker. Alternatively, you may choose to run install_prerequisites.sh once to install  utilities.  

1. [Create Configuration file](Configuration.md), and determine important information of the cluster (e.g., cluster name, number of Etcd servers used). Please refer to [Backup/Restore](Backup.md) on instruction to backup/restore cluster configuration. 

2. [Build deployment images] (Build.md): ISO (for USB deployment) and docker image (for PXE deployment).
  ```
  python deploy.py -y build 
  ```

3. Deploy base CoreOS image via USB, PXE server, on Azure or on a private Philly cluster. 
  1. If you would like to deploy a small cluster for testing, or your cluster doesn't have a VLan setup, we recommend the deployment procedure in [USB.md](USB.md). 

  2. If you would like to deply a production procedure, we recommend to set up a VLan for your cluster, and use a PXE server. The precedure are described in [PXEServer.md](PXEServer.md). 
  3. If you would like to deploy a cluster on Azure, please follow the procedure in [Azure.md](Azure.md)
  4. If you are using a private philly cluster, please follow the procedure in [philly.md](philly.md). 
  
4. Start master and etcd servers. Please use '-public' option if you run command inside firewall, while the cluster is public (e.g., Azure, AWS).

  ```
  deploy.py -y deploy
  ```
  
5. Start worker nodes. Please use '-public' option if you run command inside firewall, while the cluster is public (e.g., Azure, AWS).

  ```
  deploy.py -y updateworker
  ```

6. **__Static IP:__** Static IP/DNS name are strongly recommended for master and Etcd server, especially if you desire High Availability (HA) operation. Please contact your IT department to setup static IP for the master and Etcd server. With static IP, the DL workspace can operate uninterruptedly. 

  Otherwise, each time master and Etcd server has been rebooted (the master and Etcd servers may obtain a new IP addresses), you will need to restart master, etcd and work nodes by repeating steps of 4 and 5. 
  
7. Set hostname of the cluster. 
  ```
  deploy.py -y hostname set
  ```

8. label nodes, so that DL workspace service can be deployed to the proper set of nodes. 
  ```
  deploy.py -y kubernetes labels
  ```
  
9. Start webUI service. 
   ```
   deploy.py -y kubernetes start webportal
   deploy.py -y kubernetes start restfulapi
   deploy.py -y kubernetes start jobmanager
   ```

10. Certain advanced topics, e.g., access to each deployed DL workspace node, use kubelet command, can be found at [Advanced.md](Advanced.md).

11. If encounter problems, please check on [known issues](KnownIssues.md).
