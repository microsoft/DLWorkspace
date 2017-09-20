# Deployment of DL workspace cluster.

DL workspace is an open source toolkit that allows you to setup a cluster that can run deep learning training job, interactive exploration job, and evaluation service. The cluster also support big data analytic toolkit such as Hadoop/Spark. 

DL Workspace is still in pre-release alpha stage. If you encounter issues in either deployment and/or usage, please open an issue at [Github](https://github.com/microsoft/DLWorkspace), or contact the DL Workspace team. 

# Development environment.

Please setup the dev environment of DL workspace as [this](../DevEnvironment/Readme.md). 

# Detailed Step-by-step setup insturction for a selected set of clusters. 

DL workspace cluster can be deployed in two forms: 1) [compact deployment](CompactDeployment.md) (target small cluster, as few as 1 machine), and 2) [large production deployment](LargeProductionDeployment.md). The detail deployment procedure depends on the cluster. Here are some specific setup instruction for a selected set of clusters 

## [Azure Container Service](ACS/Readme.md)
## [Azure Cluster](Azure/Readme.md)
## [On-Prem](Ubuntu.md)

Additional information on general deployment can be found at [here](General.md).






