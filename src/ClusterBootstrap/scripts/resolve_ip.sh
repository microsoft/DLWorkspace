#!/bin/bash
sudo rm -f /opt/defaultip
ip route show | grep -oE "default via .* src \b((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b" | awk '{print $9}' | sudo tee -a /opt/defaultip
ln=$(wc -l < /opt/defaultip)
if [ "$ln" -gt 1 ]; then
  echo "too many default vals"
  sudo sed '1!d' -i /opt/defaultip
elif [ "$ln" -lt 1 ]; then
  echo "empty ip file, use 127.0.0.1 as default ip"
  echo 127.0.0.1 | sudo tee -a /opt/defaultip
fi