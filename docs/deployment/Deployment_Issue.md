# Common Deployment Issues of DL workspace cluster

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
    2. Unable to start docker. 
       Please check if the "core" account has been added to docker group and sudo group. 
       You could try to remote to the node and run a docker command, (e.g. "docker ps"), or a sudo command (e.g., "sudo parted -ls"), to see if the command works. The sudo command should also not prompt you for password. See (this)[https://askubuntu.com/questions/192050/how-to-run-sudo-command-with-no-password] if you are prompt for password. 
    3. Incorrect shell. 
       When you remote to the node using "./deploy.py connect etcd/worker <num>", you should be prompt with "core@[hostname]". If you are prompt with "$", the core account uses /bin/sh, rather than /bin/bash. /bin/sh does not set some of the environmental variable, e.g., ($HOSTNAME) needed in our script, and may cause the script to fails. You may want to edit "/etc/passwd", and change the shell associated with "core" account to /bin/bash. 
