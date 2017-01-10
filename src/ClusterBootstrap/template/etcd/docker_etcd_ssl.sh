export HostIP=$(ip route get 8.8.8.8 | awk '{print $NF; exit}') && \
#curl -w "\n" 'https://discovery.etcd.io/new?size=3'

docker run -d -v /usr/share/ca-certificates/:/etc/ssl/certs -v /etc/kubernetes/ssl:/etc/kubernetes/ssl -v /var/etcd:/var/etcd -p 4001:4001 -p 2380:2380 -p 2379:2379 \
 --net=host \
 --restart always \
 --name etcd gcr.io/google-containers/etcd:2.3.7 /usr/local/bin/etcd \
 -name $HOSTNAME \
 -advertise-client-urls https://${HostIP}:2379,https://${HostIP}:4001 \
 -listen-client-urls https://0.0.0.0:2379,https://0.0.0.0:4001 \
 -initial-advertise-peer-urls https://${HostIP}:2380 \
 -listen-peer-urls https://0.0.0.0:2380 \
 -discovery {{cnf["discovery_url"]}} \
 -data-dir /var/etcd/data \
 -client-cert-auth \
 -trusted-ca-file=/etc/kubernetes/ssl/etcd/ca.pem \
 -cert-file=/etc/kubernetes/ssl/etcd/etcd.pem \
 -key-file=/etc/kubernetes/ssl/etcd/etcd-key.pem \
 -peer-client-cert-auth \
 -peer-trusted-ca-file=/etc/kubernetes/ssl/etcd/ca.pem \
 -peer-cert-file=/etc/kubernetes/ssl/etcd/etcd.pem \
 -peer-key-file=/etc/kubernetes/ssl/etcd/etcd-key.pem
