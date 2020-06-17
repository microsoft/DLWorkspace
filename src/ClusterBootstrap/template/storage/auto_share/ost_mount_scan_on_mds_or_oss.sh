set -x
# spare some time to mount Lustre FS
sleep {{cnf["ost_reboot_wait_time"]}}
source /home/{{cnf["lustre_user"]}}/boot.env
mount | awk '{print $3}' > mounted_path
IFS=';' read -ra mount_targets <<< $DATA_DISK_MNT_PATH
for mt_tgt in "${mount_targets[@]}"; do
    if grep -q $mt_tgt mounted_path ;
    then
        echo "${mt_tgt} mounted"
    else
        echo "${mt_tgt} not successfully mounted, rebooting"
        sudo reboot
    fi
done
# mount from mgs to self as client
if grep -q /mnt/mgs_client mounted_path ;
then
    echo "lustre fs mounted to /mnt/mgs_client" 
else
    sudo mkdir -p /mnt/mgs_client
    until sudo mount $MGS_NODE_PRIVATE_IP:/$LUSTRE_FS_NAME /mnt/mgs_client -t lustre 2>&1 >/dev/null; do
        sleep 1m;
        echo 'waiting for mgs node';
    done;
fi