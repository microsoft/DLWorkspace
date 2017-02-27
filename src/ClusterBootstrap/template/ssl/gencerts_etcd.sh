# Generate certs for ETCD Server
mkdir -p etcd
openssl genrsa -out etcd/etcd-key.pem 2048
openssl req -new -key etcd/etcd-key.pem -out etcd/etcd.csr -subj "/CN=kube-apiserver" -config openssl-etcd.cnf
openssl x509 -req -in etcd/etcd.csr -CA ca/ca.pem -CAkey ca/ca-key.pem -CAcreateserial -out etcd/etcd.pem -days 3650 -extensions v3_req -extfile openssl-etcd.cnf
cp ca/ca.pem etcd

rm etcd/etcd.csr
