if [ -f /etc/NetworkManager/NetworkManager.conf ]; then
	sed "s/^dns=dnsmasq$/#dns=dnsmasq/" /etc/NetworkManager/NetworkManager.conf > /tmp/NetworkManager.conf && sudo mv /tmp/NetworkManager.conf /etc/NetworkManager/NetworkManager.conf
	sudo service network-manager restart
fi