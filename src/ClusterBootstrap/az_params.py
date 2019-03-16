default_az_parameters = {
    "azure_cluster" : { 
        "infra_node_num": 1, 
        "worker_node_num": 2, 
        "azure_location": "westus2",
        "infra_vm_size" : "Standard_D1_v2",
        "worker_vm_size": "Standard_NC6",
        "vm_image" : "UbuntuLTS",
        "vm_storage_sku" : "Premium_LRS",        
        # "udp_port_ranges": ""
        # Use file_share_name to create Azure file share
        # "file_share_name" : "files",
    },
}
