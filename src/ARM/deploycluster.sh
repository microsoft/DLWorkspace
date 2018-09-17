username=$1
cd /home/$username/dlworkspace/src/ClusterBootstrap
sudo -H -u $username python ./deploy.py --verbose scriptblocks azure
