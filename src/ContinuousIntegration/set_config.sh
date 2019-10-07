if [ ! -e ../ClusterBootstrap/config.yaml ];then
	if [ ! -e config.yaml.template ];then
		if [ ! -e ~/dltsdev-ci ];then
			git clone git@ssh.dev.azure.com:v3/dltsdev/DLTS/dltsdev-ci ~/dltsdev-ci
		fi;
		cp ~/dltsdev-ci/config.yaml.template .
	fi;
	python render_config.py
fi;