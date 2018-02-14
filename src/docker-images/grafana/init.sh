





declare -a dsarr=("collectd" "k8s" "WebUI")


dsflag="0";
while [[ dsflag -eq "0" ]]; do
	dsflag="1";
	for i in "${dsarr[@]}"
	do
	   if [[ $(curl -s http://admin:dlwsadmin@localhost:3000/api/datasources/name/$i | jq -r '.id') -eq 'null' ]]; then 
	   	dsflag="0";
	   	echo "creating datasource $i"
	   	curl -s -XPOST -H "Content-Type: application/json" -d @/var/lib/grafana/data/ds/$i.json http://admin:dlwsadmin@localhost:3000/api/datasources
	   else
	   	echo "existing datasource $i, skipping"
	   fi
	done
done





declare -a arr=("dlworkspace" "gpu" "jobgpuusage" "kubernetes-cluster" "kubernetes-pods" "app-metrics-web-monitoring")

flag="0";
while [[ flag -eq "0" ]]; do
	flag="1";
	for i in "${arr[@]}"
	do
	   if [[ $(curl -s http://admin:dlwsadmin@localhost:3000/api/dashboards/db/$i | jq -r '.dashboard.id') -eq 'null' ]]; then 
	   	flag="0";
	   	echo "creating dashboard $i"
	   	curl -s -XPOST -H "Content-Type: application/json" -d @/var/lib/grafana/data/dashboards/$i.json http://admin:dlwsadmin@localhost:3000/api/dashboards/db
	   else
	   	echo "existing dashboard $i, skipping"
	   fi
	done
done



#-H "Authorization: Bearer eyJrIjoiZDFhQ05YUWcwdU16U2l6THkzajZNTlZiVlUyU1lsaWIiLCJuIjoiZGx3cyIsImlkIjoxfQ==" 