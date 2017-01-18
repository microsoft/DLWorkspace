#! /bin/bash
/bin/bash -c 'until ping -c1 8.8.8.8; do sleep 1; done;'
export HostIP=$(ip route get 8.8.8.8 | awk '{print $NF; exit}')
hostnamectl  set-hostname $HostIP
export NSTR="null"

systemctl stop flanneld
systemctl stop kubelet

while [ -z "$ETCDENDPOINTS" ] || [ -z "$APISERVER" ] || [ $ETCDENDPOINTS == $NSTR ] || [ $APISERVER == $NSTR ]; 
do
	export ETCDENDPOINTS=$(wget -q -O - 'http://dlws-clusterportal.westus.cloudapp.azure.com:5000/GetClusterInfo?clusterId={{cnf["clusterId"]}}&key=etcd_endpoints' | sed 's/"//g' | sed 's/\//\\\//g')
	export APISERVER=$(wget -q -O - 'http://dlws-clusterportal.westus.cloudapp.azure.com:5000/GetClusterInfo?clusterId={{cnf["clusterId"]}}&key=api_server' | sed 's/"//g' | sed 's/\//\\\//g')
	if [ $ETCDENDPOINTS != $NSTR ] && [ $APISERVER != $NSTR ]; then
		echo $ETCDENDPOINTS
		echo $APISERVER
		mkdir -p /etc/flannel
		sed "s/##etcd_endpoints##/$ETCDENDPOINTS/" "/opt/options.env.template" > "/etc/flannel/options.env"
		sed "s/##api_serviers##/$APISERVER/" /opt/kubelet.service.template > /etc/systemd/system/kubelet.service
		sed "s/##api_serviers##/$APISERVER/" /etc/kubernetes/worker-kubeconfig.yaml.template > /etc/kubernetes/worker-kubeconfig.yaml



		if [ ! -f /opt/kubelet ]; then
			echo "Starting kubelet service"
		    wget -q -O "/opt/kubelet" http://ccsdatarepo.westus.cloudapp.azure.com/data/kube/kubelet/kubelet
		    chmod +x /opt/kubelet

			systemctl daemon-reload
			systemctl stop docker
			systemctl stop flanneld
			systemctl stop kubelet
			systemctl start flanneld
			systemctl start kubelet
			systemctl start docker
			systemctl enable flanneld
			systemctl enable kubelet
			systemctl start rpc-statd
		fi
	fi
	sleep 10
done


while true
do
	curl "http://dlws-clusterportal.westus.cloudapp.azure.com:5000/Report?hostIP=$HostIP&clusterId={{cnf["clusterId"]}}&role=worker" || echo "!!!Cannot report to cluster portal!!! Check the internet connection"
    sleep 600
done



