#! /bin/bash
# Wait for network to be ready 
export discoverserver="$(cat /opt/discoverserver)"
/bin/bash -c 'until ping -c1 ${discoverserver}; do sleep 1; done;'

export NSTR="null"


mkdir -p /opt/bin

while [ -z "$ETCDENDPOINTS" ] || [ -z "$APISERVER" ] || [ "$ETCDENDPOINTS" == "$NSTR" ] || [ "$APISERVER" == "$NSTR" ]; 
do
	homeinserver="$(cat /opt/homeinserver)"
	export ETCDENDPOINTS=$(wget -q -O - "$homeinserver/GetClusterInfo?clusterId={{cnf["clusterId"]}}&key=etcd_endpoints" | sed 's/"//g' | sed 's/\//\\\//g')
	export APISERVER=$(wget -q -O - "$homeinserver/GetClusterInfo?clusterId={{cnf["clusterId"]}}&key=api_server" | sed 's/"//g' | sed 's/\//\\\//g')
	echo "ETCDENDPOINTS = ${ETCDENDPOINTS}, APISERVER=${APISERVER} "
	if [ ! -z "$ETCDENDPOINTS" ] && [ ! -z "$APISERVER" ] && [ "$ETCDENDPOINTS" != "$NSTR" ] && [ "$APISERVER" != "$NSTR" ]; then
		if [ ! -f /opt/bin/kubelet ]; then
			systemctl stop flanneld
			systemctl stop kubelet
			mkdir -p /etc/flannel
			sed "s/##etcd_endpoints##/$ETCDENDPOINTS/" "/opt/options.env.template" > "/etc/flannel/options.env"
			sed "s/##api_servers##/$APISERVER/" /opt/kubelet.service.template > /etc/systemd/system/kubelet.service
			sed "s/##api_servers##/$APISERVER/" /etc/kubernetes/worker-kubeconfig.yaml.template > /etc/kubernetes/worker-kubeconfig.yaml

			echo "Starting kubelet service"
		    #wget -q -O "/opt/bin/kubelet" http://ccsdatarepo.westus.cloudapp.azure.com/data/kube/kubelet/kubelet
			kubeid=$(docker create {{cnf["dockers"]["container"]["hyperkube"]["fullname"]}})
			docker cp $kubeid:/hyperkube /opt/bin/kubelet
			docker rm -v $kubeid
		    chmod +x /opt/bin/kubelet

			systemctl daemon-reload
			systemctl stop nvidia-driver
			systemctl stop nvidia-docker
			systemctl stop docker
			systemctl stop flanneld
			systemctl stop kubelet
			systemctl start flanneld
			systemctl start docker
			systemctl start nvidia-driver
			systemctl start nvidia-docker
			systemctl start kubelet
			systemctl enable flanneld
			systemctl enable kubelet
			systemctl start rpc-statd
		fi
	fi
	echo "Sleep 10 ... "
	sleep 10
done

