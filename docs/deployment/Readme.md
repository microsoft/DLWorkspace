# Deployment of DL workspace cluster.

DL workspace is an open source toolkit that allows you to setup a cluster that can run deep learning training job, interactive exploration job, and evaluation service. The cluster also support big data analytic toolkit such as Hadoop/Spark. 

DL Workspace is still in pre-release alpha stage. If you encounter issues in either deployment and/or usage, please open an issue at [Github](https://github.com/microsoft/DLWorkspace), or contact the DL Workspace team. 

# Development environment.

Please setup the dev environment of DL workspace as [this](../DevEnvironment/Readme.md). 

# Detailed Step-by-step setup insturction for a selected set of clusters. 

DL workspace cluster can be deployed to either public cloud (e.g., Azure), or to on-prem cluster. The deployment to public cloud is more straightforward, as the environment is more uniform. The deployment instruction are as follows:

## [Azure Container Service](ACS/Readme.md)
## [Azure Cluster](Azure/Readme.md)
## [Azure Deployment using Azure Resource Management (ARM) templates](../../src/ARM/README.md)

We give instruction on the deployment of DL Workspace to an on-prem cluster as well. Please note that because each on-prem cluster is different in hardware (and maybe software) configuration, the deployment procedure is more tricky. The basic deployment step is as follows. 

## [On-Prem, Ubuntu](On-Prem/Ubuntu.md)
## [On-Prem, CoreOS](On-Prem/CoreOS.md)
## [On-Prem, Ubuntu, Single Node](On-Prem/SingleUbuntu.md)

Additional information on general deployment can be found at [here](On-Prem/General.md).






