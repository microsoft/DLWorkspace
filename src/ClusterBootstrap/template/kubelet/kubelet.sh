#! /bin/bash

export HostIP=$(ip route get 8.8.8.8 | awk '{print $NF; exit}')
mkdir -p /etc/kubernetes/ssl/
mkdir -p /etc/flannel
mkdir -p /etc/kubernetes/manifests
mkdir -p /opt

hostnamectl  set-hostname $HostIP
if [ ! -f /etc/kubernetes/ssl/worker.pem ]; then
    certstr=`wget -q -O - http://{{cnf["webserver"]}}:5000/genkey?workerId=$HOSTNAME\&workerIP=$HostIP`
    certstr1=${certstr//\"/}
    IFS=',' read -ra certs <<< "$certstr1"

    echo ${certs[0]}  | base64 -d > /etc/kubernetes/ssl/ca.pem
    echo ${certs[1]}  | base64 -d > /etc/kubernetes/ssl/worker.pem
    echo ${certs[2]}  | base64 -d > /etc/kubernetes/ssl/worker-key.pem
    mkdir -p /etc/ssl/etcd/
    cp /etc/kubernetes/ssl/ca.pem /etc/ssl/etcd/ca.pem
    cp /etc/kubernetes/ssl/worker.pem /etc/ssl/etcd/apiserver.pem
    cp /etc/kubernetes/ssl/worker-key.pem /etc/ssl/etcd/apiserver-key.pem
    #echo "FLANNELD_IFACE=${HostIP}" > /etc/flannel/options.env

    wget -q -O "/etc/flannel/options.env" http://{{cnf["webserver"]}}/options.env

    mkdir -p /etc/systemd/system/flanneld.service.d/
    wget -q -O "/etc/systemd/system/flanneld.service.d/40-ExecStartPre-symlink.conf" http://{{cnf["webserver"]}}/40-ExecStartPre-symlink.conf
    mkdir -p /etc/systemd/system/docker.service.d
    wget -q -O "/etc/systemd/system/docker.service.d/40-flannel.conf" http://{{cnf["webserver"]}}/40-flannel.conf
    wget -q -O "/etc/systemd/system/kubelet.service" http://{{cnf["webserver"]}}/kubelet.service
    wget -q -O  "/etc/kubernetes/manifests/kube-proxy.yaml" http://{{cnf["webserver"]}}/kube-proxy.yaml
    wget -q -O "/etc/kubernetes/worker-kubeconfig.yaml" http://{{cnf["webserver"]}}/worker-kubeconfig.yaml
    wget -q -O "/opt/kubelet" http://{{cnf["webserver"]}}/kubelet
    chmod +x /opt/kubelet
fi

systemctl daemon-reload
systemctl start flanneld
systemctl start kubelet
systemctl enable flanneld
systemctl enable kubelet
systemctl start rpc-statd

