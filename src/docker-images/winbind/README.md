# This folder builds the winbind docker. 

winbind docker provide a restfulapi which can be used to inquire the uid, gid and groups id of a domain user. 

At the first time this docker image is started, a Microsoft Corp. domain username and password are required in order to join the Ad. This docker image is not designed to be launched automatically by default due to the security concern. 
If you would like to compromise and allow this docker image to be launched automatically, please modify run.sh and replace $DOMAINPASSWD $DOMAINUSER with the real username and password. 

It is suggestd to use the following command to launch this docker

docker run -d --restart=always --net=host -e DOMAINUSER='[username]' -e DOMAINPASSWD='[password]' winbind

By default, this docker image uses port 80 to provide restfulapi access. You may use -p [hostport]:80 to use anyother available port on the host. 
To access the winbind restfulapi 
http://[hostip:port]/domaininfo/GetUserId?userName=[alias]