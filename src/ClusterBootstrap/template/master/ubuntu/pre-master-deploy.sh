sudo mkdir -p /etc/kubernetes
sudo mkdir -p /etc/kubernetes/manifests
sudo mkdir -p /etc/kubernetes/ssl/
sudo mkdir -p /etc/kubernetes/pki/
sudo mkdir -p /etc/kubernetes/volumeplugins
sudo mkdir -p /etc/ssl/etcd
sudo mkdir -p /opt/addons
sudo mkdir -p /opt/addons/kube-addons
sudo mkdir -p /opt/bin
sudo mkdir -p /opt/cni/bin
sudo chown -R $USER /etc/kubernetes
sudo chown -R $USER /etc/flannel
sudo chown -R $USER /opt/bin
sudo chown -R $USER /opt/addons
sudo chown -R $USER /opt/cni/bin
