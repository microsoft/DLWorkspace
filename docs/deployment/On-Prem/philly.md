# Deploy DL workspace cluster on a cluster that is already deployed with CoreOS (e.g., Philly)

This document describes the procedure to deploy DL workspace on a prior deployed CoreOS cluster (e.g., certain Philly deployment). This document is still evolving. Please contact the author for any question. Our latest deployment is more focused on Ubuntu, so this portion may be a bit outdated. 

1. [Create Configuration file](configuration/Readme.md)
   1. Please copy src/ClusterBootstrap/config_philly.yaml.template to src/ClusterBootstrap/config.yaml, and further fill in various 
   parameters in the config file. 
   2. Please specify the private key used to access the Philly cluster. 
      1. If the user already has access to the philly cluster, you can add 
      ```
      ssh_cert: ~/.ssh/id_rsa
      ```
      to the configuration file. 
      2. Otherwise, please add philly master private key to ssh_cert. 
   3. Please copy the cluster YAML file of the cluster to cluster.yaml
   4. We assume the following:
      1. All deployed machines have DNS service, and are accessible by their hostname. 
      2. NFS has already been setup on each node for shared data access. By default, the NFS folder is mounted at: /dlwsdata
   5. Execute the following commands in folder "./src/ClusterBootstrap/"

2. [Build deployment images] (Build.md).
  ```
  ./deploy.py -y build 
  ```

3. [Important] Verify Etcd/Master nodes and worker nodes to be deployed. 
  ```
  ./deploy.py display
  ```

4. Start master/etcd servers, and worker nodes. 
  ```
  ./deploy.py -y production
  ```
   

5. label nodes, so that DL workspace service can be deployed to the proper set of nodes. 
  ```
  deploy.py -y kubernetes labels
  ```
  
6. Start webUI service. 
   ```
   ./deploy.py -y kubernetes start webportal restfulapi jobmanager
   ```
