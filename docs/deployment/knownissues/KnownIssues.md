# Known issues. 

We are still prototyping the platform. Please report issues to the author, so that we can complete the document. 

1. 'docker pull' fails with error "layers from manifest don't match image configuration". 
   Please check the docker version of the 'pull' machine, the 'push' machine, and the docker register. It seems that this is caused by incompatible docker version. [See](https://github.com/docker/distribution/issues/1439)
   
2. If you don't use domain, please don't add domain: "", this adds a "." to hostname by the script, and causes the scripts to fail.  

3. In some ubuntu distributions, "NetworkManager" is enable and set dns name server to be "127.0.1.1". This is Ok on the host machine, but may cause issues in the container. Typically, if the container is not using host network and inherits dns name server from the host, the domain name will not be able to be resolved inside container. 
   If the container network is not working, please check /etc/resolv.conf. If the value is "127.0.1.1", please follow the below instructions to fix:
   
   NetworkManager is the program which (via the resolvconf utility) inserts address 127.0.1.1 into resolv.conf. NM inserts that address if an only if it is configured to start an instance of the dnsmasq program to serve as a local forwarding nameserver. That dnsmasq instance listens for queries at address 127.0.1.1.
   If you do not want to use a local forwarding nameserver then configure NetworkManager not to start a dnsmasq instance and not to insert that address. In /etc/NetworkManager/NetworkManager.conf comment out the line dns=dnsmasq
   ```
   sudo vi /etc/NetworkManager/NetworkManager.conf
   [main]:q
   plugins=ifupdown,keyfile,ofono
   #dns=dnsmasq
   ```
   and restart the NetworkManager service.
   ```
   sudo service network-manager restart
   ```
