#!/bin/sh

TMP_KEY_PATH=/tmp/fix-rsa-key
REST_CONFIG_PATH=/etc/RestfulAPI/config.yaml

alias=$1

if [ $# != 1 ] ; then
	echo "Usage: $0 alias, update id_rsa keys in NFS and database" >&2
	exit 1
fi

ssh_directory=/dlwsdata/work/$alias/.ssh/

if [ ! -d $ssh_directory ] ; then
	echo "no directory found in $ssh_directory , maybe wrong alias?" >&2
	exit 2
fi

ssh-keygen -t rsa -b 4096 -f $TMP_KEY_PATH -P ''

mysql_config=`python3 -c "import yaml; t=yaml.load(open('$REST_CONFIG_PATH')); print('%s %s %s %s' % (t['mysql']['hostname'], t['mysql']['port'], t['mysql']['username'], t['mysql']['password']))"`

hostname=`echo $mysql_config | cut -d " " -f 1`
port=`echo $mysql_config | cut -d " " -f 2`
username=`echo $mysql_config | cut -d " " -f 3`
password=`echo $mysql_config | cut -d " " -f 4`

cluster_id=`grep clusterId $REST_CONFIG_PATH | cut -d : -f 2 | sed 's/ //g'`

mysql_connection_str="mysql -h $hostname -u $username -P $port -p$password DLWSCluster-$cluster_id"

uid=`echo "SELECT uid FROM identity WHERE identityName ='$alias@microsoft.com';" | $mysql_connection_str | tail -n 1`
gid=`echo "SELECT gid FROM identity WHERE identityName ='$alias@microsoft.com';" | $mysql_connection_str | tail -n 1`

public_key=`cat ${TMP_KEY_PATH}.pub`
private_key=`cat $TMP_KEY_PATH`

echo "UPDATE identity set public_key = '$public_key' WHERE identityName='$alias@microsoft.com' ; " | $mysql_connection_str
echo "UPDATE identity set private_key = '$private_key' WHERE identityName='$alias@microsoft.com' ; " | $mysql_connection_str

sudo mv $TMP_KEY_PATH $ssh_directory/id_rsa
sudo mv ${TMP_KEY_PATH}.pub $ssh_directory/id_rsa.pub
sudo chown $uid:$gid $ssh_directory/id_rsa $ssh_directory/id_rsa.pub

rm -f $TMP_KEY_PATH ${TMP_KEY_PATH}.pub
