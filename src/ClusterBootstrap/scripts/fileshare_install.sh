sudo apt-get --no-install-recommends install -y nfs-common; 
sudo cp /lib/systemd/system/rpc-statd.service /etc/systemd/system/; 
sudo systemctl add-wants rpc-statd.service nfs-client.target; 
sudo systemctl reenable rpc-statd.service; sudo systemctl restart rpc-statd.service; 