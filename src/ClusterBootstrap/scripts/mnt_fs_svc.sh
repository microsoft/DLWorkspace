# !/bin/bash
# executed by infra and worker, assuming that NFS etc. is already setup, only mount from those storage machines
IFS=';' read -ra mountandlink <<< $MNT_N_LNK
for fs in "${mountandlink[@]}"; do
    sudo mkdir -p $fs
done
sudo systemctl stop auto_share.timer; 
sudo chmod +x /opt/auto_share/auto_share.py; 
sudo /opt/auto_share/auto_share.py; 
sudo systemctl daemon-reload; 
sudo systemctl enable auto_share.timer; 
sudo systemctl restart auto_share.timer; 
