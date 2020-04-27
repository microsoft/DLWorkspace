# Configuration of shared file system 

As with all other configurations, the shared file system is configured through its section in config.yaml. Please use the following section to specify a mounted shared file system. 

```
mountpoints:
  <<sharename>>:
    publicshare: ["publicshare1", "publicshare2", "publicshare3" ]
    type: <<share_type>>
    server: <<share_server>>
    filesharename: <<fileshare_name>>
    mountpoints: ["mntpoint1","mntpoint2","mntpoint3"]
    
deploymounts: ["mntpoint1", "mntpoint2", "mntpoint3" ]
```

The configuration paramters are as follows:

* <<sharename>>: a name to identify the share, you can use any unique name. 
* <<share_type>>: should be either nfs, glusterfs, hdfs, local, localHDD, emptyDir. This defines the type of the shared file system used. 
* server: name of the server 
  For HDFS, if the HDFS cluster is the same as the deployed cluster, no server should be specified. 
  Otherwsie, specify: hdfs://{HDFS_Cluster}
* <<fileshare_name>>: name in the shared file system to identify volume.
    * For NFS, this identifies the subfolder of the share. 
    * For glusterfs, this identifies the volume of the share. 
    * HDFS will ignore <<fileshare_name>>, as HDFS is always mounted at root. 
* publicshare: normally, each user can only access the shared file system through <<fileshare_name>>/<<username>>, so each user has access to his/her own share. The public share <<fileshare_name>>/<<publicshare>>, however, can be mounted by any user, and thus be used to share data between group members. 
* emptyDir: If this option is turned on, the shared volume <<fileshare_name>>/<<username>> will be mounted as an [emptyDir](https://kubernetes.io/docs/concepts/storage/volumes/) in container. Its content will be deleted when job terminates. 

* mountpoints: configure how the shared file system will be consumed. 
    * For each mountpoint, say mntpoint1, a symbolic link will be created:
        * /dlwsdata/mntpoint1 -> /mntdlws/<<fileshare_name>>/mntpoint1
    Note that we always create a directory within the shared file system, and symbolic link the consumed directory, e.g., /dlwsdata/mntpoint1 to the directory within the shared file system. This mechanism ensures that if the shared file system goes away, the consumed directory will fail (thus the related job will fails). We prefer this behavior compared with a fail silent behavior, in which the file may be written in local file system, and incorrectly placed. 

* deploymounts: These mounts will be offered as a option to be mounted into the container. Please note that if a certain mount fails, the container will fails to launch. 

Unless DL Workspace is deployed to a single node, it should always use a shared file system. At the minimum, the folder "jobfiles", "namenodeshare", "storage", "work" need to be placed on the shared file system. This facilitates the job execution and monitoring. For DL Workspace, if a particular share has an empty mountpoints:

```
mountpoints:
  <<sharename>>:
    type: <<share_type>>
    server: <<share_server>>
    filesharename: <<fileshare_name>>
    mountpoints: ""
```

It means that this shared file system is the master share, and all job critical folders, i.e., "jobfiles", "namenodeshare", "storage", "work", will be placed under this share. That is, mountpoints of value "" is equal to set the mount points as [] "jobfiles", "namenodeshare", "storage", "work" ].
