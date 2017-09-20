# Setup development environment of DL workspace cluster

You will need general knowledge of Linux administration to setup, admin and develop DL Workspace. You will need to setup DL workspace development environment. This can be done by in one of two ways. 

## Running install_prerequisites.sh command.

We assume that you are running in Ubuntu OS in x64 machine, and your account is in sudo group. You can run install_prerequisities.sh, the scripts will install all components (Docker, python, Azure CLI) needed by DL WOrkspace. 

The setup operation of DLWorkspace should be executed at directory:

  ```
  cd src/ClusterBootstrap
  ```
  
The 'src/ClusterBootstrap/deploy' folder contains important information to access the deployed DL workspace cluster (e.g., clusterID, access SSH key). Please do not remove the folder if you need to adminstrate your deployed cluster. 

## Use development docker (in Linux/Unix environment) and mapped in the repo

You may clone the repo, and then mapped the repo in the dev container:

  ```
  git clone https://github.com/microsoft/DLWorkspace
  docker run -ti -v DLWorkspace:/home/DLWorkspace jinl/dlworkspacedevdocker /bin/bash
  ```

Once the docker started, you can go to the folder
  ```
  cd /home/DLWorkspace/src/ClusterBootstrap
  ```
and perform the rest of the deployment work. Please note that you __can not__ use the option for Docker for Windows, as explained in [this](FAQ.md).

## Use development docker (in Linux/Unix, and Docker for Windows) and clone the repo in the docker

You may run the development docker as:

  ```
  docker run -ti jinl/dlworkspacedevdocker /bin/bash
  ```

On __Docker for Windows__, the development docker needs to be run as follows to access the docker daemon run on host windows. 

  ```
  docker run -v //var/run/docker.sock:/var/run/docker.sock -ti jinl/dlworkspacedevdocker /bin/bash
  ```

Once the docker started, you can go to the folder
  ```
  cd /home/
  git clone https://github.com/microsoft/DLWorkspace
  cd DLWorkspace/src/ClusterBootstrap
  ```
and perform the rest of the deployment work. Please note that in this option, all deployment configuration is stored in docker container. It is __highly recommended__ to run a [backup operation](../deployment/Backup.md) to preserve the deployment credential, so that you can have administrative access to the cluster. 

## Kubernete development. 

DL Workspace enhance Kubernetes with specific features on GPU affinity, so that the user can request GPUs that have fast GPU Direct connection. If you need to develop/enhance kubernetes, you need to setup an environment to develop kubernetes, with instruction [here](Kubernetes.md).