cwd=`dirname $0`

mkdir -p /etc/ssh
cp $cwd/ssh_build/etc/* /etc/ssh
cp $cwd/ssh_config/sshd/sshd_config /etc/ssh/sshd_config

cp $cwd/ssh_config/init.d/* /etc/init.d
cp $cwd/ssh_config/default/* /etc/default
chmod +x /etc/init.d/ssh

cp -r $cwd/ssh_build/bin $cwd/ssh_build/sbin $cwd/ssh_build/lib $cwd/ssh_build/libexec /usr/
