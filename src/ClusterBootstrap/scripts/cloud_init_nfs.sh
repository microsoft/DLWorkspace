#!/bin/bash
source ../boot.env
if [ $PLATFORM_TYPE == "azure_cluster" ]; then
    sudo parted -l 2>&1 >/dev/null | awk -F': ' '{print $2}' > unlabeled_disk_file
    # Partition
    for disk in `cat unlabeled_disk_file`; do printf "n\n1\n\n\n8e00\nw\nY\n" | sudo gdisk ${disk}; done
    # Create PV
    for disk in `cat unlabeled_disk_file`; do sudo pvcreate ${disk}; done
    # Create vg
    pv_list=$(cat unlabeled_disk_file | awk '{printf("%s1\n", $1)}')
    sudo vgcreate dlts-data-lvm ${pv_list}
    sudo lvcreate -l 100%FREE -n dlts-data-lvm-vol1 dlts-data-lvm
    sudo mkfs.ext4 /dev/mapper/dlts--data--lvm-dlts--data--lvm--vol1
    echo "UUID=$(sudo blkid | grep dlts | sed -n 's/.*UUID=\"\(.*\)\" TYPE.*/\1/p')     $DATA_DISK_MNT_PATH   ext4   defaults,discard      0 0" | sudo tee -a /etc/fstab
fi
sudo mkdir -p $DATA_DISK_MNT_PATH
sudo mount $DATA_DISK_MNT_PATH

# setup NFS service
sudo apt-get update
sudo apt-get install -y nfs-kernel-server

IFS=';' read -ra files2share <<< $FILES_2_SHARE
for fs in "${files2share[@]}"; do
    sudo mkdir -p $fs
    sudo chmod -R 777 $fs
    sudo chown nobody:nogroup $fs
    IFS=';' read -ra node_ranges <<< $CIDR_NODE_RANGES
    for nr in "${node_ranges[@]}"; do
    echo "$fs $nr(rw,sync,no_subtree_check,no_root_squash)" | sudo tee -a /etc/exports
    done
    IFS=';' read -ra samba_ranges <<< $CIDR_SAMBA_RANGES
    for ns in "${samba_ranges[@]}"; do
    echo "$fs $ns(rw,fsid=1,nohide,insecure,sync,no_subtree_check,no_root_squash)" | sudo tee -a /etc/exports
    done
done

# Get number of CPU
num_cores=$(grep -c ^processor /proc/cpuinfo)
num_nfsd=$((${num_cores} * 2))
sudo sed -i "s/RPCNFSDCOUNT=8/RPCNFSDCOUNT=${num_nfsd}/" /etc/default/nfs-kernel-server
grep RPCNFSDCOUNT /etc/default/nfs-kernel-server

sudo systemctl restart nfs-kernel-server.service
sudo exportfs -a
