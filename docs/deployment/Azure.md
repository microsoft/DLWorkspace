# Deploy DL workspace cluster on Azure. 

This document describes the procedure to deploy DL workspace cluster on Azure. We are still improving the deployment procedure on Azure, and the current process is not as automated as we hope. Please contact the authors if you have encounter deployment issue. 

1. Please [create Configuration file](Configuration.md) and build [a bootable image](Build.md).

2. Create Azure VM in the desired region with a customized CoreOS image, with a initial username and password or initial SSH key. Please note that once successfully deployed, you can use DLworkspace utility to directly connecte to the created Kubernetes cluster. The initial username/password/SSH key and Azure VM machine name are just used for the initial deployment. 

3. Copy cloud configuration file to each deployed Azure VM.
  ```
  cd src/ClusterBootstrap/deploy/cloud-config
  sftp [USER]@[Azure-VM-NAME]
  put *
  ```
  The procedure above will send 'cloud-config-etcd.yml', 'cloud-config-kubelet.yml', 'cloud-config-master.yml' to the Azure VM. 

4. SSH to Azure VM, run installation script. 
  ```
  ssh [USER]@[Azure-VM-NAME]
  sudo coreos-cloudinit -from-file [CONFIGURATION_FILE]
  ```
  Please use 'cloud-config-etcd.yml' for initialization of the etcd node. Please use 'cloud-config-master.yml' for initialization of the master node. Please use 'cloud-config-kubelet.yml' for initialization of each of the worker node. 

5. You may then proceed with the rest of the deployment procedure.