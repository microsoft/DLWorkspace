#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging

import utils

logger = logging.getLogger(__file__)


@utils.case(dangerous=True)
def test_vc_quota_change(args):
    sku = "Standard_ND24rs"
    origin_spec = utils.get_resource_quota(args.rest, args.username)
    gpu_count = int(utils.walk_json(origin_spec, args.vc, "resourceQuota",
                                    "gpu", sku))
    assert gpu_count is not None

    target_gpu_count = gpu_count + 1
    quota_spec = {args.vc: {"resourceQuota": {"gpu": {sku: target_gpu_count}}}}
    with utils.ResourceQuota(args.rest, args.email, quota_spec):
        spec = utils.get_resource_quota(args.rest, args.username)
        r_quota = utils.walk_json(spec, args.vc, "resourceQuota")
        assert r_quota is not None

        gpu = utils.walk_json(r_quota, "gpu", sku)
        gpu_memory = utils.walk_json(r_quota, "gpu_memory", sku)
        cpu = utils.walk_json(r_quota, "cpu", sku)
        memory = utils.walk_json(r_quota, "memory", sku)

        r_metadata = utils.walk_json(spec, args.vc, "resourceMetadata")
        assert r_metadata is not None

        gpu_per_node = int(utils.walk_json(r_metadata, "gpu", sku))
        gpu_memory_per_node = \
            utils.to_byte(utils.walk_json(r_metadata, "gpu_memory", sku))
        cpu_per_node = int(utils.walk_json(r_metadata, "cpu", sku))
        memory_per_node = \
            utils.to_byte(utils.walk_json(r_metadata, "memory", sku))

        nodes = target_gpu_count / gpu_per_node
        assert gpu == target_gpu_count
        assert gpu_memory == int(nodes * gpu_memory_per_node)
        assert cpu == int(nodes * cpu_per_node)
        assert memory == int(nodes * memory_per_node)
