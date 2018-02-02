# AWS EC2 platform deployment

1. Create VM
   ```
   python aws_tools.py vm create
   python aws_tools.py vm describe [Attempt to get public DNS name after VM start]
   python aws_tools.py genconfig [Generate config]
   python deploy.py hostname set [Set hostname of Azure VM according to public DNS]
   ```
   Information of the address created is saved to aws_cluster_file.yaml

2. Delete VM and clean up
   ```
   python aws_tools.py vm delete
   ```
