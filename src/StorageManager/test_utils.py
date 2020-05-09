#!/usr/bin/env python3

from unittest import TestCase
from utils import keep_ancestor_paths


class TestPathTree(TestCase):
    def test_keep_ancestor_paths(self):
        paths = [
            "/data/share/storage/local",
            "/data/share/work",
            "/data/share/storage",
            "/data/share/storage/users/local"
            "/data/share/storage/users"
        ]

        ancestors = keep_ancestor_paths(paths)
        self.assertEqual(2, len(ancestors))
        self.assertEqual(["/data/share/storage", "/data/share/work"], ancestors)
