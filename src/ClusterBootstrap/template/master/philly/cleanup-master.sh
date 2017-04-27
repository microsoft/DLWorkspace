sudo systemctl stop kubelet
sudo mkdir -p /etc/kubernetes
sudo mkdir -p /etc/ssl/etcd
sudo mkdir -p /opt/addons
sudo rm -r /etc/kubernetes
sudo rm -r /etc/ssl/etcd
sudo rm -r /opt/addons
sudo systemctl daemon-reload
sudo docker rm -f $(docker ps -a | grep 'k8s_kube\|k8s_POD' | awk '{print $1}')