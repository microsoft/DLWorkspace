# Deploy DL workspace cluster on Azure. 

This document describes the procedure to deploy DL workspace cluster on Azure. We are still improving the deployment procedure on Azure. Please contact the authors if you have encounter deployment issue. 

1. Please [create Configuration file](Configuration.md) and build [the relevant deployment key](Build.md).
   You do not need to build either the ISO or PXE server, but still need to execute the build to generate the necessary certificates. 

2. Create Azure VM in the desired region with a Ubuntu image (Please use Ubuntu 16.04 LTS). 

  It is recommended that you use the new Azure Portal to create the VM. When creating the VM, please make sure that the SSH key generated in step 1 at src/ClusterBootstrap/deploy/sshkey is used as the SSH key for accoount core when creating the VM. 

3. Please open all network ports for the created VM. 

  This can be most easily achived by setting up a network security group that allow all inbound traffic, and then assign the VM to the network security group. For more information, please refer to [this](https://docs.microsoft.com/en-us/azure/virtual-machines/windows/nsg-quickstart-portal). 

  (When the DL Workspace stablize, we may create a list of the specific ports that needed to be opened). 

4. Add th DNS name of the created VM to a configuration file.  

  You may add the configuration to either config.yaml, or cluster.yaml, with the following entry:

  ```
  network:
    domain: cloudapp.net


  machines:
    <<machine1>>:
      role: infrastructure
    <<machine2>>:
      role: worker
  ```

5. Setup basic tools on the Ubuntu image. 


4. Copy cloud configuration file to each deployed Azure VM.
  ```
  cd src/ClusterBootstrap/deploy/cloud-config
  sftp [USER]@[Azure-VM-NAME]
  put *
  ```
  The procedure above will send 'cloud-config-etcd.yml', 'cloud-config-kubelet.yml', 'cloud-config-master.yml' to the Azure VM. 

5. SSH to Azure VM, run installation script. 
  ```
  ssh [USER]@[Azure-VM-NAME]
  sudo coreos-cloudinit -from-file [CONFIGURATION_FILE]
  ```
  Please use 'cloud-config-etcd.yml' for initialization of the etcd node. Please use 'cloud-config-master.yml' for initialization of the master node. Please use 'cloud-config-kubelet.yml' for initialization of each of the worker node. 

6. You may then proceed with the rest of the deployment procedure. Be sure to use '-public' flag unless you are running the program inside Azure. That is, you may use to deploy Etcd/master, deploy worker nodes, and connect to those nodes. 
  ```
  python deploy.py -y deploy -public
  python deploy.py -y updateworker -public 
  python deploy.py connect master -public
  ```

    
