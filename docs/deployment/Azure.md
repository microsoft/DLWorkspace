# Deploy DL workspace cluster on Azure. 

This document describes the procedure to deploy DL workspace cluster on Azure. We are still improving the deployment procedure on Azure. Please contact the authors if you have encounter deployment issue. 

1. Please [create Configuration file](Configuration.md) and build [the relevant deployment key](Build.md).
   You do not need to build either the ISO or PXE server, but still need to execute the build to generate the necessary certificates. 

2. Create Azure VM in the desired region with a Ubuntu image. 

  Please create a network security group that allow all inbound traffic, and then assign the VM to the network security group. For more information, please refer to [this]. (When the DL Workspace stablize, we may create a list of the specific ports that needed to be opened). 

  It is highly recommended that you create the VM following the exact options below:

  * Use the new Auzre Portal to create VM. 
  * Image: Ubuntu 16.04 LTS
  * Use Resource Manager 
  * Click Public IP, and select "Static IP". 
  * Assign the VM to the Security Group created above. 

  The key operation is to make sure that all ports on the VMs are assessible publicly. 

3. Add th DNS name of the created VM to a configuration file.  

  You may add the configuration to either config.yaml, or cluster.yaml, with the following entry:

  ```
  network:
    domain: westus.cloudapp.azure.com
  
  platform-scripts : ubuntu

  machines:
    <<machine1>>:
      role: infrastructure
    <<machine2>>:
      role: worker
  ```

4. Setup basic tools on the Ubuntu image. 
  ```
  ./deploy.py runscriptonall ./scripts/prepare_ubuntu.sh
  ./deploy.py execonall sudo usermod -aG docker core
  ```

5. Deploy etcd/master and workers. 
  ```
  ./deploy.py -y deploy
  ./deploy.py -y updateworker
  ```

6. Label nodels and deploy services:
  ```
  ./deploy.py -y kubernetes labels
  ./deploy.py -y updateworker
  ```

