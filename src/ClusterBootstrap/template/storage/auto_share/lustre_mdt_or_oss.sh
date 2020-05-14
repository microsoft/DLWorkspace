set -x
source /home/{{cnf["lustre_user"]}}/boot.env

# This section is moved from ./scripts/cloud_init_lustre.sh to here to avoid
# extremely long latency in file system operations (cp, rm, etc.).
# This section here takes ~1m7s to finish.
#-----------------------------------------------------------------------------
cd /home/{{cnf["lustre_user"]}}/cloudinit
bash ./prepare_lustre_centos.sh
bash ./dns.sh

bash ./pre-worker-deploy.sh
./cloud_init_mkdir_and_cp.py -p file_map.yaml -u $USER -m "kubernetes_common;kubelet_worker"

./render_env_vars.sh kubelet_worker/deploy/kubelet/options.env.template /etc/flannel/options.env ETCD_ENDPOINTS
./render_env_vars.sh kubelet_worker/deploy/kubelet/worker-kubeconfig.yaml.template /etc/kubernetes/worker-kubeconfig.yaml KUBE_API_SERVER
./render_env_vars.sh lustre.kubelet.service.template /etc/systemd/system/kubelet.service KUBE_LABELS

bash ./post-worker-deploy.sh
#-----------------------------------------------------------------------------

sudo modprobe -v lustre
sudo modprobe -v ldiskfs
# for on-premise machines, we need to get this file prepared in advance, maybe doesn't need to be unlabeled
if [ $PLATFORM_TYPE == "azure_cluster" ]; then
    sudo parted -l 2>&1 >/dev/null | awk -F': ' '{print $2}' > unlabeled_disk_file
fi
IFS=' ' read -ra disk_list <<< $(cat unlabeled_disk_file)
if [ ! -z "$MDT_ID" ]; then
sudo mkfs.lustre --fsname=lustrefs --mgs --mdt --index=$MDT_ID ${disk_list[0]}
sudo mkdir -p $DATA_DISK_MNT_PATH
echo "${disk_list[0]}                               $DATA_DISK_MNT_PATH               lustre  defaults,_netdev        0 0" | sudo tee -a /etc/fstab
sudo mount $DATA_DISK_MNT_PATH

# Lustre mount in jobs shows Permission denied even with drwxrwxrwx. E.g.
# $ /lustre$ ls -l
# ls: cannot open directory '.': Permission denied
# The solution is to remove client identity check on lustre on all MDTs
for path in $(ls -d /proc/fs/lustre/mdt/*); do
    sudo lctl set_param -n mdt.$(basename $path).identity_upcall NONE 2>/dev/null;
    identity_upcall_val=$(sudo lctl get_param -n "mdt.$(basename $path).identity_upcall")
    echo "mdt.$(basename $path).identity_upcall: ${identity_upcall_val}"
done

elif [ ! -z "$OSS_ID" ]; then
IFS=';' read -ra paths_2_mount <<< $DATA_DISK_MNT_PATH
until ping -c 5 $MGS_NODE_PRIVATE_IP 2>&1 >/dev/null; do
    sleep 1m;
    echo 'waiting for mgs node';
done;
for i in "${!disk_list[@]}"; do
sudo mkfs.lustre --fsname=lustrefs --mgsnode=$MGS_NODE_PRIVATE_IP@tcp --ost --index=$((OSS_ID+i)) ${disk_list[$i]}
echo "${disk_list[$i]}                              ${paths_2_mount[$i]}               lustre  defaults,_netdev        0 0" | sudo tee -a /etc/fstab
sudo mkdir -p ${paths_2_mount[$i]}
sudo mount ${paths_2_mount[$i]}
done
fi
sudo rm {{cnf["folder_auto_share"]}}/lustre_setup_finished
sudo systemctl disable lustre_server
