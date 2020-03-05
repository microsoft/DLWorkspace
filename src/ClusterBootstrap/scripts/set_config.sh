config=$(echo "$1" | awk '{print tolower($0)}')
# echo $config
if [ ! -e ../template/${config}_config.yaml.template ];then
	if [ ! -e ~/dltsdev-ci ];then
		git clone git@ssh.dev.azure.com:v3/dltsdev/DLTS/dltsdev-ci ~/dltsdev-ci
	fi;
	cp ~/dltsdev-ci/${config}_config.yaml.template ../template/
fi;
cd ..
python3 render_config.py ${config} $2