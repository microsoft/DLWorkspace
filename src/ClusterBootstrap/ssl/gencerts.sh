
# Generate CA
mkdir ca
openssl genrsa -out ca/ca-key.pem 2048
openssl req -x509 -new -nodes -key ca/ca-key.pem -days 10000 -out ca/ca.pem -subj "/CN=kube-ca"



# Generate certs for API Server
mkdir apiserver
openssl genrsa -out apiserver/apiserver-key.pem 2048
openssl req -new -key apiserver/apiserver-key.pem -out apiserver/apiserver.csr -subj "/CN=kube-apiserver" -config openssl-apiserver.cnf
openssl x509 -req -in apiserver/apiserver.csr -CA ca/ca.pem -CAkey ca/ca-key.pem -CAcreateserial -out apiserver/apiserver.pem -days 3650 -extensions v3_req -extfile openssl-apiserver.cnf
cp ca/ca.pem apiserver
cp ca/ca-key.pem apiserver

# Generate certs for ETCD Server
mkdir etcd
openssl genrsa -out etcd/etcd-key.pem 2048
openssl req -new -key etcd/etcd-key.pem -out etcd/etcd.csr -subj "/CN=kube-apiserver" -config openssl-etcd.cnf
openssl x509 -req -in etcd/etcd.csr -CA ca/ca.pem -CAkey ca/ca-key.pem -CAcreateserial -out etcd/etcd.pem -days 3650 -extensions v3_req -extfile openssl-etcd.cnf
cp ca/ca.pem etcd

rm etcd/etcd.csr
rm ca/ca.srl
rm apiserver/apiserver.csr