# Deploy DL workspace cluster on Ubuntu. 

This document describes the procedure to deploy DL workspace cluster on a single Ubuntu node. The target deployment node can be either your local machine, or a remote node. 

1. [Run Once] Setup [development environment](../../DevEnvironment/Readme.md).  

2. Please make sure that the deployment node satisfy the following:
   * We assume that it is Ubuntu OS, preferably 16.04
   * It has a "core" account that you can [ssh into](https://www.ssh.com/ssh/copy-id)
   * The "core" account can [sudo](https://linuxconfig.org/sudo-install-usage-and-sudoers-config-file-basics) to gain root priviledge. Please follow the instruction to setup sudo without password. 
   * Please turn of apache2 server if it is running:
   ```
   sudo systemctl disable apache2
   ```
   DL workspace runs WebUI on port 80, which conflicts with apache2.

3. [Configuration the cluster](../configuration/Readme.md). You will need the following as a minimum. 

   * cluster_name
   * An existing SQL or Azure SQL database, or you can create one using [scripts](../database/Readme.md). Please note that Azure SQL charge may apply. 
   * [Authentication](../authentication/Readme.md)
   * Any shared file system. For single node, you can use a local drive for jobs. 

4. Configure the information of the servers used in the cluster. Please write the following entries in config.yaml. 

  ```
  ssh_cert: ~/.ssh/id_rsa {{ assuming that this is the SSH key that ssh into core account. }}

  machines:
    <<hostname_of_the_machine>>:
      role: infrastructure

  etcd_node_num: 1
  ```

  If use domain, please add:
  ```
  network:
    domain: <<domain_of_the_machine>>
  ```
  Please don't use domain: "", this adds a "." to hostname by the script, and causes the scripts to fail. 


5. Run deployment script block:
  ```
  ./deploy.py --verbose scriptblocks ubuntu_uncordon 
  ```

