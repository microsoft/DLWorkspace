#!/usr/bin/env python3

import os
import sys
import unittest

import base

sys.path.append(os.path.abspath("../src/"))

import lustre


class TestLustre(base.TestBase):
    def test_group_content_singleline(self):
        content = "health_check=healthy"
        ret = lustre.group_content(content)
        self.assertEqual("health_check=healthy", ret.get("health_check"))


    def test_group_content_multilines(self):
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
obdfilter.lustrefs-OST0002.stats=
snapshot_time             1589930459.810001740 secs.nsecs
read_bytes                689345 samples [bytes] 4096 4194304 1285617164288
write_bytes               519702 samples [bytes] 8 4194304 2178849904953
setattr                   8 samples [reqs]
punch                     24 samples [reqs]
sync                      171 samples [reqs]
destroy                   3166048 samples [reqs]
create                    994 samples [reqs]
statfs                    241330 samples [reqs]
get_info                  1 samples [reqs]
set_info                  257 samples [reqs]
"""
        ret = lustre.group_content(content)
        self.assertEqual(
            """obdfilter.lustrefs-OST0001.stats=
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
set_info                  262 samples [reqs]""",
            ret.get("obdfilter.lustrefs-OST0001.stats"))
        self.assertEqual(
            """obdfilter.lustrefs-OST0002.stats=
snapshot_time             1589930459.810001740 secs.nsecs
read_bytes                689345 samples [bytes] 4096 4194304 1285617164288
write_bytes               519702 samples [bytes] 8 4194304 2178849904953
setattr                   8 samples [reqs]
punch                     24 samples [reqs]
sync                      171 samples [reqs]
destroy                   3166048 samples [reqs]
create                    994 samples [reqs]
statfs                    241330 samples [reqs]
get_info                  1 samples [reqs]
set_info                  257 samples [reqs]""",
            ret.get("obdfilter.lustrefs-OST0002.stats")
        )


if __name__ == '__main__':
    unittest.main()
