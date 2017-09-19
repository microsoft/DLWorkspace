# Deployment of DL workspace on Philly 

Please follow the following setup to deploy DL workspace on philly. 

0. [Run Once] The installation program needs certain utilities (such as docker and python). The simplest setup is to use the [development docker](../../DevDocker.md) and run the subsequent command in the development docker. Alternatively, you may choose to run install_prerequisites.sh once to install  utilities.  

1. [Create Configuration file](../deployment/configuration/Readme.md), and determine important information of the cluster (e.g., cluster name, number of Etcd servers used). Please refer to [Backup/Restore](Backup.md) on instruction to backup/restore cluster configuration. 

2. [Build deployment images and various executables] (Build.md):
  ```
  python deploy.py -y build 
  ```

4. Start master and etcd servers. 

  ```
  deploy.py -y deploy
  ```
  
5. Start worker nodes. 

  ```
  deploy.py -y updateworker
  ```

6. Please uncordon master so that certain process can be execued on master nodes. 
  ```
  deploy.py -y uncordon
  ```

7. Label infrastructure and worker nodes according to the configuration file. 
  ```
  deploy.py kubectl labels 
  ```

8. Start/restart various services. 
  ```
  deploy.py kubectl start [service]
  or deploy.py kubectl restart [service]
  ```

9. Certain advanced topics, e.g., access to each deployed DL workspace node, use kubelet command, can be found at [Advanced.md](Advanced.md).

10. If encounter problems, please check on [known issues](KnownIssues.md).
