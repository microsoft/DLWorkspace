#export HostIP=$(ip route get 8.8.8.8 | awk '{print $NF; exit}') && \
#curl -w "\n" 'https://discovery.etcd.io/new?size=3'

docker run -d -v /usr/share/ca-certificates/:/etc/ssl/certs -v /var/etcd:/var/etcd -p {{cnf["etcd3port1"]}}:{{cnf["etcd3port1"]}} -p {{cnf["etcd3portserver"]}}:{{cnf["etcd3portserver"]}} -p {{cnf["etcd3port2"]}}:{{cnf["etcd3port2"]}} \
 --net=host \
 --restart always \
 --name etcd gcr.io/google-containers/etcd:3.0.4 /usr/local/bin/etcd \
 -name $HOSTNAME \
 -advertise-client-urls http://{{cnf["etcd_node_ip"]}}:{{cnf["etcd3port1"]}},http://{{cnf["etcd_node_ip"]}}:{{cnf["etcd3port2"]}} \
 -listen-client-urls http://0.0.0.0:{{cnf["etcd3port1"]}},http://0.0.0.0:{{cnf["etcd3port2"]}} \
 -initial-advertise-peer-urls http://{{cnf["etcd_node_ip"]}}:{{cnf["etcd3portserver"]}} \
 -listen-peer-urls http://0.0.0.0:2380 \
 -discovery {{cnf["discovery_url"]}} \
 -data-dir /var/etcd/data 

