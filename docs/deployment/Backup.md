# Backup and restore cluster configuration and operating keys. 

The backup/restore operation should be performed at the following folder.

  ```
  cd src/ClusterBootstrap
  ```
  
0. Backup configuration can be performed via:
  ```
  ./deploy.py backup [backup_file_prefix] [password]
  ```
  [backup_file_prefix] is the prefix of the backup configuration file (suffix .tar.gz.enc). Password is an optional encryption to protect the configuration file. 
  
1. Restore configuration can be done via: 
  ```
  ./deploy.py restore [backup_file] [password]
  ```
