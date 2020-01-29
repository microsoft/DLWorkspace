#export HostIP=$(ip route get 8.8.8.8 | awk '{print $NF; exit}') && \
#curl -w "\n" 'https://discovery.etcd.io/new?size=3'

docker run -d -v /usr/share/ca-certificates/:/etc/ssl/certs -v /var/etcd:/var/etcd -p {{cnf["etcd3port1"]}}:{{cnf["etcd3port1"]}} -p {{cnf["etcd3portserver"]}}:{{cnf["etcd3portserver"]}} \
 --net=host \
 --restart always \
 --name etcd dlws/etcd:3.1.10 /usr/local/bin/etcd \
 -name $HOSTNAME \
 {% if cnf["etcd_node_num"] == 1 %}-initial-cluster {{cnf["hostname"]}}=https://{{cnf["etcd_node_ip"]}}:{{cnf["etcd3portserver"]}} \
 -initial-cluster-state new \
 -initial-cluster-token {{cnf["clusterId"]}} \
 -advertise-client-urls https://{{cnf["etcd_node_ip"]}}:{{cnf["etcd3port1"]}} \
 -listen-client-urls https://0.0.0.0:{{cnf["etcd3port1"]}} \
 -initial-advertise-peer-urls https://{{cnf["etcd_node_ip"]}}:{{cnf["etcd3portserver"]}} \
 -listen-peer-urls https://0.0.0.0:{{cnf["etcd3portserver"]}} \
 {% else %}-advertise-client-urls https://{{cnf["etcd_node_ip"]}}:{{cnf["etcd3port1"]}} \
 -listen-client-urls https://0.0.0.0:{{cnf["etcd3port1"]}} \
 -initial-advertise-peer-urls https://{{cnf["etcd_node_ip"]}}:{{cnf["etcd3portserver"]}} \
 -listen-peer-urls https://0.0.0.0:{{cnf["etcd3portserver"]}} \
 -discovery {{cnf["discovery_url"]}} \
 {% endif %}-data-dir /var/etcd/data \