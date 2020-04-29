IFS=';' read -ra file_share_sys <<< $FILE_SHARE_SYSTEM
if [[ " ${file_share_sys[@]} " =~ "nfs" ]]; then
sudo apt-get --no-install-recommends install -y nfs-common; 
sudo cp /lib/systemd/system/rpc-statd.service /etc/systemd/system/; 
sudo systemctl add-wants rpc-statd.service nfs-client.target; 
sudo systemctl reenable rpc-statd.service; sudo systemctl restart rpc-statd.service; 
fi
if [[ " ${file_share_sys[@]} " =~ "lustre" ]]; then
wget -O /tmp/lustre-client-modules-5.0.0-1027-azure_2.13.0-1_amd64.deb http://ccsdatarepo.westus.cloudapp.azure.com/data/lustre_clients_debs/5.0.0-1027-azure/lustre-client-modules-5.0.0-1027-azure_2.13.0-1_amd64.deb
wget -O /tmp/lustre-client-utils_2.13.0-1_amd64.deb http://ccsdatarepo.westus.cloudapp.azure.com/data/lustre_clients_debs/5.0.0-1027-azure/lustre-client-utils_2.13.0-1_amd64.deb
sudo apt install -y /tmp/lustre-client-modules-5.0.0-1027-azure_2.13.0-1_amd64.deb
sudo apt install -y /tmp/lustre-client-utils_2.13.0-1_amd64.deb
fi