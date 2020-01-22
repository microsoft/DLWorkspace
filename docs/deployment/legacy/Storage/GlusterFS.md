# Deployment of GlusterFS on a kubernete cluster. 

The document describes the procedure to setup glusterFS across a cluster. GlusterFS needs to access block device on the cluster. For manipulation of block device, please refer to [Partition.md](Partition.md). 

1. Configure glusterFS on the cluster. 
  You will need to specify: 1) the nodes, 2) partition on nodes, and 3) volume to be created on glusterFS. 
  The configuration entry are as follws: 
  
  ```
  glusterFS:
    partitions: <<regular expression matching drives deploying glusterFS>>
    gluster_volumes: 
      default: 
        netvolume: 
          property: "replica 2" 
          tolerance: 1
          # number of bricks need to be a multiple of this
          multiple: 2    
  kubelabels:
    glusterfs: worker or <<glusterfs_labels>>
  mountpoints:
    rootshare:
      type: glusterfs
      filesharename: netvolume
      # Mount at root
      mountpoints: netvolume
  ```

  The glusterFS\partition controls what partition glusterFS are deployed upon. The kubelabels\glusterfs control what nodes glusterFS will be deployed upon. If you do not want to deploy glusterFS to all worker node, you could use "glusterfs_labels", and mark node to be deployed with glusterfs with the specific "glusterfs_labels". Please see [node labeling](Labels.md) for more information. 

  The mountpoints control the location on everynode that glusterfs will be mounted upon. 

2. Repartition(Repartition.md) some data drives on the cluster and use those partition for glusterFS. 

3. Format thin_pool volumes to be used by glusterFS. 
  ```
  deploy.py glusterfs create 
  ```
  Those pools can be removed via
  ```
  deploy.py glusterfs remove
  ```
  These two command may destroy all data stored on the target glusterFS partition, please use them with care. You will be asked to confirm the command specifically. 
  
4. Configure and build glusterFS docker 
  ```
  deploy.py glusterfs config
  ```

5. Label Kubernetes node for deployment. 
  ```
  deploy.py kubernetes labels
  ```
  
6. Start glusterFS daemon set and mount volumes.
  First time, you should use the follows to bootstrap the cluster. 
  ```
  deploy.py --glusterfs start kubernetes start glusterfs
  [Wait about 30 seconds]
  deploy.py kubernetes stop glusterfs
  ```
  The second time around, glusterFS daemon set can be started with 
  ```
  deploy.py kubernetes start glusterfs
  ```
  The glusterfs volume can now be used. 
  You may use:
  ```
  deploy.py --glusterfs format kubernetes start glusterfs
  [Wait about 30 seconds]
  deploy.py kubernetes stop glusterfs
  ```
  to remove any wrongly created volume in glusterfs, and recreate the volume. Please caution that this command will erasure all data on the glusterfs volume. Please use with care. 
  
7. [Administrator] Stop glusterFS daemon set. 
  ```
  deploy.py kubernetes stop glusterfs
  ```

8. Configure and mount glusterFS share to all nodes. 
  ```
  deploy.py mount
  ```

9. Trouble shooting:
   You may log onto a node deployed with glusterfs, and check its operating log at: /var/log/glusterfs.
   The launch log is available at /var/log/glusterfs/launch/launch.log
   Check on commonly observed issue of glusterfs [here](GlusterFS_FAQ.md).
