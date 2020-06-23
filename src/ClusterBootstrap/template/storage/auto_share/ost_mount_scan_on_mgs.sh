set -x
lfs df -h > mounted_ost
while IFS= read -r line; do
    IFS=',' read -ra disk_ids <<< $(echo $line | awk '{print $2}')
    for disk_id in "${disk_ids[@]}"; do
        disk_id_appendix="OST${disk_id}_UUID"
        if grep -q $disk_id_appendix mounted_ost ;
        then
            echo "${mt_tgt} mounted"
        else
            echo "${mt_tgt} not successfully mounted, waiting"
            exit 1
        fi
    done
done < {{cnf["folder_auto_share"]}}/lustre_disk_vc_map