#export HostIP=$(ip route get 8.8.8.8 | awk '{print $NF; exit}') && \
#curl -w "\n" 'https://discovery.etcd.io/new?size=3'

docker run -d -v /usr/share/ca-certificates/:/etc/ssl/certs -v /var/etcd:/var/etcd -p 4001:4001 -p 2380:2380 -p 2379:2379 \
 --net=host \
 --restart always \
 --name etcd gcr.io/google-containers/etcd:3.0.4 /usr/local/bin/etcd \
 -name $HOSTNAME \
 -advertise-client-urls http://{{cnf["etcd_node_ip"]}}:2379,http://{{cnf["etcd_node_ip"]}}:4001 \
 -listen-client-urls http://0.0.0.0:2379,http://0.0.0.0:4001 \
 -initial-advertise-peer-urls http://{{cnf["etcd_node_ip"]}}:2380 \
 -listen-peer-urls http://0.0.0.0:2380 \
 -discovery {{cnf["discovery_url"]}} \
 -data-dir /var/etcd/data 

