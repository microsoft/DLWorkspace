# Deploy DL workspace cluster on a cluster that is already deployed with CoreOS (e.g., Philly)

This document describes the procedure to deploy DL workspace on a prior deployed CoreOS cluster (e.g., certain Philly deployment). This document is still evolving. Please contact the author for any question. 

1. [Create Configuration file](Configuration.md)
   1. Please copy config_philly.yaml.template to config.yaml, and further fill in various 
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

2. [Build deployment images] (Build.md).
  ```
  python deploy.py -y build 
  ```

3. [Important] Verify Etcd/Master nodes and worker nodes to be deployed. 
  ```
  deploy.py display
  ```

4. Start master and etcd servers. 
  ```
  deploy.py -y deploy
  ```
   
5. Start worker nodes. 
  ```
  deploy.py -y updateworker
  ```

6. Start webUI service. 
   ```
   deploy.py -y kubernetes start webportal
   deploy.py -y kubernetes start restfulapi
   deploy.py -y kubernetes start jobmanager
   ```
