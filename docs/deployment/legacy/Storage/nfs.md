# Deployment NFS server

The document describes the procedure to setup NFS server. We follow the procedure in https://www.digitalocean.com/community/tutorials/how-to-set-up-an-nfs-mount-on-ubuntu-16-04

1.  Install nfs kernel.
  ```
  sudo apt-get update
  sudo apt-get --no-install-recommends install -y nfs-kernel-server
  ```

2. Format ext4 partition, and mount the partition to a particular mount point
  ```
  sudo mkdir -p /mnt/dlwsdata
  # nfs use nobody:nogroup to visit
  sudo chown nobody:nogroup /mnt/dlwsdata
  # discover the UUID information of the block device.
  sudo lsblk -o Name,FSTYPE,UUID  
  # edit /etc/fstab, and add entry, which mounts a particular UUID storage device to the mount point. Last number is the fsck order.
  UUID=e2c91cb7-c97d-46f7-a51b-001a06a14e08 /mnt/dlwsdata   ext4    errors=remount-ro 0     2
  # Comment any swap entry, as kubelet doesn't run with swap on
  # causes all filesystems mentioned in fstab (of the proper type and/or having or not having the proper options) to be mounted as indicated, except for those whose line contains the noauto keyword. 
  sudo mount -a
  ```

3. Modify /etc/exports
  /mnt/dlwsdata       *(rw,sync,no_root_squash,no_subtree_check)

4. Check firewall status, if any. 
  ```
  sudo ufw status
  ```

5. Start NFS server. 
   ```
   sudo systemctl restart nfs-kernel-server
   ```
