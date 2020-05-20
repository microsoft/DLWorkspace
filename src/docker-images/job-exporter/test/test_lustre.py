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


if __name__ == '__main__':
    unittest.main()
