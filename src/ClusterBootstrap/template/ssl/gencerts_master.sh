# Generate certs for API Server
mkdir -p apiserver
openssl genrsa -out apiserver/apiserver-key.pem 2048
openssl req -new -key apiserver/apiserver-key.pem -out apiserver/apiserver.csr -subj "/CN=kube-apiserver" -config openssl-apiserver.cnf
openssl x509 -req -in apiserver/apiserver.csr -CA ca/ca.pem -CAkey ca/ca-key.pem -CAcreateserial -out apiserver/apiserver.pem -days 3650 -extensions v3_req -extfile openssl-apiserver.cnf
cp ca/ca.pem apiserver
cp ca/ca-key.pem apiserver

rm apiserver/apiserver.csr