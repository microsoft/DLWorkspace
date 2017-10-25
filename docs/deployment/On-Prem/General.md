# General Instruction on DL Workspace deployment. 

These are the general steps to deploy a DL Workspace cluster. 

1. [Run Once] Setup [development environment](../../DevEnvironment/Readme.md).  

2. [Configuration the cluster](../configuration/Readme.md), and determine important information of the cluster (e.g., cluster name, number of Etcd servers used). Please refer to [Backup/Restore](../Backup.md) on instruction to backup/restore cluster configuration. 

3. Configure and setup the [databased](../database/Readme.md) used in the cluster. 

4. Config shared file system to be used in the cluster, following instructions in [Storage.md](../Storage/Readme.md) and the [configuration](../Storage/configure.md).

5. [Build]: build credentials.
  ```
  python deploy.py -y build 
  ```

6. Deploy base OS via USB, PXE server, on Azure or on a private Philly cluster. 
    1 If you would like to deploy a small cluster for testing, or your cluster doesn't have a VLan setup, we recommend the deployment procedure in [USB.md](USB.md). 
    * If you would like to deply a production procedure, we recommend to set up a VLan for your cluster, and use a PXE server. The precedure are described in [PXEServer.md](PXEServer.md). 
    * If you would like to deploy a cluster on Azure, please follow the procedure in [Azure](../Azure/Readme.md)
    * If you are using a private CoreOS cluster, please follow the procedure in [CoreOS](CoreOS.md). 
    If we plan to install a small number of machines (say 1-2), you may use [ISO image](USB.md). For deploying any larger cluster, [PXE server](PXEServer.md) is highly recommended. 
  

7. Start master and etcd servers. Please use '-public' option if you run command inside firewall, while the cluster is public (e.g., Azure, AWS).
    ```
    deploy.py -y deploy
    ```
  
8. Start worker nodes. Please use '-public' option if you run command inside firewall, while the cluster is public (e.g., Azure, AWS).

    ```
    deploy.py -y updateworker
    ```
    If you stop here, you will have a fully functional kubernete cluster. Thus, part of DL Workspace setup can be considered automatic procedure to setup a kubernete cluster. You don't need shared file system or database for kubernete cluster operation. 

9. **__Static IP:__** Static IP/DNS name are strongly recommended for master and Etcd server, especially if you desire High Availability (HA) operation. Please contact your IT department to setup static IP for the master and Etcd server. With static IP, the DL workspace can operate uninterruptedly. 

    Otherwise, each time master and Etcd server has been rebooted (the master and Etcd servers may obtain a new IP addresses), you will need to restart master, etcd and work nodes by repeating steps of 4 and 5. 
  
10. Set hostname of the cluster. 
    ```
    deploy.py -y hostname set
    ```

11. label nodes, so that DL workspace service can be deployed to the proper set of nodes. 
    ```
    deploy.py -y kubernetes labels
    ```

12. [Build and mount shared file system](../Storage/Readme.md)
  
14. Build and push docker images which are used by the cluster, start webUI service. 
     ```
     deploy.py webui
     deploy.py docker push restfulapi
     deploy.py docker push webui
     deploy.py -y kubernetes start webportal
     deploy.py -y kubernetes start restfulapi
     deploy.py -y kubernetes start jobmanager
     ```

15. If encounter problems, please check on [known issues](../knownissues/Readme.md).