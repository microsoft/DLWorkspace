# Frequently Asked Question During DL Workspace deployment. 

We are still prototyping the platform. Please report issues to the author, so that we can complete the document. 

1. DL workspace deployment environment.

   The deployment script of DL workspace makes specific assumption of the deployment environment, specifically as follows:

   1. The nodes (infrastructure and worker) are accessible by ssh and account "core". 
   2. "core" account is a member of sudo group and docker group, and can run sudo without password prompt. 
   3. The shell of "core" should be /bin/bash. Common environmental variable, such as $HOSTNAME, should be properly set. 

2. Common deployment issues. 
   
   1. The node cannot be accessed. You may also refer to (this)
      [https://docs.microsoft.com/en-us/azure/virtual-machines/linux/detailed-troubleshoot-ssh-connection] for Azure VM. 
      1. Symptons: "Could not resolve hostname <<...>>"
         Solution: enter the proper hostname of worker/infrastructure node. 
      2. Symptons: "connect to host <<...>> port 22: Connection refused"
         Solution: check if the host port has been properly openned. For Azure VM, check if it has been added to the correct network security group. 
      3. Symptoms: "Permission denied (publickey)."
         Solution: check if the correct public key has been inserted to core account on the node. 
      4. Symptoms: "Non-system drive" after OS installation for HP server. 
         Issue: HP boot controller designate RAID controller as the boot device for the hard drives. When the RAID is broken, the boot controller under RAID configuration fails to find MBR record, and fails to boot. 
         Solution: Break RAID in RAID controller, the boot can then proceeds. 
    2. Unable to start docker. 
       Please check if the "core" account has been added to docker group and sudo group. 
       You could try to remote to the node and run a docker command, (e.g. "docker ps"), or a sudo command (e.g., "sudo parted -ls"), to see if the command works. The sudo command should also not prompt you for password. See (this)[https://askubuntu.com/questions/192050/how-to-run-sudo-command-with-no-password] if you are prompt for password. 
    3. Incorrect shell. 
       When you remote to the node using "./deploy.py connect etcd/worker <num>", you should be prompt with "core@[hostname]". If you are prompt with "$", the core account uses /bin/sh, rather than /bin/bash. /bin/sh does not set some of the environmental variable, e.g., ($HOSTNAME) needed in our script, and may cause the script to fails. You may want to edit "/etc/passwd", and change the shell associated with "core" account to /bin/bash. 
    4. ECSDA host key issue when the cluster is deployed multiple times.
       You get a warning message: 
       ```
       Warning: the ECDSA host key for <<machine>> differs from the key for the IP address <<ip_address>>, 
       Offending key for IP in /home/<username>/.ssh/known_hosts
       Matching host key in /home/<username>/.ssh/known_hosts:79
       Are you sure you want to continue connecting (yes/no)? yes
       ```
       Issue: when machines redeployed, they got new host key, which differed from their prior host key, which triggers the warning above each time a remote machine is connected. 
       Solution: remove the hosts from /home/<username>/.ssh/known_hosts, you may also delete the file /home/<username>/.ssh/known_hosts.
    5. I see a web page of apache server, instead of DL Workspace. 
       Apache server may be default enabled on the installed node. Please use "sudo service apache2 stop" to disable the server. 
    6. I have a deployment failure. 
       Sometime, there is deployment glitches during script execution. Please try to execute the script again to see if the issue goes away. 

    7. 'docker pull' fails with error "layers from manifest don't match image configuration". 
        Please check the docker version of the 'pull' machine, the 'push' machine, and the docker register. It seems that this is caused by incompatible docker version. [See](https://github.com/docker/distribution/issues/1439)
   
    8. If you don't use domain, please don't add domain: "", this adds a "." to hostname by the script, and causes the scripts to fail.  

    9. In some ubuntu distributions, "NetworkManager" is enable and set dns name server to be "127.0.1.1". This is Ok on the host machine, but may cause issues in the container. Typically, if the container is not using host network and inherits dns name server from the host, the domain name will not be able to be resolved inside container. 

        If the container network is not working, please check /etc/resolv.conf. If there is a value of "127.0.1.1", run scripts:

        ```
        ./deploy.py runscriptonall ./scripts/disable_networkmanager.sh
        ```
   
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


