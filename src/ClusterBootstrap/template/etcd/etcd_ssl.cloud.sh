docker rm -f etcd3
systemctl daemon-reload
systemctl start etcd3
systemctl enable etcd3