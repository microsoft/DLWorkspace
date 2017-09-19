# Backup and restore cluster configuration and operating keys. 

Please note that during deployment, certain generated files, e.g., __src/ClusterBootstrap/*.yaml__, __src/ClusterBootstrap/deploy/*__, contains administrator information of the cluster, and should be preserved. We highly recommend to run a backup operation after deployment so that you can have administrator access to the cluster. 

The backup/restore operation should be performed at the following folder.

  ```
  cd src/ClusterBootstrap
  ```
  
1. Backup configuration can be performed via:
  ```
  ./deploy.py backup [backup_file_prefix] [password]
  ```
  [backup_file_prefix] is the prefix of the backup configuration file. The generated backup_file will have suffix tar.gz if not encrypted, and suffix tar.gz.enc if encrpyted. Password is an optional encryption to protect the configuration file. Please send/store the generated backup_file in a safe place for safe keeping. 
  
2. Restore configuration can be done via: 
  ```
  ./deploy.py restore [backup_file] [password]
  ```
