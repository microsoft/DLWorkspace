#!/bin/bash
# read in env variables if necessary
bash ./prepare_vm_disk.sh
bash ./prepare_ubuntu.sh
bash ./disable_kernel_auto_updates.sh
bash ./docker_network_gc_setup.sh
bash ./dns.sh

# TODO if necessary, later make it filemap4$ROLE
source ../boot.env
# awk -F, '{print $1, $2}' infra.filemap | xargs -l ./mkdir_and_cp.sh
./cloud_init_mkdir_and_cp.py -p file_map.yaml -u $USER -m $MOD_2_CP

sudo systemctl stop etcd3
sudo mkdir -p /etc/etcd/ssl
sudo chown $USER /etc/etcd/ssl
chmod +x /opt/etcd_ssl.sh
sudo /opt/etcd_ssl.sh
echo $ETCDSERVER1

# or reference:
until curl --cacert /etc/etcd/ssl/ca.pem --cert /etc/etcd/ssl/etcd.pem --key /etc/etcd/ssl/etcd-key.pem https://$ETCDSERVER1:$ETCDPORT1/v2/keys; do
    sleep 5;
    echo 'waiting for ETCD service...';
done;

bash ./init_network.sh
# render ip to kube-apiserver.yaml
export MASTER_IP=$(cat /opt/defaultip)
./render_env_vars.sh kubernetes_infra/deploy/master/kube-apiserver.yaml kubernetes_infra/deploy/master/kube-apiserver.yaml.1st MASTER_IP
./render_env_vars.sh kubernetes_infra/deploy/master/kube-apiserver.yaml.1st /etc/kubernetes/manifests/kube-apiserver.yaml ETCD_ENDPOINTS 
./render_env_vars.sh infra.kubelet.service.template /etc/systemd/system/kubelet.service KUBE_LABELS 

bash ./pre-master-deploy.sh
bash ./post-master-deploy.sh

until curl -q http://127.0.0.1:8080/version/ ; do
    sleep 30;
    echo 'waiting for master kubernetes service...';
done;

until sudo /opt/bin/kubectl apply -f /opt/addons/kube-addons/weave.yaml --validate=false ; do
    sleep 5;
    echo 'waiting for master kube-addons weave...';
done ;

until sudo /opt/bin/kubectl apply -f /opt/addons/kube-addons/dashboard.yaml --validate=false ; do
    sleep 5;
    echo 'waiting for master kube-addons dashboard...';
done ;

until sudo /opt/bin/kubectl apply -f /opt/addons/kube-addons/dns-addon.yml --validate=false ;  do
    sleep 5;
    echo 'waiting for master kube-addons dns-addon...';
done ;

until sudo /opt/bin/kubectl apply -f /opt/addons/kube-addons/kube-proxy.json --validate=false ;  do
    sleep 5;
    echo 'waiting for master kube-addons kube-proxy.json...';
done ;

until sudo /opt/bin/kubectl create -f /etc/kubernetes/clusterroles/ ;  do
    sleep 5;
    echo 'waiting for master kubernetes clusterroles...';
done ;
sudo ln -s /opt/bin/kubectl /usr/bin/;

#mount
bash ./fileshare_install.sh
bash ./mnt_fs_svc.sh

bash ./pass_secret.sh
#start services
IFS=';' read -ra services <<< $KUBE_SERVICES

for svc in "${services[@]}"; do
    cntr=10
    until kubectl create -f $svc ; do
        sleep 5;
        cntr=$((cntr-1))
        echo "waiting for ${svc}, ${cntr} more attempts"
        if [ "$cntr" -le 0 ]; then
            break
        fi
    done
done
