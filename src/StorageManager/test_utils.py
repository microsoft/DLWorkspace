#!/usr/bin/env python3

import os

from pathlib import Path
from unittest import TestCase
from utils import keep_ancestor_paths, post_order_delete


class TestUtils(TestCase):
    def test_keep_ancestor_paths(self):
        paths = [
            "/data/share/storage/local", "/data/share/work",
            "/data/share/storage", "/data/share/storage/users/local"
            "/data/share/storage/users"
        ]

        ancestors = keep_ancestor_paths(paths)
        self.assertEqual(2, len(ancestors))
        self.assertEqual(["/data/share/storage", "/data/share/work"], ancestors)

    def test_post_order_delete(self):
        Path("/tmp/test_dir").mkdir()
        Path("/tmp/test_dir/subdir1").mkdir()
        Path("/tmp/test_dir/subdir2").mkdir()
        Path("/tmp/test_dir/file1.txt").touch()
        Path("/tmp/test_dir/subdir2/file2.txt").touch()
        Path("/tmp/test_dir/subdir2/file3.txt").touch()

        # Do nothing if the path does not exist
        post_order_delete("/tmp/test_dir/non-existent")

        # Delete a file
        self.assertTrue(os.path.exists("/tmp/test_dir/file1.txt"))
        self.assertFalse(os.path.isdir("/tmp/test_dir/file1.txt"))
        post_order_delete("/tmp/test_dir/file1.txt")
        self.assertFalse(os.path.exists("/tmp/test_dir/file1.txt"))

        # Delete a directory
        self.assertTrue(os.path.exists("/tmp/test_dir"))
        self.assertTrue(os.path.isdir("/tmp/test_dir"))
        post_order_delete("/tmp/test_dir")
        self.assertFalse(os.path.exists("/tmp/test_dir"))
