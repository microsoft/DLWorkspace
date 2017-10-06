# Shared File System in DL Workspace. 

DLWorkspace supports variety of storage system, e.g. NFS, glusterFS or HDFS. If you want a distributed file system that hasn't been supported, you are welcome to contribute to DL Workspace and get it supported.

We consider the file system as an independent system module. You can play around and test different type of file system. In general, you will need to 
**partition data**, **setup** and **mount** file system for them to be used. 

## [Partition disk drive](Repartition.md)

## [Configure shared file system](configure.md) 

## Setup shared file system
  * Setup [Glusterfs](GlusterFS.md)
  * Setup [HDFS](hdfs.md)
  * Setup [Spark](spark.md)

## Mount shared file system

The following command mounted the shared file system in DL Workspace, and establish the necessaries symbolic link. 
  ```
  .\deploy.py mount
  ```

The basic guidelines of mounting shared file system in DLWorkspace are described as follow:
  1. The file system should be able to be mounted on Linux system, natively or via a third-party client. 
  2. If your users are using Windows Desktop, it is recommended that the used file system to have a windows file share interface (e.g. samba) to access the file system. This allows more smooth data transfer, and also use of certain command (e.g., ssh with shared key)/ 
  3. Please plan at least two logical partitions in the file system: one is used for data storage and the other one is used for users' home folder.
  
The following config options related to storage system:
  1. {{storage-mount-path}} : the you need to mount your file system to this point on each master node and work node. The default value is /dlwsdata.
     The structure of this folder must be:
     ```
     /dlwsdata
       |-- /dlwsdata/work
       |-- /dlwsdata/storage
       |-- /dlwsdata/jobfiles
     ```
     In most cases, the work folder and storage folder are soft links to the actual mount points. 
     
  2. If NFS server is used as storage system, {{nfs-server}} can be set to the access point of your NFS server, and DLWorkspace will mount this NFS access point to all the nodes automatically.  Note: if you use other file system other than NFS, you need to mount your fs on {{storage-mount-path}} by your own method. 

  3. {{workFolderAccessPoint}} and {{dataFolderAccessPoint}} are the samba access point to work folder and data folder. These two items are only used by web portal. It should be a folder that the user can access when running the web portal. E.g., if the user is using a windows desktop, {{workFolderAccessPoint}} and {{dataFolderAccessPoint}} should be the samba access point from users' desktop. 

As with other subsystems, the Shared File System in DL Workspace is setup and configured through config.yaml. Please follow the [configuration instruction](configure.md) 
