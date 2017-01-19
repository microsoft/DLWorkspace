if [ -f /opt/systemid ]
then
   uuid=$(cat /opt/systemid)
else
   uuid=$(uuidgen)
   echo $uuid > /opt/systemid
fi
echo "systemId:$uuid"    
while true
do
  export HostIP=$(ip route get 8.8.8.8 | awk '{print $NF; exit}')
  curl "http://dlws-clusterportal.westus.cloudapp.azure.com:5000/Report?hostIP=$HostIP&sysId=$uuid&clusterId={{cnf["clusterId"]}}&role=master" || echo "!!!Cannot report to cluster portal!!! Check the internet connection"
  sleep 600
done
