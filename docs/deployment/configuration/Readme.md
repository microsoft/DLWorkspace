# Configure DL workspace cluster

This document describes the procedure to write a configuration file for your DL workspace cluster. 

DL Workspace configuration is stored in JSON format. It is a combination of : 1) default configuration in code (deploy.py), 2) user configuration (in config.yaml at src/ClusterBootstrap) and 3) derivative configuration (e.g., cluster.yaml). In execution, any configuration in 1) will be overwritten by 2), 
which is further override by 3). 

config.yaml is written in [yaml format](https://en.wikipedia.org/wiki/YAML). You can use any of your favorite text editor to generate the file. 

At a minimum, each DL Workspace cluster should have a unique cluster_name, specified at config.yaml. 

1. {{cluster_name}}: replace it with the your DL workspace cluster name, e.g., ccs1

Depending on the cluster that you will deploy, and whether you enable certain function (e.g., authentication, HDFS/spark), you will need to add additional section to config.yaml. 

config.yaml can be [backup](../Backup.md) or [restored](../Backup.md). 