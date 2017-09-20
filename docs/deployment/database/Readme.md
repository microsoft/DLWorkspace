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

Use 'az login' to login to your azure create. Create Azure resource group and azure database via:

```
./az_tools.py create
./az_tools.py genconfig 
```

3. Other database. 

It is possible to use other database provider, e.g., MySQL. Currently, database is used in WebUI (consumed via Entityframework .Net Core ) and restful API (comsumed via python). Both programming language support connection to other database, e.g., MySQL. We encourage contribution in this space. 





