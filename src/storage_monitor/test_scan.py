"""
Tests for methods in scan.py
"""
import shutil
import platform

from .scan import *
from unittest import TestCase


SYSTEM = platform.system()
WINDOWS = "Windows"
LINUX = "Linux"

EMPTY_DIR_SIZE = 4096 if SYSTEM is LINUX else 0


class TestScan(TestCase):

    def setUp(self):
        self.test_dir = "test_dir"
        self.dir1 = os.path.join(self.test_dir, "dir1")
        self.dir2 = os.path.join(self.test_dir, "dir2")

        if os.path.exists(self.test_dir):
            self.tearDown()

        os.mkdir(self.test_dir)
        os.mkdir(self.dir1)
        os.mkdir(self.dir2)

        self.file2_1 = os.path.join(self.dir2, "file2_1")
        self.file2_2 = os.path.join(self.dir2, "file2_2")
        self.file1 = os.path.join(self.test_dir, "file1")

        self.file2_1_len = 8100
        self.file2_2_len = 500
        self.file1_len = 10240

        with open(self.file2_1, "wb") as f:
            f.write(b"a" * self.file2_1_len)

        with open(self.file2_2, "wb") as f:
            f.write(b"a" * self.file2_2_len)

        with open(self.file1, "wb") as f:
            f.write(b"a" * self.file1_len)

    def tearDown(self):
        try:
            shutil.rmtree(self.test_dir)
        except:
            print("Error while deleting directory %s" % self.test_dir)

    def test_create_node(self):
        file_node = create_node(self.file1)
        self.assertEqual(self.file1, file_node.path)
        self.assertFalse(file_node.isdir)
        self.assertEqual(self.file1_len, file_node.size)
        self.assertEqual(self.file1_len, file_node.subtree_size)
        self.assertEqual([], file_node.children)
        self.assertEqual(1, file_node.num_subtree_nodes)

        dir_node = create_node(self.dir1)
        self.assertEqual(self.dir1, dir_node.path)
        self.assertTrue(dir_node.isdir)
        self.assertEqual(EMPTY_DIR_SIZE, dir_node.size)
        self.assertEqual(EMPTY_DIR_SIZE, dir_node.subtree_size)
        self.assertEqual([], dir_node.children)
        self.assertEqual(1, dir_node.num_subtree_nodes)

    def test_invalid_create_tree(self):
        self.assertIsNone(create_tree("does_not_exist"))
        self.assertIsNone(create_tree(self.file1))

    def test_create_tree(self):
        test_dir = create_tree(self.test_dir)

        # Check test_dir
        self.assertEqual(self.test_dir, test_dir.path)
        self.assertTrue(test_dir.isdir)
        self.assertEqual(EMPTY_DIR_SIZE, test_dir.size)
        self.assertEqual(3 * EMPTY_DIR_SIZE + self.file2_1_len +
                         self.file2_2_len + self.file1_len,
                         test_dir.subtree_size)
        self.assertEqual(3, len(test_dir.children))
        self.assertEqual(6, test_dir.num_subtree_nodes)

        # Check dir1
        dir1 = test_dir.children[0]
        self.assertEqual(self.dir1, dir1.path)
        self.assertTrue(dir1.isdir)
        self.assertEqual(EMPTY_DIR_SIZE, dir1.size)
        self.assertEqual(EMPTY_DIR_SIZE, dir1.subtree_size)
        self.assertEqual(0, len(dir1.children))
        self.assertEqual(1, dir1.num_subtree_nodes)

        # Check dir2
        dir2 = test_dir.children[1]
        self.assertEqual(self.dir2, dir2.path)
        self.assertTrue(dir2.isdir)
        self.assertEqual(EMPTY_DIR_SIZE, dir2.size)
        self.assertEqual(EMPTY_DIR_SIZE + self.file2_1_len +
                         self.file2_2_len,
                         dir2.subtree_size)
        self.assertEqual(2, len(dir2.children))
        self.assertEqual(3, dir2.num_subtree_nodes)

        # Check file1
        file1 = test_dir.children[2]
        self.assertEqual(self.file1, file1.path)
        self.assertFalse(file1.isdir)
        self.assertEqual(self.file1_len, file1.size)
        self.assertEqual(self.file1_len, file1.subtree_size)
        self.assertEqual(0, len(file1.children))
        self.assertEqual(1, file1.num_subtree_nodes)

        # Check file2_1
        file2_1 = dir2.children[0]
        self.assertEqual(self.file2_1, file2_1.path)
        self.assertFalse(file2_1.isdir)
        self.assertEqual(self.file2_1_len, file2_1.size)
        self.assertEqual(self.file2_1_len, file2_1.subtree_size)
        self.assertEqual(0, len(file2_1.children))
        self.assertEqual(1, file2_1.num_subtree_nodes)

        # Check file2_2
        file2_2 = dir2.children[1]
        self.assertEqual(self.file2_2, file2_2.path)
        self.assertFalse(file2_2.isdir)
        self.assertEqual(self.file2_2_len, file2_2.size)
        self.assertEqual(self.file2_2_len, file2_2.subtree_size)
        self.assertEqual(0, len(file2_2.children))
        self.assertEqual(1, file2_2.num_subtree_nodes)

    def test_find_overweight_nodes(self):
        test_dir = create_tree(self.test_dir)
        overweight_nodes = find_overweight_nodes(test_dir, 10000)
        self.assertEqual(2, len(overweight_nodes))
        self.assertIn(test_dir, overweight_nodes)
        self.assertIn(test_dir.children[2], overweight_nodes)

    def test_find_expired_nodes(self):
        test_dir = create_tree(self.test_dir)
        expiry = datetime.now() - timedelta(days=1)

        file2_1 = test_dir.children[1].children[0]
        file2_1.atime = expiry - timedelta(days=1)

        expired_nodes = find_expired_nodes(test_dir, expiry)
        self.assertEqual(1, len(expired_nodes))
        self.assertIn(file2_1, expired_nodes)
