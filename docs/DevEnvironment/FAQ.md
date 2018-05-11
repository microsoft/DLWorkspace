# Frequently Asked Questions (FAQ) for DL Worspace, Development Environment.  

Please refer to [this](../knownissues/Readme.md) for more general issues. 

## I use Docker for Windows, and I mapped my git repo into the DL Workspace development docker. The deployment fails with message 

```
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@         WARNING: UNPROTECTED PRIVATE KEY FILE!          @
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
Permissions 0755 for './deploy/sshkey/id_rsa' are too open.
It is required that your private key files are NOT accessible by others.
This private key will be ignored.
Load key "./deploy/sshkey/id_rsa": bad permissions
Permission denied (publickey).
```

In the deployment stage, DL Workspace uses ssh to perform certain remote operations to setup remote machines. In the beginning of the setup stage, a set of SSH key is generated, which are then used in later setup stage. In certain docker version (e.g., Docker for Windows), 'id_rsa' file created by ssh-keygen is of mode '0755'. Moreover, the permission cannot be changed by 'chmod' command. SSH refuses the consumption of such private key, and causes the script to fails. 

At the moment, the solution is to **not working on mapped folder** in Docker for Windows. That is, in Docker for Windows, you will need to copy/clone a repo in the docker, not to map the repo from Windows inside docker. Please note that during deployment, certain generated files, e.g., __src/ClusterBootstrap/*.yaml__, __src/ClusterBootstrap/deploy/*__, contains administrator information of the cluster, and should be preserved. In Docker for Windows, once the container terminates, those files will be gone, and you may lost administrative access to your cluster. It is highly recommended to run a [backup operation](../deployment/Backup.md) after deployment. 

## I use Docker for Windows, and I failed to build the docker image for webui and restfulapi. 

  For Docker for Windows, make sure that you run __follows__ to access the docker daemon on host. 

  ```
  docker run -v //var/run/docker.sock:/var/run/docker.sock -ti jinl/dlworkspacedevdocker /bin/bash
  ```
