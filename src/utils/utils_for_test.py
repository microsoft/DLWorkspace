#!/usr/bin/env python3


def get_test_quota():
    quota = {
        "cpu": {
            "Standard_D2s_v3": 4,
            "Standard_ND24rs": 72,
        },
        "memory": {
            "Standard_D2s_v3": "16Gi",
            "Standard_ND24rs": "1344Gi",
        },
        "gpu": {
            "Standard_ND24rs": 12,
        },
    }
    return quota


def get_test_metadata():
    metadata = {
        "cpu": {
            "Standard_D2s_v3": {
                "per_node": 2,
                "schedulable_ratio": 0.9,
            },
            "Standard_ND24rs": {
                "per_node": 24,
                "schedulable_ratio": 0.9,
            },
        },
        "memory": {
            "Standard_D2s_v3": {
                "per_node": "8Gi",
                "schedulable_ratio": 0.9,
            },
            "Standard_ND24rs": {
                "per_node": "448Gi",
                "schedulable_ratio": 0.9,
            },
        },
        "gpu": {
            "Standard_ND24rs": {
                "per_node": 4,
                "gpu_type": "P40",
                "schedulable_ratio": 1,
            },
        },
    }
    return metadata
