#!/usr/bin/python 
default_gs_parameters = {
    "gs_cluster" : { 
        
        # Spell out regional location used in Google cloud platform, see
        # https://cloud.google.com/storage/docs/bucket-locations
        "location_mapping": {
            "westus": "us-west1-c", 
            "eastus": None, # or us-east4
        }, 
        "region_mapping": {
            "westus": "us-west1", 
            "eastus": None, # or us-east4
        }, 
        "sku_mapping": {
            # Google's multi_regional is associated with us, eu, asia, see
            # https://cloud.google.com/storage/docs/bucket-locations
            "Standard_LRS": "regional", 
            "Standard_GRS": "regional", # multi_regional
            "Standard_RAGRS": "regional", # multi_regional
        },
        "config": "~/code/config", 
            "infra_node_num": 1, 
            "worker_node_num": 0, 
            "gs_location": "us-west1-a",
            # pd-ssd: $0.17/GB, 10GB: $1.7/mo
            # local-ssd: $0.048/GB, 375GB, $18/mo
            # n1-standard1: $0.01/hr, preemptible, $7.3/mo
            "infra_vm_size" : "n1-standard-1 --boot-disk-type=pd-ssd --local-ssd interface=nvme --boot-disk-size=10GB", 
            "worker_vm_size": "n1-standard-1 --boot-disk-type=pd-ssd --local-ssd interface=nvme --boot-disk-size=10GB",
            "vm_image" : "--image-project ubuntu-os-cloud --image-family ubuntu-1604-lts  --preemptible",
            "vm_storage_sku" : "--local-ssd interface=nvme",        
            "vnet_range" : "192.168.0.0/16",        
            "default_admin_username" : "dlwsadmin", 
    },
}
