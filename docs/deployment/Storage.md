DLWorkspace supports variety of storage system, e.g. NFS, glusterFS or LusterFS. 

We consider the storage system as an independent system module. You can play around and test different type of file system. 

The basic guidelines of using storage system in DLWorkspace are described as follow:
  1. The file system should be able to be mounted on Linux system, natively or via a third-party client. 
  2. It is suggested to have a windows file share interface (e.g. samba) to access the file system. 
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
     
     In the case of work folder and storage folder are not located on the same file system. These sub-folders can be soft links to the actual mount point. 
     
  2. If NFS server is used as storage system, {{nfs-server}} can be set to the access point of your NFS server, and DLWorkspace will mount this NFS access point to all the nodes automatically.  Note: if you use other file system other than NFS, you need to mount your fs on {{storage-mount-path}} by your own method. 
  3. {{workFolderAccessPoint}} and {{dataFolderAccessPoint}} are the samba access point to work folder and data folder. These two items are only used by web portal. 
  
  
  
  
