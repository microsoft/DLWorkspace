sudo systemctl stop kubelet
sudo timeout 10 docker rm -f $(docker ps -a | grep 'k8s_kube\|k8s_POD' | awk '{print $1}')
sudo mkdir -p /etc/kubernetes
sudo mkdir -p /opt/addons
sudo rm -r /etc/kubernetes
sudo rm -r /opt/addons
sudo rm -r /opt/cni
sudo systemctl daemon-reload

# pre deployment
sudo mkdir -p /etc/kubernetes
sudo mkdir -p /etc/kubernetes/manifests
sudo mkdir -p /etc/kubernetes/ssl/
sudo mkdir -p /etc/kubernetes/pki/
sudo mkdir -p /opt/addons
sudo mkdir -p /opt/bin
sudo mkdir -p /opt/cni/bin
sudo chown -R $USER /etc/kubernetes
sudo chown -R $USER /etc/flannel
sudo chown -R $USER /opt/bin
sudo chown -R $USER /opt/addons
{% if "kubelogdir" in cnf %}
sudo mkdir -p {{cnf["kubelogdir"]}}/kubescheduler
sudo mkdir -p {{cnf["kubelogdir"]}}/kubeapiserver
sudo chown -R $USER {{cnf["kubelogdir"]}}
{% endif %}
