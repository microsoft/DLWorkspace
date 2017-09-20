# Configuration of shared file system 

As with all other configurations, the shared file system is configured through its section in config.yaml. Please use the following section to specify a mounted shared file system. 

```
mountpoints:
  <<sharename>>:
    type: <<share_type>>
    server: <<share_server>>
    filesharename: <<fileshare_name>>
    mountpoints: ["mntpoint1","mntpoint2","mntpoint3"]
```

The configuration paramters are as follows:

* <<sharename>>: a name to identify the share, you can use any unique name. 
* <<share_type>>: should be either nfs, glusterfs, hdfs, local. This defines the type of the shared file system used. 
* <<fileshare_name>>: name in the shared file system to identify volume.
    * For NFS, this identifies the subfolder of the share. 
    * For glusterfs, this identifies the volume of the share. 
    * HDFS will ignore <<fileshare_name>>, as HDFS is always mounted at root. 
* mountpoints: configure how the shared file system will be consumed. 
    * For each mountpoint, say mntpoint1, a symbolic link will be created:
        * /dlwsdata/mntpoint1 -> /mntdlws/<<fileshare_name>>/mntpoint1
    Note that we always create a directory within the shared file system, and symbolic link the consumed directory, e.g., /dlwsdata/mntpoint1 to the directory within the shared file system. This mechanism ensures that if the shared file system goes away, the consumed directory will fail (thus the related job will fails). We prefer this behavior compared with a fail silent behavior, in which the file may be written in local file system, and incorrectly placed. 

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
