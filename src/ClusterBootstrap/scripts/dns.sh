#this script aims to make resolv.conf static, 8.8.8.8 could have different values
sudo systemctl disable systemd-resolved.service
sudo systemctl stop systemd-resolved
echo "dns=default" | sudo tee -a /etc/NetworkManager/NetworkManager.conf
sudo rm /etc/resolv.conf
echo "nameserver 8.8.8.8" | sudo tee -a /etc/resolv.conf
# echo 'search {{cnf["network"]["domain"]}}' | esudo tee -a /etc/resolv.conf
# echo "search eastus.cloudapp.azure.com" | sudo tee -a /etc/resolv.conf
echo "search ${grep "azure_location" config.yaml | awk '{print $2}'}.cloudapp.azure.com" | sudo tee -a /etc/resolv.conf
sudo chattr -e /etc/resolv.conf
sudo chattr +i /etc/resolv.conf
# sudo service network-manager restart