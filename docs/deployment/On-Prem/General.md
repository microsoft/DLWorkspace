# General Instruction on DL Workspace deployment. 

These are the general steps to deploy a DL Workspace cluster. 

1 [Run Once] Setup [development environment](../../DevEnvironment/Readme.md).  

* [Configuration the cluster](configuration/Readme.md), and determine important information of the cluster (e.g., cluster name, number of Etcd servers used). Please refer to [Backup/Restore](Backup.md) on instruction to backup/restore cluster configuration. 

* Config shared file system to be used in the cluster, following instructions in [Storage.md](../Storage/Readme.md) and the [configuration](../Storage/configure.md).

* [Build]: build credentials.
  ```
  python deploy.py -y build 
  ```

* Deploy base OS via USB, PXE server, on Azure or on a private Philly cluster. 
    1 If you would like to deploy a small cluster for testing, or your cluster doesn't have a VLan setup, we recommend the deployment procedure in [USB.md](USB.md). 
    * If you would like to deply a production procedure, we recommend to set up a VLan for your cluster, and use a PXE server. The precedure are described in [PXEServer.md](PXEServer.md). 
    * If you would like to deploy a cluster on Azure, please follow the procedure in [Azure.md](Azure.md)
    * If you are using a private CoreOS cluster, please follow the procedure in [philly.md](philly.md). 
    If we plan to install a small number of machines (say 1-2), you may use [ISO image](USB.md). For deploying any larger cluster, [PXE server](PXEServer.md) is highly recommended. 
  

* Start master and etcd servers. Please use '-public' option if you run command inside firewall, while the cluster is public (e.g., Azure, AWS).
    ```
    deploy.py -y deploy
    ```
  
* Start worker nodes. Please use '-public' option if you run command inside firewall, while the cluster is public (e.g., Azure, AWS).

    ```
    deploy.py -y updateworker
    ```

* **__Static IP:__** Static IP/DNS name are strongly recommended for master and Etcd server, especially if you desire High Availability (HA) operation. Please contact your IT department to setup static IP for the master and Etcd server. With static IP, the DL workspace can operate uninterruptedly. 

    Otherwise, each time master and Etcd server has been rebooted (the master and Etcd servers may obtain a new IP addresses), you will need to restart master, etcd and work nodes by repeating steps of 4 and 5. 
  
* Set hostname of the cluster. 
    ```
    deploy.py -y hostname set
    ```

* label nodes, so that DL workspace service can be deployed to the proper set of nodes. 
    ```
    deploy.py -y kubernetes labels
    ```

* [Build and mount shared file system](../Storage/Readme.md)
  
* Build and push docker images which are used by the cluster
    ```
    deploy.py docker push
    ```

* Start webUI service. 
     ```
     deploy.py webui
     deploy.py -y kubernetes start webportal
     deploy.py -y kubernetes start restfulapi
     deploy.py -y kubernetes start jobmanager
     ```

* If encounter problems, please check on [known issues](../knownissues/Readme.md).