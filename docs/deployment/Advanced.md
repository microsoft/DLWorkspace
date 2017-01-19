# Deployment of DL workspace cluster: Advanced Topics. 

This document describes additional advanced access and features to the deployed DL workspace cluster. 

1. Access to DL workspace node. 

   Please use:
   
   ```
   python ./deploy.py connect master|etcd|worker [number]
   ```
   to connect to a particular Kubernetes master, etcd or worker node. 

2. Access to kubelet command. 
   Please log in to the kubernetes master, you may use the kubectl to further administrate the cluster, e.g., 
   ```
   kubectl get nodes
   ```
   