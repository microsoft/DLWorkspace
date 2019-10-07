sudo systemctl stop kubelet
sudo systemctl stop kubecri
sudo systemctl restart docker
sudo docker rm -f $(docker ps -a | grep 'k8s_kube\|k8s_POD' | awk '{print $1}')

sudo mkdir -p /etc/kubernetes
sudo mkdir -p /etc/kubernetes/manifests
sudo mkdir -p /etc/kubernetes/ssl/
sudo mkdir -p /etc/kubernetes/volumeplugins
sudo mkdir -p /etc/ssl/etcd
sudo mkdir -p /opt/bin
sudo mkdir -p /opt/addons/kube-addons
sudo rm -r /etc/kubernetes/manifests/*
sudo rm -r /etc/kubernetes/ssl/*
sudo rm -r /etc/ssl/etcd/*
sudo rm -r /opt/addons/kube-addons/*
sudo rm -rf /etc/cni/net.d
sudo chown -R $USER /etc/kubernetes
sudo chown -R $USER /opt/addons/kube-addons
