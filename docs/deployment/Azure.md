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
  * Create the VM. 
  * After the public IP is available, assign a DNS name to the VM, this DNS name is needed in the configuration file below.

  The key operation is to make sure that all ports on the VMs are assessible publicly. 

  We assume that the Azure VM is deployed at westUs region. If you plan to deploy the VM to other Azure regions, please contact the authors. We use Azure App with region authentication, and currently, the App is only authorized in certain specific Azure regions. 

3. Creaet a Azure File Share. Please note that you need a ** Classic ** storage account at Azure, and [A sample instruction is here.] (https://docs.microsoft.com/en-us/azure/storage/storage-dotnet-how-to-use-files)

4. Add the DNS name of the created VM to a configuration file.  

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

  mountpoints:
    rootshare:
      type: azurefileshare
      accountname: <<your azure storage account>>
      filesharename: <<your azure file sharename>>
      # Mount at root
      mountpoints: ""
      accesskey: <<your azure fileshare accesskey>>
  ```

5. Run Azure deployment script block:
  ```
  ./deploy.py --verbose scriptblocks azure 
  ```
  After the script completes execution, you may still need to wait for a few minutes so that relevant docker images can be pulled to the target machine for execution. You can then access your cluster at:
  ```
  http://machine1.westus.cloudapp.azure.com/
  ```
  where machine1 is your azure infrastructure node. 

  The script block execute the following command in sequences:
  1. Setup basic tools on the Ubuntu image. 
  ```
  ./deploy.py runscriptonall ./scripts/prepare_ubuntu.sh
  ./deploy.py execonall sudo usermod -aG docker core
  ```

  2. Deploy etcd/master and workers. 
  ```
  ./deploy.py -y deploy
  ./deploy.py -y updateworker
  ```

  3. Label nodels and deploy services:
  ```
  ./deploy.py -y kubernetes labels
  ./deploy.py -y updateworker
  ```

  4. Build and deploy jobmanager, restfulapi, and webportal. 
  ```
  ./deploy.py docker push restfulapi
  ./deploy.py docker push webui
  ./deploy.py webui
  ./deploy.py kubernetes start jobmanager
  ./deploy.py kubernetes start restfulapi
  ./deploy.py kubernetes start webportal
  ```


