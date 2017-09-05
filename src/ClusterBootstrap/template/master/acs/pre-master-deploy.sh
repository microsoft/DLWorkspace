sudo mkdir -p /etc/kubernetes
sudo mkdir -p /etc/kubernetes/manifests
sudo mkdir -p /etc/kubernetes/ssl/
sudo mkdir -p /etc/ssl/etcd
sudo mkdir -p /opt/addons
sudo mkdir -p /opt/bin
sudo mkdir -p /opt/cni/bin
sudo chown -R core /etc/kubernetes
sudo chown -R core /etc/flannel
sudo chown -R core /opt/bin
sudo chown -R core /opt/addons
sudo chown -R core /opt/cni/bin
