# Deploy DL workspace cluster on a cluster on an already deployed with CoreOS cluster

This document describes the procedure to deploy DL workspace on a prior deployed CoreOS cluster. This document is still evolving. Please contact the author for any question. Our latest deployment is more focused on Ubuntu, so this portion may be a bit outdated. 

1. [Configuration cluster](configuration/Readme.md)
   1. Please copy src/ClusterBootstrap/config_coreos.yaml.template to src/ClusterBootstrap/config.yaml, fill in the cluster name, number of etcd server, domain, and the machines involved in the deployment. 
   ```
   cluster_name : <<your_cluster_name>>
   etcd_node_num : 3
   network:
     domain: <<your_cluster_domain>>
     container-network-iprange: "<<your_cluster_ip_range, in 10.109.x.x/24 format>>" 

  machines:
    <<infrastructure_machine_1>>:
      role: infrastructure
    <<infrastructure_machine_2>>:
      role: infrastructure
    <<worker_machine>>:
      role: worker
   ```
   2. Configure and setup the [databased](../database/Readme.md) used in the cluster.
   3. Please edit cluster.yaml generated in the step above, and remove:
   ```
   deploydockerETCD: false
   platform-scripts: ubuntu
   ```   
   4. If the machine is imaged through the [PXEServer](PXEServer) process, you can skip this step. If the machine is imaged and provided to you, please fill in config.yaml the installation username:
   ```
   admin_username: jinli
   ```
   and put password in ./deploy/sshkey/rootpasswd. The run 
   ```
   ./deploy.py sshkey install
   ```
   After this step, you should be able to access the cluster via [Scripts](../Scripts/Readme.md). Please make sure that the user is in sudo and docker group.  
   
2. [Build deployment images] (Build.md).
  ```
  ./deploy.py -y build 
  ```

3. Start master/etcd servers, and worker nodes. 
  ```
  ./deploy.py -y production
  ```

4. label nodes, so that DL workspace service can be deployed to the proper set of nodes. 
  ```
  deploy.py -y kubernetes labels
  ```
  
5. Start webUI service. 
   ```
   ./deploy.py scriptblocks bldwebui
   ./deploy.py scriptblocks restartwebui
   ```
