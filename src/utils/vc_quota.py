#!/usr/bin/env python3
import json


def vc_value_str(config, ratio_dict):
    if "worker_sku_cnt" not in config or "sku_mapping" not in config:
        print(
            "Warning: no default value would be added to VC table. Need to manually specify"
        )
        return "", "", [], ""

    worker_sku_cnt, sku_mapping = config["worker_sku_cnt"], config[
        "sku_mapping"]
    quota_dict = {}
    old_meta = {}
    resource_quota = {"cpu": {}, "memory": {}, "gpu": {}, "gpu_memory": {}}
    for sku, cnt in worker_sku_cnt.items():
        gpu_type = sku_mapping.get(sku, {}).get("gpu-type", "None")
        num_gpu_per_node = sku_mapping.get(sku, {}).get("gpu", 0)
        quota_dict[gpu_type] = quota_dict.get(gpu_type,
                                              0) + cnt * num_gpu_per_node
        old_meta[gpu_type] = {"num_gpu_per_node": num_gpu_per_node}
        sku_name_in_map = sku if sku in sku_mapping else ""
        meta_tmp = sku_mapping.get(sku_name_in_map, {})
        for r_type in resource_quota.keys():
            resource_quota[r_type][
                sku_name_in_map] = resource_quota[r_type].get(
                    sku_name_in_map, 0) + meta_tmp.get(r_type, 0) * cnt

    for r_type in ["cpu", "memory"]:
        for sku, val in resource_quota[r_type].items():
            resource_quota[r_type][sku] *= config.get("schedulable_ratio", 0.9)

    # default value of quota and metadata are based on the assumption that there's only one default VC, this is not reasonable, and
    # these 2 fields would also finally get removed
    quota = json.dumps(quota_dict, separators=(",", ":"))
    metadata = json.dumps(old_meta, separators=(",", ":"))

    # TODO use cluster_resource.py to simplify code:
    # res_obj = ClusterResource(resource_quota), and directly multiply the ratio.
    res_quota = {}
    for vc, ratio in ratio_dict.items():
        res_quota_dict = {}
        for res, res_q in resource_quota.items():
            tmp_res_quota = {}
            for sku, cnt in res_q.items():
                cnt_p = cnt * ratio
                if "memory" in res:
                    cnt_p = '{}Gi'.format(cnt)
                tmp_res_quota[sku] = cnt_p
            res_quota_dict[res] = tmp_res_quota
        res_quota[vc] = json.dumps(res_quota_dict, separators=(",", ":"))

    res_meta_dict = {}
    for r_type in ["cpu", "memory", "gpu", "gpu_memory"]:
        tmp_res_meta = {}
        for sku in worker_sku_cnt:
            sku_name_in_map = sku if sku in sku_mapping else ""
            pernode_cnt = sku_mapping.get(sku_name_in_map, {}).get(r_type, 0)
            if "memory" in r_type:
                pernode_cnt = '{}Gi'.format(pernode_cnt)
            tmp_res_meta[sku_name_in_map] = {"per_node": pernode_cnt}
            if r_type in ["cpu", "memory"]:
                tmp_res_meta[sku_name_in_map]["schedulable_ratio"] = 0.9
            if r_type == "gpu":
                tmp_res_meta[sku_name_in_map]["gpu_type"] = sku_mapping.get(
                    sku_name_in_map, {}).get("gpu-type", "None")
        res_meta_dict[r_type] = tmp_res_meta
    res_meta = json.dumps(res_meta_dict, separators=(",", ":"))
    return quota, metadata, res_quota, res_meta
