#! /bin/bash
export HostIP=$(ip route get 8.8.8.8 | awk '{print $NF; exit}')
hostnamectl  set-hostname $HostIP
export NSTR="null"

while [ -z "$ETCDENDPOINTS" ] || [ -z "$APISERVER" ] || [ $ETCDENDPOINTS == $NSTR ] || [ $APISERVER == $NSTR ]; 
do
	export ETCDENDPOINTS=$(wget -q -O - 'http://dlws-clusterportal.westus.cloudapp.azure.com:5000/GetClusterInfo?clusterId={{cnf["clusterId"]}}&key=etcd_endpoints' | sed 's/"//g' | sed 's/\//\\\//g')
	export APISERVER=$(wget -q -O - 'http://dlws-clusterportal.westus.cloudapp.azure.com:5000/GetClusterInfo?clusterId={{cnf["clusterId"]}}&key=api_server' | sed 's/"//g' | sed 's/\//\\\//g')
	if [ $ETCDENDPOINTS != $NSTR ] && [ $APISERVER != $NSTR ]; then
		echo $ETCDENDPOINTS
		echo $APISERVER
		sed "s/##etcd_endpoints##/$ETCDENDPOINTS/" /opt/options.env.template > /etc/flannel/options.env
		sed "s/##api_serviers##/$APISERVER/" /opt/kubelet.service.template > /etc/systemd/system/kubelet.service

		if [ ! -f /opt/kubelet ]; then
		    wget -q -O "/opt/kubelet" http://ccsdatarepo.westus.cloudapp.azure.com/data/kube/kubelet/kubelet
		    chmod +x /opt/kubelet

			systemctl daemon-reload
			systemctl start flanneld
			systemctl start kubelet
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



