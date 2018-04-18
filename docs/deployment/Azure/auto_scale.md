# The following describe the procedures to autoscale a DLWorkspace cluster (i.e., automatically create/release VM when needed).

1. Download auto_scaler binary
   ```
   wget https://github.com/DLWorkspace/autoscaler/releases/download/v1.9.0/cluster-autoscaler
   ```

2. Setup azure running environment and login (via az login)

3. For the Azure machine types supported, please check the document at:
   ```
   src/ClusterBootstrap/templates/machine-types/azure/machineTypes.yaml
   ```

   A sample template is as follows. Please fill in additional worker VM SKUs if you need. 

   ```
    ---
    Standard_NC6:
    cpu: 6
    memoryInMb: 56339
    gpu: 1
    Standard_D3_v2:
    cpu: 4
    memoryInMb: 14339
  ```

4. Start auto_scaler:
   ```
    ./cluster-autoscaler --v=5 --stderrthreshold=error --logtostderr=true --cloud-provider=aztools --skip-nodes-with-local-storage=false --nodes=0:10:Standard_NC6 --nodes=0:10:Standard_D3_v2 --leader-elect=false --scale-down-enabled=true --kubeconfig=./deploy/kubeconfig/kubeconfig.yaml --expander=least-waste
   ```