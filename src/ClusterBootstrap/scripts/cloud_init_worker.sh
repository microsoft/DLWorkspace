#!/bin/bash
# set -ex
bash ./prepare_vm_disk.sh
bash ./prepare_ubuntu.sh
bash ./disable_kernel_auto_updates.sh
bash ./docker_network_gc_setup.sh
bash ./dns.sh

bash ./pre-worker-deploy.sh
source ../boot.env
./cloud_init_mkdir_and_cp.py -p file_map.yaml -u $USER -m $MOD_2_CP

./render_env_vars.sh kubelet_worker/deploy/kubelet/options.env.template /etc/flannel/options.env ETCD_ENDPOINTS
./render_env_vars.sh kubelet_worker/deploy/kubelet/worker-kubeconfig.yaml.template /etc/kubernetes/worker-kubeconfig.yaml KUBE_API_SERVER
./render_env_vars.sh worker.kubelet.service.template /etc/systemd/system/kubelet.service KUBE_LABELS

bash ./post-worker-deploy.sh

if [ ! -z "$MNT_N_LNK" ]; then
bash ./fileshare_install.sh
bash ./mnt_fs_svc.sh
fi

# the latest tested image is Canonical:UbuntuServer:18.04-LTS:18.04.201912180
IFS=';' read -ra script_modules <<< $SCRIPT_MODULES
if [[ "${script_modules[@]}" =~ "infiniband" ]]; then
    bash ./install_ib_on_sriov_az_cluster.sh
fi