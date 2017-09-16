# Setup development environment of DL workspace cluster

You will need general knowledge of Linux administration for the task. To setup, admin and develop DL Workspace, you will need to setup DL workspace development environment. This can be done by in one of two ways. 

## Running install_prerequisites.sh command.

We assume that you are running in Ubuntu OS in x64 machine, and the account is in sudo group. Run install_prerequisities.sh.


The setup operation of DLWorkspace should be executed at directory:

  ```
  cd src/ClusterBootstrap
  ```
  
The 'deploy' folder contains important information to access the deployed DL workspace cluster (e.g., clusterID, access SSH key). Please do not remove the folder if you need to adminstrate your deployed cluster. 

# Kubernete development. 

DL Workspace enhance Kubernetes with specific features on GPU affinity, so that the user can request GPUs that have fast GPU Direct connection. If you need to develop/enhance kubernetes, you need to setup an environment to develop kubernetes, with instruction [here](Kubernetes.md).