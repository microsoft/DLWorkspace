# Deployment of DL workspace cluster: Advanced Topics. 

This document describes additional advanced access and features to the deployed DL workspace cluster. 

1. Access to DL workspace node. 

   The private SSH key used to access the cluster is generated and stored at src/ClusterBootstrap/deploy/sshkey/id_rsa. To access each individual DL workspace node, please use:
   
   ```
   ssh -i deploy/sshkey/id_rsa core@[IP_Address]
   ```

2. Access to kubelet command. 
   Please log in to the kubernetes master, and then use the kubectl. 
   ```
   ssh -i deploy/sshkey/id_rsa core@[IP_Address_Kubernetes_Master]
   ```
   You may then use all kubernetes command, e.g., 
   ```
   kubectl get nodes
   ```
   