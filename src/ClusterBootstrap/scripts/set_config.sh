if [ ! -e ../template/config.yaml.template ];then
	if [ ! -e ~/dltsdev-ci ];then
		git clone git@ssh.dev.azure.com:v3/dltsdev/DLTS/dltsdev-ci ~/dltsdev-ci
	fi;
	cp ~/dltsdev-ci/config.yaml.template ../template/
fi;
cd ..
python render_config.py
