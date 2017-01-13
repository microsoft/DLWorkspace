
# Generate certs for worker nodes
mkdir -p kubelet
openssl genrsa -out kubelet/apiserver-key.pem 2048
openssl req -new -key kubelet/apiserver-key.pem -out kubelet/apiserver.csr -subj "/CN=kube-apiserver" -config openssl-kubelet.cnf
openssl x509 -req -in kubelet/apiserver.csr -CA ca/ca.pem -CAkey ca/ca-key.pem -CAcreateserial -out kubelet/apiserver.pem -days 3650 -extensions v3_req -extfile openssl-kubelet.cnf
cp ca/ca.pem kubelet

rm ca/ca.srl
rm kubelet/apiserver.csr