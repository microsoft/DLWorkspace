#!/usr/bin/env python3

from unittest import TestCase
from mountpoint import *


class TestMountPoint(TestCase):
    def test_create_host_path_mountpoint(self):
        params = {
            "mountType": "hostPath",
            "mountPath": "/data",
            "hostPath": "/data/share/storage",
            "type": "Directory",
        }
        expected_dict = {
            "mountType": "hostPath",
            "mountPath": "/data",
            "hostPath": "/data/share/storage",
            "type": "Directory",
            "name": "data",
            "enabled": True,
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
            "subPath": "sub_dir",
            "server": "10.0.0.1",
            "path": "/data/share/storage",
        }
        expected_dict = {
            "mountType": "nfs",
            "mountPath": "/data",
            "subPath": "sub_dir",
            "server": "10.0.0.1",
            "path": "/data/share/storage",
            "name": "data",
            "enabled": True,
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

    def test_create_blobfuse_mountpoint(self):
        params = {
            "mountType": "blobfuse",
            "mountPath": "/mnt/blobfuse",
            "secreds": "secred-1",
            "containerName": "platform-container",
            "rootTmppath": "/mnt/local_fast_dir",
            "tmppath": "job1",
        }
        expected_dict = {
            "mountType": "blobfuse",
            "mountPath": "/mnt/blobfuse",
            "secreds": "secred-1",
            "containerName": "platform-container",
            "rootTmppath": "/mnt/local_fast_dir",
            "tmppath": "job1",
            "name": "mntblobfuse",
            "enabled": True,
        }
        mp = make_mountpoint(params)
        self.assertTrue(mp.is_valid())
        self.assertEqual(expected_dict, mp.to_dict())

        params = {
            "mountType": "blobfuse",
            "mountPath": "/mnt/blobfuse",
        }
        mp = make_mountpoint(params)
        self.assertFalse(mp.is_valid())
