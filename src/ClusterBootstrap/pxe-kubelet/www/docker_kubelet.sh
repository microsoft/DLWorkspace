#! /bin/bash
sudo mkdir -p /var/lib/kubelet
#sudo mount --bind /var/lib/kubelet /var/lib/kubelet
#sudo mount --make-shared /var/lib/kubelet
sysID=`ifconfig | grep ether | awk '{print $2}' | sed 's/://g' | head -1`
sudo hostnamectl  set-hostname $sysID
docker run -d \
 --hostname=kubelet-$HOSTNAME-$sysID \
 --restart always \
 --name kubelet \
 --net=host \
 --pid=host \
 -v /srv/kubernetes:/srv/kubernetes:ro \
 -v /etc/kubernetes:/etc/kubernetes:ro \
 -v /dev:/dev \
 -v /sys:/sys:ro \
 -v /var/run:/var/run:rw \
 -v /var/lib/docker/:/var/lib/docker:rw \
 -v /var/lib/kubelet/:/var/lib/kubelet \
 -v /var/log:/var/log \
 -e NODE_X_POD_CIDR:10.0.0.0/16 \
 --privileged=true \
gcr.io/google-containers/hyperkube-amd64:v1.4.1 \
    /hyperkube kubelet \
    --address=0.0.0.0 \
    --allow-privileged=true \
    --enable-server \
    --enable-debugging-handlers \
    --kubeconfig=/srv/kubernetes/kubeconfig.json \
    --config=/etc/kubernetes/manifests \
    --v=2 \
    --api-servers=https://104.40.86.142 \
    --hairpin-mode=promiscuous-bridge \
    --cluster-dns=10.0.0.10 \
    --cluster-domain=cluster.local \
    --network-plugin=kubenet \
    --reconcile-cidr

