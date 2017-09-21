# Running scripts in DL Workspace. 

DL Workspace nodes are installed with python, so you can run both unix shell scripts/python scripts on the cluster. 
  
1. Run an inline command on all node. The following will execute a command on all cluster nodes and print the output. 

   ```
   ./deploy.py execonall [cmd ...] 
   ```

2. The following will execute a command on all cluster nodes without printing the output. 

   ```
   ./deploy.py doonall [cmd ...] 
   ```

3. The following will copy a script file (either shell script or python) to all cluster nodes and execute the script on remote node. 

   ```
   ./deploy.py runscriptonall [script] 
   ```

4. Access to DL workspace node. 

   Please use:
   
   ```
   python ./deploy.py connect master|etcd|worker [number]
   ```
   to connect to a particular Kubernetes master, etcd or worker node. You will log in as "core" account with sudo priviledge. 

5. You can use the following to directly run kubectl command on the cluster. 
   ```
   ./deploy.py kubectl <<command>> <<parameter>>
   ```
   
