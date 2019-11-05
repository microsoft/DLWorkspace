
sudo mkdir -p /data
sudo mount /data

# setup NFS service
sudo apt-get update
sudo apt-get install -y nfs-kernel-server


sudo mkdir -p /data/share
sudo chmod -R 777 /data/share
sudo chown nobody:nogroup /data/share

echo "/data/share 10.209.247.0/24(rw,fsid=1,nohide,insecure,sync,no_subtree_check,no_root_squash)" | sudo tee -a /etc/exports

echo "/data/share 127.0.0.1/32(rw,fsid=1,nohide,insecure,sync,no_subtree_check,no_root_squash)" | sudo tee -a /etc/exports

echo "/data/share 127.0.1.1/32(rw,fsid=1,nohide,insecure,sync,no_subtree_check,no_root_squash)" | sudo tee -a /etc/exports

echo "/data/share 104.44.112.0/24(rw,fsid=1,nohide,insecure,sync,no_subtree_check,no_root_squash)" | sudo tee -a /etc/exports



# Get number of CPU
num_cores=$(grep -c ^processor /proc/cpuinfo)
num_nfsd=$((${num_cores} * 2))
sudo sed -i "s/RPCNFSDCOUNT=8/RPCNFSDCOUNT=${num_nfsd}/" /etc/default/nfs-kernel-server
grep RPCNFSDCOUNT /etc/default/nfs-kernel-server

sudo systemctl restart nfs-kernel-server.service
sudo exportfs -a