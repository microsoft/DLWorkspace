#sudo docker rm -f $(docker ps -a | grep 'k8s_kube\|k8s_POD' | awk '{print $1}')

