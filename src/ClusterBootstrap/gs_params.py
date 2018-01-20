#!/usr/bin/python 
default_gs_parameters = {
    "gs_cluster" : { 
        "project": {
            "name": "yummyorder", 
            "id": "yummyorder-191922", 
        },
        # Spell out regional location used in Google cloud platform, see
        # https://cloud.google.com/storage/docs/bucket-locations
        "location_mapping": {
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
    },
}
