default_az_parameters = {
    "azure_cluster" : { 
        "infra_node_num": 1, 
        "worker_node_num": 2, 
        "nfs_node_num": 0, 
        "azure_location": "westus2",
        "infra_vm_size" : "Standard_D1_v2",
        "worker_vm_size": "Standard_NC6",
        "nfs_vm_size": "Standard_D1_v2",
        "vm_image" : "Canonical:UbuntuServer:18.04-LTS:18.04.201907221",
        "vm_storage_sku" : "Premium_LRS",
        "infra_local_storage_sz" : 1023,
        "worker_local_storage_sz" : 1023,
        "nfs_local_storage_sz" : 1023,
        "priority": "regular",
        "nfs_suffixes":[],
    },
}
