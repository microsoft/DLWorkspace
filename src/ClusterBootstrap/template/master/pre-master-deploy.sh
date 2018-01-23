sudo mkdir -p /etc/kubernetes
sudo mkdir -p /etc/systemd/system/flanneld.service.d
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo mkdir -p /etc/flannel
sudo mkdir -p /etc/kubernetes/manifests
sudo mkdir -p /etc/kubernetes/ssl/
sudo mkdir -p /etc/kubernetes/pki/
sudo mkdir -p /etc/ssl/etcd
sudo mkdir -p /opt/addons
sudo mkdir -p /opt/bin
sudo chown -R $USER /etc/kubernetes
sudo chown -R $USER /etc/flannel
sudo chown -R $USER /opt/bin
sudo chown -R $USER /opt/addons
{% if "kubelogdir" in cnf %}
sudo mkdir -p {{cnf["kubelogdir"]}}/kubescheduler
sudo mkdir -p {{cnf["kubelogdir"]}}/kubeapiserver
sudo chown -R $USER {{cnf["kubelogdir"]}}
{% endif %}
