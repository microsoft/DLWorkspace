# Goolge compute platform deployment

1. Create VM 
   ```
   python gs_tools.py vm create
   ```

2. [Manual] Put the IP address of the GCE VM created 
3. Give VM a public accessible DNS entry (you will need to own the domain). 
4. Attach Google cloud compute username to SSH key generated (at ./deploy/sshkey/id_rsa.pub)