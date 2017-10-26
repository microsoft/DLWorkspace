sudo systemctl stop kubelet
sudo timeout 10 docker rm -f $(docker ps -a | grep 'k8s_kube\|k8s_POD' | awk '{print $1}')
sudo systemctl stop flanneld
sudo systemctl stop docker
sudo mkdir -p /etc/kubernetes
sudo mkdir -p /etc/systemd/system/flanneld.service.d
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo mkdir -p /etc/flannel
sudo mkdir -p /etc/ssl/etcd
sudo mkdir -p /opt/addons
sudo rm -r /etc/kubernetes
sudo rm -r /etc/ssl/etcd
sudo rm -r /etc/systemd/system/flanneld.service.d
sudo rm -r /etc/systemd/system/docker.service.d
sudo rm -r /etc/flannel
sudo rm -r /opt/addons
sudo systemctl daemon-reload
sudo systemctl start docker