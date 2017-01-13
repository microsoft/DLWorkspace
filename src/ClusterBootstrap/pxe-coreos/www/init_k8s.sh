#! /bin/bash

export HostIP=$(ip route get 8.8.8.8 | awk '{print $NF; exit}')
mkdir -p /etc/kubernetes/ssl/
mkdir -p /etc/flannel
mkdir -p /etc/kubernetes/manifests

hostnamectl  set-hostname $HostIP
if [ ! -f /etc/kubernetes/ssl/worker.pem ]; then
    certstr=`wget -q -O - http://ccsdatarepo.westus.cloudapp.azure.com:9090/?workerId=$HOSTNAME\&workerIP=$HostIP`
    IFS=',' read -ra certs <<< "$certstr"
    echo ${certs[0]}  | base64 -d > /etc/kubernetes/ssl/ca.pem
    echo ${certs[1]}  | base64 -d > /etc/kubernetes/ssl/worker.pem
    echo ${certs[2]}  | base64 -d > /etc/kubernetes/ssl/worker-key.pem

    echo "FLANNELD_IFACE=${HostIP}" > /etc/flannel/options.env
    echo "FLANNELD_ETCD_ENDPOINTS=http://104.42.96.204:2379" >> /etc/flannel/options.env  
    mkdir -p /etc/systemd/system/flanneld.service.d/
    wget -q -O "/etc/systemd/system/flanneld.service.d/40-ExecStartPre-symlink.conf" http://ccsdatarepo.westus.cloudapp.azure.com/data/kube/kubelet/40-ExecStartPre-symlink.conf
    mkdir -p /etc/systemd/system/docker.service.d
    wget -q -O "/etc/systemd/system/docker.service.d/40-flannel.conf" http://ccsdatarepo.westus.cloudapp.azure.com/data/kube/kubelet/40-flannel.conf
    wget -q -O "/etc/systemd/system/kubelet.service" http://ccsdatarepo.westus.cloudapp.azure.com/data/kube/kubelet/kubelet.service
    wget -q -O  "/etc/kubernetes/manifests/kube-proxy.yaml" http://ccsdatarepo.westus.cloudapp.azure.com/data/kube/kubelet/kube-proxy.yaml
    wget -q -O "/etc/kubernetes/worker-kubeconfig.yaml" http://ccsdatarepo.westus.cloudapp.azure.com/data/kube/kubelet/worker-kubeconfig.yaml
fi

systemctl daemon-reload
systemctl start flanneld
systemctl start kubelet
systemctl enable flanneld
systemctl enable kubelet
systemctl start rpc-statd
