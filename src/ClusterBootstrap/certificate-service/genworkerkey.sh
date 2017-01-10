#! /bin/bash
WORKER_FQDN=$1
WORKER_IP1=$2
WORKER_IP2=$3
echo =======${WORKER_FQDN}========
echo =======${WORKER_IP1}========
echo =======${WORKER_IP2}========

rm -r workers/$WORKER_IP1
mkdir -p workers/$WORKER_IP1
openssl genrsa -out workers/$WORKER_IP1/${WORKER_FQDN}-worker-key.pem 2048
#WORKER_IP1=${WORKER_IP1} WORKER_IP2=${WORKER_IP2} WORKER_DNS=${WORKER_DNS} openssl req -new -key workers/$WORKER_IP1/${WORKER_FQDN}-worker-key.pem -out workers/$WORKER_IP1/${WORKER_FQDN}-worker.csr -subj "/CN=${WORKER_FQDN}" -config openssl.cnf

WORKER_IP1=${WORKER_IP1} WORKER_IP2=${WORKER_IP2} WORKER_DNS=${WORKER_DNS} openssl req -new -key workers/$WORKER_IP1/${WORKER_FQDN}-worker-key.pem -out workers/$WORKER_IP1/${WORKER_FQDN}-worker.csr -subj "/CN=kube-apiserver" -config openssl.cnf

WORKER_IP1=${WORKER_IP1} WORKER_IP2=${WORKER_IP2} WORKER_DNS=${WORKER_DNS} openssl x509 -req -in workers/$WORKER_IP1/${WORKER_FQDN}-worker.csr -CA ./ca/ca.pem -CAkey ./ca/ca-key.pem -CAcreateserial -out workers/$WORKER_IP1/${WORKER_FQDN}-worker.pem -days 3650 -extensions v3_req -extfile openssl.cnf
