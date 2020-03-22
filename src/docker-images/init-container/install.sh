cwd=`dirname $0`
ssh_root="$cwd/ssh_build/usr"

mkdir -p /usr/etc
cp $ssh_root/etc/* /usr/etc
cp $cwd/ssh_config/sshd/sshd_config /usr/etc/sshd_config

cp $cwd/ssh_config/init.d/* /etc/init.d
cp $cwd/ssh_config/default/* /etc/default
chmod +x /etc/init.d/ssh

cp -r $ssh_root/bin $ssh_root/sbin $ssh_root/lib $ssh_root/libexec /usr/

ssh-keygen -t dsa -f /usr/etc/ssh_host_dsa_key -N "" > /dev/null
ssh-keygen -t rsa -f /usr/etc/ssh_host_rsa_key -N "" > /dev/null
ssh-keygen -t ecdsa -f /usr/etc/ssh_host_ecdsa_key -N "" > /dev/null

cp $cwd/gpu_topo /usr/bin
