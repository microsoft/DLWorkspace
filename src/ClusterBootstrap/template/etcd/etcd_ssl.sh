#ETCD_VER=v3.3.2 && DOWNLOAD_URL=https://github.com/coreos/etcd/releases/download && \
#curl -L ${DOWNLOAD_URL}/${ETCD_VER}/etcd-${ETCD_VER}-linux-amd64.tar.gz -o /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz && \
#mkdir -p /tmp/test-etcd && \
#tar xzvf /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz -C /tmp/test-etcd --strip-components=1 && \
#mkdir -p /opt/bin && \
#mv /tmp/test-etcd/etcd /opt/bin && \
#mv /tmp/test-etcd/etcdctl /opt/bin 
#rm -r /tmp/test-etcd
docker rm -f etcd3
systemctl daemon-reload
systemctl start etcd3
systemctl enable etcd3