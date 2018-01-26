# Goolge compute platform deployment

1. Create addresses for infrastructure node. 
   ```
   python gs_tools.py address create
   ```
   Information of the address created is saved to gs_cluster_file.yaml
   Please find the address and put it into your DNS provider, say dlwsg-infra0?.freeddns.org

2. Create VM and generate configuration
   ```
   python gs_tools.py vm create
   python gs_tools.py genconfig
   python gs_tools.py vm prepare
   ```
3. You should be able to connect to the VM created at this moment. Execute the following script ONCE to prepare the VM. 
   ```
   ./deploy.py --verbose --sudo runscriptonall ./scripts/platform/gce/configure-vm.sh

   ```
3. Give VM a public accessible DNS entry (you will need to own the domain). 
4. Attach Google cloud compute username to SSH key generated (at ./deploy/sshkey/id_rsa.pub)