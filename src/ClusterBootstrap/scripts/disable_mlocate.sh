#!/bin/bash

# Remove x permission to disable mlocate
sudo chmod -x /etc/cron.daily/mlocate

# Extra protection in updatedb.conf
if grep "PRUNEPATHS=" /etc/updatedb.conf | grep -q "/mnt"; then
    echo "/mnt exists under PRUNEPATHS"
else
    line=$(grep "PRUNEPATHS=" /etc/updatedb.conf)
    new_line=$(echo "${line::-1} /mnt /var/lib/kubelet\"")
    line=$(echo ${line} | sed 's/\//\\\//g')
    new_line=$(echo ${new_line} | sed 's/\//\\\//g')
    sudo sed -i "s/${line}/${new_line}/g" /etc/updatedb.conf
fi

if grep "PRUNEFS=" /etc/updatedb.conf | grep -q "fuse blobfuse"; then
    echo "fuse blobfuse exists under PRUNES"
else
    line=$(grep "PRUNEFS=" /etc/updatedb.conf)
    new_line=$(echo "${line::-1} fuse blobfuse\"")
    sudo sed -i "s/${line}/${new_line}/g" /etc/updatedb.conf
fi

echo ""
echo "Content of /etc/updatedb.conf"
cat /etc/updatedb.conf
