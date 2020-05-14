IFS=';' read -ra file_share_sys <<< $FILE_SHARE_SYSTEM
if [[ " ${file_share_sys[@]} " =~ "nfs" ]]; then
    sudo apt-get --no-install-recommends install -y nfs-common; 
    sudo cp /lib/systemd/system/rpc-statd.service /etc/systemd/system/; 
    sudo systemctl add-wants rpc-statd.service nfs-client.target; 
    sudo systemctl reenable rpc-statd.service; sudo systemctl restart rpc-statd.service; 
fi
if [[ " ${file_share_sys[@]} " =~ "lustre" ]]; then
    docker pull mlcloudreg.westus.cloudapp.azure.com:5000/lustre-client/$(uname -r)
    docker create -ti --name lustre_client mlcloudreg.westus.cloudapp.azure.com:5000/lustre-client/$(uname -r):latest bash
    docker cp lustre_client:/usr/lustre-client-modules-$(uname -r)_2.13.0-1_amd64.deb ./
    docker cp lustre_client:/usr/lustre-client-utils_2.13.0-1_amd64.deb ./
    if [ ! -e lustre-client-utils_2.13.0-1_amd64.deb ]; then
        sudo bash build_lustre_client.sh
    fi;
    sudo apt install -y $(ls ./lustre-client-modules*.deb)
    sudo apt install -y $(ls ./lustre-client-utils*.deb)
fi