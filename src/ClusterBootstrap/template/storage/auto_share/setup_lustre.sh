cat <<EOM >/etc/yum.repos.d/lustre.repo 
[lustre-server]
name=lustre-server
baseurl=https://downloads.whamcloud.com/public/lustre/latest-feature-release/el7/server
# exclude=*debuginfo*
gpgcheck=0

[lustre-client]
name=lustre-client
baseurl=https://downloads.whamcloud.com/public/lustre/latest-feature-release/el7/client
# exclude=*debuginfo*
gpgcheck=0

[e2fsprogs-wc]
name=e2fsprogs-wc
baseurl=https://downloads.whamcloud.com/public/e2fsprogs/latest/el7
# exclude=*debuginfo*
gpgcheck=0
EOM




yum install -y e2fsprogs
mkdir /tmp/lustre
wget -O /tmp/lustre/kernel-3.10.0-1062.1.1.el7_lustre.x86_64.rpm https://downloads.whamcloud.com/public/lustre/lustre-2.13.0/el7.7.1908/server/RPMS/x86_64/kernel-3.10.0-1062.1.1.el7_lustre.x86_64.rpm
wget -O /tmp/lustre/lustre-2.13.0-1.el7.x86_64.rpm https://downloads.whamcloud.com/public/lustre/lustre-2.13.0/el7.7.1908/server/RPMS/x86_64/lustre-2.13.0-1.el7.x86_64.rpm
wget -O /tmp/lustre/kmod-lustre-2.13.0-1.el7.x86_64.rpm https://downloads.whamcloud.com/public/lustre/lustre-2.13.0/el7.7.1908/server/RPMS/x86_64/kmod-lustre-2.13.0-1.el7.x86_64.rpm
wget -O /tmp/lustre/kmod-lustre-osd-ldiskfs-2.13.0-1.el7.x86_64.rpm https://downloads.whamcloud.com/public/lustre/lustre-2.13.0/el7.7.1908/server/RPMS/x86_64/kmod-lustre-osd-ldiskfs-2.13.0-1.el7.x86_64.rpm
wget -O /tmp/lustre/lustre-osd-ldiskfs-mount-2.13.0-1.el7.x86_64.rpm https://downloads.whamcloud.com/public/lustre/lustre-2.13.0/el7.7.1908/server/RPMS/x86_64/lustre-osd-ldiskfs-mount-2.13.0-1.el7.x86_64.rpm
wget -O /tmp/lustre/lustre-tests-2.13.0-1.el7.x86_64.rpm https://downloads.whamcloud.com/public/lustre/lustre-2.13.0/el7.7.1908/server/RPMS/x86_64/lustre-tests-2.13.0-1.el7.x86_64.rpm

yum install -y /tmp/lustre/kernel-3.10.0-1062.1.1.el7_lustre.x86_64.rpm
yum install -y /tmp/lustre/kmod*
yum install -y /tmp/lustre/lustre*

# generate token
mkdir -p {{cnf["folder_auto_share"]}}
touch {{cnf["folder_auto_share"]}}/lustre_setup_finished
chown -R {{cnf["lustre_user"]}}:{{cnf["lustre_user"]}} {{cnf["folder_auto_share"]}}
# we further setup service that examine 2 token: when lustre_setup_finished exist, lustre_nodes_locally_mounted doesn't, execute following script
source ../boot.env
python ./cloud_init_mkdir_and_cp.py -p file_map.yaml -u $USER -m $MOD_2_CP
systemctl enable lustre_server
reboot
