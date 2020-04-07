#!/bin/bash
/opt/resolve_ip.sh
ETCDIP=$(cat /opt/defaultip)
/usr/bin/docker rm -f etcd3 
/usr/bin/docker run -v /usr/share/ca-certificates/mozilla:/etc/ssl/certs -v /etc/etcd/ssl:/etc/etcd/ssl -v /var/etcd:/var/etcd -p {{cnf["etcd3port1"]}}:{{cnf["etcd3port1"]}} -p {{cnf["etcd3portserver"]}}:{{cnf["etcd3portserver"]}} \
  --net=host \
  --name etcd3 {{cnf["dockers"]["container"]["etcd"]["fullname"]}} /usr/local/bin/etcd \
  -name $HOSTNAME \
  {% if cnf["etcd_node"]|length == 1 %}-initial-cluster $HOSTNAME=https://$ETCDIP:{{cnf["etcd3portserver"]}} \
  -initial-cluster-state new \
  -initial-cluster-token {{cnf["clusterId"]}} \
  -advertise-client-urls https://$ETCDIP:{{cnf["etcd3port1"]}} \
  -listen-client-urls https://0.0.0.0:{{cnf["etcd3port1"]}} \
  -initial-advertise-peer-urls https://$ETCDIP:{{cnf["etcd3portserver"]}} \
  -listen-peer-urls https://0.0.0.0:{{cnf["etcd3portserver"]}} \
  {% else %}-advertise-client-urls https://$ETCDIP:{{cnf["etcd3port1"]}} \
  -listen-client-urls https://0.0.0.0:{{cnf["etcd3port1"]}} \
  -initial-advertise-peer-urls https://$ETCDIP:{{cnf["etcd3portserver"]}} \
  -listen-peer-urls https://0.0.0.0:{{cnf["etcd3portserver"]}} \
  -discovery {{cnf["discovery_url"]}} \
  {% endif %}-data-dir /var/etcd/data \
  -client-cert-auth \
  -trusted-ca-file=/etc/etcd/ssl/ca.pem \
  -cert-file=/etc/etcd/ssl/etcd.pem \
  -key-file=/etc/etcd/ssl/etcd-key.pem \
  -peer-client-cert-auth \
  -peer-trusted-ca-file=/etc/etcd/ssl/ca.pem \
  -peer-cert-file=/etc/etcd/ssl/etcd.pem \
  -peer-key-file=/etc/etcd/ssl/etcd-key.pem
