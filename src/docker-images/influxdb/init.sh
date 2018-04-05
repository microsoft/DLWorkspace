declare -a dsarr=("WebUI")
dsflag="0";
while [[ dsflag -eq "0" ]]; do
	dsflag="1";
	for i in "${dsarr[@]}"
	do
	   res=$(curl -s -POST "http://localhost:8086/query?db=$i" --data-urlencode 'q=show databases' | grep $i)

	   if [[ -z $res ]]; then
	   	dsflag="0";
	   	echo "creating datasource $i"
	   	curl -POST 'http://localhost:8086/query' --data-urlencode "q=CREATE DATABASE $i"
	   else
	   	echo "existing datasource $i, skipping"
	   fi
	done
done
