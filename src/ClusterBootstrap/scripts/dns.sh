sudo systemctl disable systemd-resolved.service
sudo systemctl stop systemd-resolved
# echo "dns=default" | sudo tee -a /etc/NetworkManager/NetworkManager.conf
sudo rm /etc/resolv.conf
echo "nameserver 8.8.8.8" | sudo tee -a /etc/resolv.conf
echo 'search eastus.cloudapp.azure.com' | sudo tee -a /etc/resolv.conf
# sudo service network-manager restart