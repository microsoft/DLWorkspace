default_config_parameters = {
    "azure_cluster" : { 
        "infra_node_num": 1, 
        "worker_node_num": 2, 
        "azure_location": "westus2",
        "infra_vm_size" : "Standard_D1_v2",
        "worker_vm_size": "Standard_NC6",
        "vm_image" : "UbuntuLTS",
        "vm_storage_sku" : "Standard_LRS",        
        "vnet_range" : "192.168.0.0/16",        
        "default_admin_username" : "dlwsadmin",        
        "file_share_name" : "files",
        "storages" : ["journal"], 
        "azure_location" : ["westus"], 
        "journal": { # Journal storage 
            "name": "yummyjournal", 
            "sku": "Standard_GRS",
            "containers" : {
                "private" : {
                    "public-access": "off", 
                }, 
                "journal" : {
                    "public-access": "off", 
                }, 
            }, 
        },
    },
    
}