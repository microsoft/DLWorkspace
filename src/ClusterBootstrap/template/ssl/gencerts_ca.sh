
# Generate CA
mkdir -p ca
openssl genrsa -out ca/ca-key.pem 2048
openssl req -x509 -new -nodes -key ca/ca-key.pem -days 10000 -out ca/ca.pem -subj "/CN=kube-ca"
