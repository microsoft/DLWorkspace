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
    <<your_cluster_name>>:
      infra_node_num: 0
      worker_node_num: 0
  ```

  Use 'az login' to login to your azure create. Create Azure resource group and azure database via:

  ```
  ./az_tools.py create
  ./az_tools.py genconfig 
  ```

  After script is running, the deployed database credential can be found at cluster.yaml. The cluster.yaml also contains a set of credential that will be used to for Kubernete API server.

3. Configure SQL Azure database size. 

  If you are using SQL Azure, we recommend to use change the database DLWorkspaceCluster-xxxxx to S4. The most heavy use of the database is when the Web Portal is left open to see the execution status of a particular job. We use SQL database to store the job status information. SQL instance S0 can quickly max out during job query. 

  Please note that SQL Azure attaches a pricing tier per database. Only database DLWorkspaceCluster-xxxxx needs to be bumped to a high pricing tier. For most of usage case, the other database can be left at S0. 

  Investigating better way to organize data and reduce the load of database, or select a database implementation which gives better performance is on the work plan. 

4. Other database. 

  It is possible to use other database provider, e.g., MySQL. Currently, database is used in WebUI (consumed via Entityframework .Net Core ) and restful API (comsumed via python). Both programming language support connection to other database, e.g., MySQL. We encourage contribution in this space. 





