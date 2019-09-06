# Frequently Asked Questions (FAQ) for Azure Cluster Deployment. 

Please refer to [this](../knownissues/Readme.md) for more general deployment issues. 

## After setup, I cannot visit the deployed DL Workspace portal. 

* Please wait a few minutes after the deployment script runs through to allow the portal container to be pulled and scheduled for execution. 

## sudo ./az_tools.py create failed.

* Check whether your subscription is correct. Always execute ```az account list | grep -A5 -B5 '"isDefault": true'``` to double check.

## Lost connection at the very first step of deploying infra node to Azure, or ```./deploy.py runscriptonall ./scripts/prepare_vm_disk.sh```

* Check whether hostname and source address in config.yaml are correctly set. Also try to make sure that you can ssh to the node.

## I cannot ssh to the node when my devbox is a physical server instead of a virtual one.

* Source IP address in config.yaml should probably be public IP, which could be derived by ```curl ifconfig.me```, instead of private IP you use to ssh to the devbox deriving from ```hostname -I```. If you cannot even ssh to the node after creating it, try to first set a new rule in Azure portal, allowing any source and destination IP, and set destination portal ranges to 22. Then ssh to the node, and type ```who``` to get the actual IP that is used to login to the node. Delete the temporary rule and in Networking setting, add <broaden IP>/16 to valid source IP, where <broaden IP> is the ```who``` IP with last two numbers set to 0. (e.g., 167.220.2.105 to 167.220.0.0/16)

## How do I know the node has been deployed?

* You can log into the master node: ```./deploy.py connect master```

## I could not build docker image/No such image/An image does not exist locally with the tag/The repository XXX does not have a Release file

* Check whether your docker is able to correctly resolve dns. First try on your devbox to ping a certain website, then do it in docker, such as `docker run -it busybox`,
	if the former setting can ping but not the later one, try to figure out whether your devbox need to visit public Internet via some private DNS. Then edit it in `/etc/docker/daemon.json` on your devbox. refer to [this article](https://medium.com/@faithfulanere/solved-docker-build-could-not-resolve-archive-ubuntu-com-apt-get-fails-to-install-anything-9ea4dfdcdcf2)
	use `systemd-resolve --status` to get more info about DNS if it is not managed by network-manager

## I can connect master/infra node, but the UI is not working (cannot access from browser), how to debug?

* Login to the master node, and use ```docker ps | grep web``` to get the ID corresponding to Web UI, then use ```docker logs --follow <WebUI ID>``` to figure out what happened.
  a better way is to use ```sudo docker logs --tail 100 --follow $(sudo docker ps | grep webui | awk '{print $1}') ``` since the ID would change everytime the docker is restarted.
  Everytime after modifying /etc/WebUI/userconfig.json etc., remember to restart that docker image: ```docker rm -f <WebUI ID>```

## finished all deployment, but not able to connect to master node via ```./deploy.py connect master```, ssh denied even with ``` ssh -i deploy/sshkey/id_rsa core@<infra node url>```.  

* Need to change owner ```sudo chown -R <usr_name>:<usr_name> DLWorkspace/```, can check ownership using ```ls -l```

## I can't execute Spark job on Azure. 

* The current default deployment procedure on Azure doesn't deploy HDFS/Spark. So Spark job execution is not available. 

## For 'az login', when I type in the device code, the web page prompt me again for the code. 

* It seems that sometime the browser (Edge, Chrome) cache another identity not intended to be used with az login. To get around, please start the browser in (in-private) or (incognito) mode, you may then enter the proper device code. 

## I have launched a job (e.g., TensorFlow-iPython-GPU). However, I am unable to access the endpoint with error 

    ```This site can’t be reached
    ....cloudapp.azure.com refused to connect.
    ```

    Please check the docker image of the job you are running. Sometime, the iPython (or SSH server) hasn't been properly started, which caused the endpoint to be not accessible.  

## I notice that my azure command is failing. 

Azure CLI may time out after inactivity. You may need to re-login via 'az login'. 

## Common configuration errors. 

* "merge_config( config["azure_cluster"], tmpconfig["azure_cluster"][config["azure_cluster"]["cluster_name"]], verbose )"
  Please check if the cluster_name used in azure_cluster is the same as the DL workspace cluster name.