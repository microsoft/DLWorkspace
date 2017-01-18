# Deployment of DL workspace cluster

DL workspace allows you to setup a cluster that you can run deep learning training job, interactive exploration job, and evaluation service. Please refer to docs/WhitePaper/ for more information. 

The document in this section describes the procedure to deploy a DL workspace cluster, as follows.

1. [Create Configuration file](Configuration.md), and determine important information of the cluster (e.g., cluster name, number of Etcd servers used).

2. [Build deployment images] (Build.md): ISO (for USB deployment) and docker image (for PXE deployment).

3. Deploy via USB or PXE server. 
  1. If you would like to deploy a small cluster for testing, or your cluster doesn't have a VLan setup, we recommend the deployment procedure in [USB.md](USB.md). 

  2. If you would like to deply a production procedure, we recommend to set up a VLan for your cluster, and use a PXE server. The precedure are described in [PXEServer.md](PXEServer.md). We are still fine tuning the setup procedure for this route. If you are interested, please contacted the DL workspace team and we will be happy to work with you. 

4. Certain advanced topics, e.g., access to each deployed DL workspace node, can be found at [Advanced.md](Advanced.md).
