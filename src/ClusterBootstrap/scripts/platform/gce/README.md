# Goolge compute platform deployment

1. Create addresses for infrastructure node. 
   ```
   python gs_tools.py address create
   ```
   Information of the address created is saved to gs_cluster_file.yaml
   Please find the address and put it into your DNS provider, say dlwsg-infra0?.freeddns.org. Please write domain information to network:domain entry in config.yaml. The infrastructure node should have name: clustername-infra??, where ?? is from 01..99.

2. Create VM and generate configuration
   ```
   python gs_tools.py vm create
   python gs_tools.py genconfig
   python gs_tools.py vm prepare
   ```
3. You should be able to connect to the VM created at this moment. Execute the startup script. 
   ```
   ./deploy.py --verbose scriptblocks azure_uncordon
   ```
