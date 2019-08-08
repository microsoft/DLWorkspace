loc_wht_spc=$(grep "azure_location" config.yaml | awk '{print $2}')
loc="$(echo -e "${loc_wht_spc}" | tr -d '[:space:]')"
pre="echo \"search "
apd=".cloudapp.azure.com\" | sudo tee -a /etc/resolv.conf"
rm scripts/dns.sh
echo "sudo systemctl disable systemd-resolved.service" > scripts/dns.sh
echo "sudo systemctl stop systemd-resolved" >> scripts/dns.sh
echo "echo \"dns=default\" | sudo tee -a /etc/NetworkManager/NetworkManager.conf" >> scripts/dns.sh
echo "sudo rm /etc/resolv.conf" >> scripts/dns.sh
echo "echo \"nameserver 8.8.8.8\" | sudo tee -a /etc/resolv.conf" >> scripts/dns.sh
echo $pre$loc$apd >> scripts/dns.sh
echo "sudo chattr -e /etc/resolv.conf" >> scripts/dns.sh
echo "sudo chattr +i /etc/resolv.conf" >> scripts/dns.sh
