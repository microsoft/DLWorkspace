sudo timeout 10 docker rm -f $(docker ps -a | grep 'k8s_kube\|k8s_POD' | awk '{print $1}')
sudo mkdir -p /etc/flannel
sudo mkdir -p /opt/addons
sudo rm -r /etc/flannel
sudo rm -r /opt/addons
sudo systemctl daemon-reload
