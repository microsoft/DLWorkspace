sudo systemctl stop kubelet
timeout 10 docker rm -f $(timeout 3 docker ps -q -a)
sudo mkdir -p /etc/kubernetes
sudo mkdir -p /etc/ssl/etcd
sudo mkdir -p /opt/addons
sudo rm -r /etc/kubernetes
sudo rm -r /etc/ssl/etcd
sudo rm -r /etc/flannel
sudo rm -r /opt/addons
sudo systemctl daemon-reload
