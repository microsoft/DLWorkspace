#!/usr/bin/env python3

import os
import sys
import unittest

import base

sys.path.append(os.path.abspath("../src/"))

import lustre


def get_a_lmetric(name, pattern):
    return lustre.LustreMetric(name, pattern, "dummy", "dummy", "dummy")


class TestLustre(base.TestBase):
    def test_parse_lmetric_single(self):
        content = "health_check=healthy"

        lmetric = get_a_lmetric("health_check", "health_check")
        gauge = lustre.parse_lmetric(content, lmetric)
        self.assertEqual("lustre_health_check", gauge.name)
        self.assertEqual(1, len(gauge.samples))
        self.assertEqual(1, gauge.samples[0].value)
        self.assertEqual({"server": "dummy",
                          "role": "dummy",
                          "component": "N/A",
                          "target": "N/A"}, gauge.samples[0].labels)

    def test_parse_lmetric_stats(self):
        content = """obdfilter.lustrefs-OST0001.stats=
snapshot_time             1589930459.809922337 secs.nsecs
read_bytes                704739 samples [bytes] 4096 4194304 1292415627264
write_bytes               521010 samples [bytes] 8 4194304 2179270529672
setattr                   5 samples [reqs]
punch                     6 samples [reqs]
sync                      171 samples [reqs]
destroy                   3165939 samples [reqs]
create                    1037 samples [reqs]
statfs                    241361 samples [reqs]
get_info                  1 samples [reqs]
set_info                  262 samples [reqs]
"""
        lmetric = get_a_lmetric("stats_total", "obdfilter.*.stats")
        gauge = lustre.parse_lmetric(content, lmetric)
        self.assertEqual("lustre_stats_total", gauge.name)
        self.assertEqual(8, len(gauge.samples))
        expected_values = {
            "setattr": 5,
            "punch": 6,
            "sync": 171,
            "destroy": 3165939,
            "create": 1037,
            "statfs": 241361,
            "get_info": 1,
            "set_info": 262,
        }
        for sample in gauge.samples[:8]:
            operation = sample.labels.get("operation")
            self.assertEqual(expected_values[operation], sample.value)
            self.assertEqual({"server": "dummy",
                              "role": "dummy",
                              "operation": operation,
                              "component": "obdfilter",
                              "target": "lustrefs-OST0001"}, sample.labels)

        expected_tuples = {
            "read_samples_total": ("read_bytes", 704739),
            "read_bytes_minimum": ("read_bytes", 4096),
            "read_bytes_maximum": ("read_bytes", 4194304),
            "read_bytes_total": ("read_bytes", 1292415627264),
            "write_samples_total": ("write_bytes", 521010),
            "write_bytes_minimum": ("write_bytes", 8),
            "write_bytes_maximum": ("write_bytes", 4194304),
            "write_bytes_total": ("write_bytes", 2179270529672),
        }

        for metric, expected_tuple in expected_tuples.items():
            operation, expected_value = expected_tuple
            lmetric = get_a_lmetric(metric, "obdfilter.*.stats")
            gauge = lustre.parse_lmetric(content, lmetric)
            self.assertEqual(1, len(gauge.samples))
            sample = gauge.samples[0]
            self.assertEqual(expected_value, sample.value)
            self.assertEqual({"server": "dummy",
                              "role": "dummy",
                              "operation": operation,
                              "component": "obdfilter",
                              "target": "lustrefs-OST0001"}, sample.labels)

    def test_parse_lustre_fsnames(self):
        content = """
192.168.0.2:/data/share on /host-fs/mntdlts/nfs/somepath type nfs4 (rw,relatime,vers=4.2,rsize=8192,wsize=1048576,namlen=255,hard,proto=tcp,timeo=14,retrans=2,sec=sys,clientaddr=xxxx,local_lock=none,addr=xxxx)
192.168.0.1@tcp:/lustrefs on /host-fs/mntdlts/lustre type lustre (rw,flock,lazystatfs)
/dev/sdc on /lustre type lustre (ro,context=system_u:object_r:fsadm_tmp_t:s0,svname=lustrefs-MDT0000,mgs,osd=osd-ldiskfs,user_xattr,errors=remount-ro)
        """
        fsnames = lustre.parse_lustre_fsnames(content)
        self.assertEqual(1, len(fsnames))
        self.assertEqual("lustrefs", fsnames[0])

        # Ignore if there is no lustre mount
        content = """
192.168.0.2:/data/share on /host-fs/mntdlts/nfs/somepath type nfs4 (rw,relatime,vers=4.2,rsize=8192,wsize=1048576,namlen=255,hard,proto=tcp,timeo=14,retrans=2,sec=sys,clientaddr=xxxx,local_lock=none,addr=xxxx)
/dev/sdc on /lustre type lustre (ro,context=system_u:object_r:fsadm_tmp_t:s0,svname=lustrefs-MDT0000,mgs,osd=osd-ldiskfs,user_xattr,errors=remount-ro)
        """
        fsnames = lustre.parse_lustre_fsnames(content)
        self.assertEqual(0, len(fsnames))

    def test_parse_lustre_pool_names(self):
        content = """
Pools from lustrefs:
lustrefs.hdd
lustrefs.nvme
lustrefs.test
        """
        pool_names = lustre.parse_lustre_pool_names(content, "lustrefs")
        self.assertEqual(3, len(pool_names))
        self.assertEqual("lustrefs.hdd", pool_names[0])
        self.assertEqual("lustrefs.nvme", pool_names[1])
        self.assertEqual("lustrefs.test", pool_names[2])

        content = """
Pools from lustrefs:
        """
        pool_names = lustre.parse_lustre_pool_names(content, "lustrefs")
        self.assertEqual(0, len(pool_names))

    def test_parse_lustre_pool_size(self):
        content = """
UUID                   1K-blocks        Used   Available Use% Mounted on
lustrefs-MDT0000_UUID     33285776     1187236    28954456   4% /mntdlts/lustre/[MDT:0]
lustrefs-MDT0001_UUID     33285776       67620    30074072   1% /mntdlts/lustre/[MDT:1]
lustrefs-MDT0002_UUID     33285776       67776    30073916   1% /mntdlts/lustre/[MDT:2]
lustrefs-MDT0003_UUID     33285776       67624    30074068   1% /mntdlts/lustre/[MDT:3]
lustrefs-OST0000_UUID  27853187524 25589008644  1982305268  93% /mntdlts/lustre/[OST:0]
lustrefs-OST0001_UUID  27853187524 25607584292  1963729620  93% /mntdlts/lustre/[OST:1]
lustrefs-OST0002_UUID  27853187524 25598612920  1972700992  93% /mntdlts/lustre/[OST:2]
lustrefs-OST0003_UUID  27853187524 25612460316  1958853596  93% /mntdlts/lustre/[OST:3]

filesystem_summary:  111412750096 102407666172  7877589476  93% /mntdlts/lustre

        """
        pool_size = lustre.parse_lustre_pool_size(content)
        self.assertIsNotNone(pool_size)
        total, used, avail = pool_size
        self.assertEqual(111412750096, total)
        self.assertEqual(102407666172, used)
        self.assertEqual(7877589476, avail)


if __name__ == '__main__':
    unittest.main()
