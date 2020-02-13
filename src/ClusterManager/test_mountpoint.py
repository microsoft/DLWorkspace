#!/usr/bin/env python3

from unittest import TestCase
from mountpoint import *


class TestMountPoint(TestCase):
    def test_create_host_path_mountpoint(self):
        params = {
            "mountType": "hostPath",
            "mountPath": "/data",
            "hostPath": "/data/share/storage",
        }
        expected_dict = {
            "mountType": "hostPath",
            "mountPath": "/data",
            "hostPath": "/data/share/storage",
            "name": "data",
            "enabled": True,
            "vc": None
        }
        mp = make_mountpoint(params)
        self.assertTrue(mp.is_valid())
        self.assertEqual(expected_dict, mp.to_dict())

        params = {
            "mountType": "hostPath",
            "mountPath": "/data",
        }
        mp = make_mountpoint(params)
        self.assertFalse(mp.is_valid())

    def test_create_nfs_mountpoint(self):
        params = {
            "mountType": "nfs",
            "mountPath": "/data",
            "server": "10.0.0.1",
            "path": "/data/share/storage",
        }
        expected_dict = {
            "mountType": "nfs",
            "mountPath": "/data",
            "server": "10.0.0.1",
            "path": "/data/share/storage",
            "name": "data",
            "enabled": True,
            "vc": None
        }
        mp = make_mountpoint(params)
        self.assertTrue(mp.is_valid())
        self.assertEqual(expected_dict, mp.to_dict())

        params = {
            "mountType": "nfs",
            "mountPath": "/data",
            "path": "/data/share/storage",
        }
        mp = make_mountpoint(params)
        self.assertFalse(mp.is_valid())

    def test_create_bad_mountpoint(self):
        params = {
            "mountType": "nfs_bad",
            "mountPath": "/data",
            "server": "10.0.0.1",
            "path": "/data/share/storage",
        }
        mp = make_mountpoint(params)
        self.assertIsNone(mp)
