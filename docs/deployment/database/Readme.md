# Database in DL Workspace

DL Workspace uses a SQL server or SQL Azure to store user information (uid, gid, whether the user is an admin), job templates, scheduled job information and job output. The options to configure the database is as follows. 

1. Setup your own SQL server or SQL Azure. 

Please fill in the config.yaml with the following information. 

```
sqlserver-hostname : tcp:<<dns_name_of_server>>
sqlserver-username : <<sql_user_name>>
sqlserver-password : <<sql_password>>
sqlserver-database : DLWorkspaceJobs
```

2. Use automatic setup script to setup SQL Azure. 

If you are using [Azure Cluster](../Azure/Readme.md) or [ACS](../ACS/Readme.md) setup, the SQL Azure will be automatically setup through part of the process. You can use this process to setup a SQL Azure for a on-prem cluster, as follows. 

Add the following section to config.yaml. 

```
azure_cluster:
  infra_node_num: 0
  worker_node_num: 0

```




The easist way to setup SQL Azure for DL Workspace usage is to follow the operation in Azure cluster deployment, but specify the number of infrastructure node and worker node to be 0. Pleaes 





