# Deployment of DL workspace cluster

DL workspace allows you to setup a cluster that you can run deep learning training job, interactive exploration job, and evaluation service. Please refer to docs/WhitePaper/ for more information. 

The document in this section describes the procedure to deploy a DL workspace cluster, as follows. You may want to change directory to the follows to perform the operations below.

  ```
  cd src/ClusterBootstrap
  ```

1. [Create Configuration file](Configuration.md), and determine important information of the cluster (e.g., cluster name, number of Etcd servers used).

2. [Build deployment images] (Build.md): ISO (for USB deployment) and docker image (for PXE deployment).
  ```
  python ./deploy.py build
  ```

3. Deploy base CoreOS image via USB or PXE server. 
  1. If you would like to deploy a small cluster for testing, or your cluster doesn't have a VLan setup, we recommend the deployment procedure in [USB.md](USB.md). 

  2. If you would like to deply a production procedure, we recommend to set up a VLan for your cluster, and use a PXE server. The precedure are described in [PXEServer.md](PXEServer.md). 

4. Start master and etcd servers. 

  ```
  python ./deploy.py deploy
  ```
  
5. Start worker nodes.

  ```
  python ./deploy.py updateworker
  ```

6. **__Static IP__** Static IP/DNS name are strongly recommended for master and Etcd server, especially if you desire High Availability (HA) operation. Please contact your IT department to setup static IP for the master and Etcd server. With static IP, the DL workspace can operate uninterruptedly. 

  Otherwise, each time master and Etcd server has been rebooted (the master and Etcd servers may obtain a new IP addresses), you will need to restart master, etcd and work nodes by repeating steps of 4 and 5. 

7. Certain advanced topics, e.g., access to each deployed DL workspace node, use kubelet command, can be found at [Advanced.md](Advanced.md).
