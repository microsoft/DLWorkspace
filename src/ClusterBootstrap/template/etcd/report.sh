if [ -f /opt/systemid ]
then
   uuid=$(cat /opt/systemid)
else
   uuid=$(uuidgen)
   echo $uuid > /opt/systemid
fi

if [ -f /opt/systemrole ]
then
   systemrole="$(cat /opt/systemrole)"
else
   systemrole="etcd"
   echo $systemrole > /opt/systemrole
fi


while true
do
  export HostIP=$(ip route get 8.8.8.8 | awk '{print $NF; exit}')
  curl "http://dlws-clusterportal.westus.cloudapp.azure.com:5000/Report?hostIP=$HostIP&sysId=$uuid&clusterId={{cnf["clusterId"]}}&role=$systemrole" || echo "!!!Cannot report to cluster portal!!! Check the internet connection"
  echo "systemId:$uuid"    
  echo "systemrole:$systemrole"      
  echo "HostIP:$HostIP"      
  sleep 600
done
