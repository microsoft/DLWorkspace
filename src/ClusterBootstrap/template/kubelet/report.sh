if [ -f /opt/systemrole ]
then
   systemrole="$(cat /opt/systemrole)"
else
   systemrole="worker"
   echo $systemrole > /opt/systemrole
fi

if [ -f /opt/systemid ]
then
   uuid=$(cat /opt/systemid)
   systemname="${systemrole}-${uuid}"
   hostnamectl set-hostname ${systemname}
else
   uuid=$(uuidgen)
   echo $uuid > /opt/systemid
fi

while [ -f /opt/homeinserver ];
do
  homeinserver="$(cat /opt/homeinserver)"
  discoverserver="$(cat /opt/discoverserver)"
  export HostIP=$(ip route get ${discoverserver} | awk '{print $NF; exit}')
  curl "${homeinserver}/Report?hostIP=$HostIP&sysId=$uuid&clusterId={{cnf["clusterId"]}}&role=$systemrole" || echo "!!!Cannot report to cluster portal!!! Check the internet connection"
  echo "systemId:$uuid"
  echo "systemrole:$systemrole"
  echo "HostIP:$HostIP"
  if [ -f /opt/homeininterval ]
  then
    homeininterval="$(cat /opt/homeininterval)"
  else
    homeininterval=6
  fi
  sleep $homeininterval
done

