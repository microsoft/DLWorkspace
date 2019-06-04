sudo apt-get update
sudo apt-get install -y nfs-kernel-server

sudo mkdir -p /data/share 
sudo chown nobody:nogroup /data/share

echo "/data/share {{cnf["cloud_config"]["vnet_range"]}}(rw,sync,no_subtree_check,no_root_squash)" | sudo tee /etc/exports
sudo systemctl restart nfs-kernel-server


