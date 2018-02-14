#!/usr/bin/python 
default_aws_parameters = {
    "aws_cluster" : { 
        
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
            "aws_location": "us-west-2",
            # pd-ssd: $0.17/GB, 10GB: $1.7/mo
            # local-ssd: $0.048/GB, 375GB, $18/mo
            # n1-standard1: $0.01/hr, preemptible, $7.3/mo
            "infra_vm_size" : "t2.medium", 
            "worker_vm_size": "t2.medium",
            # Ubuntu Server 16.04 LTS (HVM), SSD Volume Type - ami-1ee65166
            "vm_image" : "ami-1ee65166",
            "vm_storage_sku" : """--block-device-mapping '[ { \"DeviceName\": \"/dev/sda1\", \"Ebs\": { \"VolumeSize\": 32 } } ]' """,        
            "vnet_range" : "192.168.0.0/16",        
            "default_admin_username" : "ubuntu", 
    },
}