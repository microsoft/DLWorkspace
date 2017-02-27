#export HostIP=$(ip route get 8.8.8.8 | awk '{print $NF; exit}') && \
#curl -w "\n" 'https://discovery.etcd.io/new?size=3'

docker rm -f philly-etcd3
sudo rm -r /var/etcd/data

docker run -d -v /usr/share/ca-certificates/:/etc/ssl/certs -v /etc/etcd/ssl:/etc/etcd/ssl -v /var/etcd:/var/etcd -p 4001:4001 -p 2380:2380 -p 2379:2379 \
 --net=host \
 --restart always \
 --name philly-etcd3 gcr.io/google-containers/etcd:3.0.4 /usr/local/bin/etcd \
 -name $HOSTNAME \
 -advertise-client-urls https://{{cnf["etcd_node_ip"]}}:2379,https://{{cnf["etcd_node_ip"]}}:4001 \
 -listen-client-urls https://0.0.0.0:2379,https://0.0.0.0:4001 \
 -initial-advertise-peer-urls https://{{cnf["etcd_node_ip"]}}:2380 \
 -listen-peer-urls https://0.0.0.0:2380 \
 -discovery {{cnf["discovery_url"]}} \
 -data-dir /var/etcd/data \
 -client-cert-auth \
 -trusted-ca-file=/etc/etcd/ssl/ca.pem \
 -cert-file=/etc/etcd/ssl/etcd.pem \
 -key-file=/etc/etcd/ssl/etcd-key.pem \
 -peer-client-cert-auth \
 -peer-trusted-ca-file=/etc/etcd/ssl/ca.pem \
 -peer-cert-file=/etc/etcd/ssl/etcd.pem \
 -peer-key-file=/etc/etcd/ssl/etcd-key.pem
