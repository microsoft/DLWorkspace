import os
import platform

from datetime import datetime, timedelta
from unittest import TestCase
from mock import patch
from path_tree import PathTree
from testcase_utils import DummyNodeStat


SYSTEM = platform.system()
WINDOWS = "Windows"
LINUX = "Linux"

EMPTY_DIR_SIZE = 4096 if SYSTEM is LINUX else 0

TEST_DIR = "test_dir"
DIR1 = os.path.join(TEST_DIR, "dir1")
DIR2 = os.path.join(TEST_DIR, "dir2")
FILE2_1 = os.path.join(DIR2, "file2_1")
FILE2_1_LEN = 8100
FILE2_2 = os.path.join(DIR2, "file2_2")
FILE2_2_LEN = 500
FILE1 = os.path.join(TEST_DIR, "file1")
FILE1_LEN = 10240


def stat_side_effect(value):
    node = DummyNodeStat()

    if value == TEST_DIR:
        node.st_size = EMPTY_DIR_SIZE
    elif value == DIR1:
        node.st_size = EMPTY_DIR_SIZE
    elif value == DIR2:
        node.st_size = EMPTY_DIR_SIZE
        node.st_atime -= 3 * DAY
    elif value == FILE2_1:
        node.st_size = FILE2_1_LEN
        node.st_atime -= 2 * DAY
    elif value == FILE2_2:
        node.st_size = FILE2_2_LEN
        node.st_atime -= 4 * DAY
    elif value == FILE1:
        node.st_size = FILE1_LEN
        node.st_atime -= 3 * DAY

    return node


def isdir_side_effect(value):
    return value in [TEST_DIR, DIR1, DIR2]


def listdir_side_effect(value):
    if value == TEST_DIR:
        return ["dir1", "dir2", "file1"]
    elif value == DIR1:
        return []
    elif value == DIR2:
        return ["file2_1", "file2_2"]
    return []


class TestPathTree(TestCase):
    def test_create_invalid_path_tree(self):
        config = {
            "path": "dummy",
            "overweight_threshold": 1000,
            "expiry_days": 1
        }
        tree = PathTree(config)
        tree.create_tree()
        self.assertEqual(None, tree.root)

    @patch("os.listdir")
    @patch("os.path.islink")
    @patch("os.path.isdir")
    @patch("os.stat")
    def test_create_path_tree(self,
                              mock_stat,
                              mock_isdir,
                              mock_islink,
                              mock_listdir):
        mock_stat.side_effect = stat_side_effect
        mock_isdir.side_effect = isdir_side_effect
        mock_islink.return_value = False
        mock_listdir.side_effect = listdir_side_effect

        config = {
            "path": TEST_DIR,
            "overweight_threshold": 1000,
            "expiry_days": 1
        }
        tree = PathTree(config)
        tree.create_tree()

        # Check test_dir
        test_dir = tree.root
        self.assertIsNotNone(test_dir)
        self.assertEqual(TEST_DIR, test_dir.path)
        self.assertTrue(test_dir.isdir)
        self.assertEqual(EMPTY_DIR_SIZE, test_dir.size)
        self.assertEqual(3 * EMPTY_DIR_SIZE + FILE2_1_LEN +
                         FILE2_2_LEN + FILE1_LEN,
                         test_dir.subtree_size)
        self.assertEqual(datetime(2019, 11, 19, 14, 39, 27),
                         test_dir.atime)
        self.assertEqual(datetime(2019, 11, 19, 14, 39, 27),
                         test_dir.subtree_atime)
        self.assertEqual(1000, test_dir.uid)
        self.assertEqual(1000, test_dir.gid)
        self.assertEqual("", test_dir.owner)
        self.assertEqual(6, test_dir.num_subtree_nodes)
        self.assertEqual(3, len(test_dir.children))

        # Check dir1
        dir1 = test_dir.children[0]
        self.assertIsNotNone(dir1)
        self.assertEqual(DIR1, dir1.path)
        self.assertTrue(dir1.isdir)
        self.assertEqual(EMPTY_DIR_SIZE, dir1.size)
        self.assertEqual(EMPTY_DIR_SIZE, dir1.subtree_size)
        self.assertEqual(datetime(2019, 11, 19, 14, 39, 27),
                         dir1.atime)
        self.assertEqual(datetime(2019, 11, 19, 14, 39, 27),
                         dir1.subtree_atime)
        self.assertEqual(1000, dir1.uid)
        self.assertEqual(1000, dir1.gid)
        self.assertEqual("", dir1.owner)
        self.assertEqual(1, dir1.num_subtree_nodes)
        self.assertEqual(0, len(dir1.children))

        # Check dir2
        dir2 = test_dir.children[1]
        self.assertIsNotNone(dir2)
        self.assertEqual(DIR2, dir2.path)
        self.assertTrue(dir2.isdir)
        self.assertEqual(EMPTY_DIR_SIZE, dir2.size)
        self.assertEqual(EMPTY_DIR_SIZE + FILE2_1_LEN + FILE2_2_LEN,
                         dir2.subtree_size)
        self.assertEqual(datetime(2019, 11, 19, 14, 39, 27) - timedelta(days=3),
                         dir2.atime)
        self.assertEqual(datetime(2019, 11, 19, 14, 39, 27) - timedelta(days=2),
                         dir2.subtree_atime)
        self.assertEqual(1000, dir2.uid)
        self.assertEqual(1000, dir2.gid)
        self.assertEqual("", dir2.owner)
        self.assertEqual(3, dir2.num_subtree_nodes)
        self.assertEqual(2, len(dir2.children))

        # Check file2_1
        file2_1 = dir2.children[0]
        self.assertIsNotNone(file2_1)
        self.assertEqual(FILE2_1, file2_1.path)
        self.assertFalse(file2_1.isdir)
        self.assertEqual(FILE2_1_LEN, file2_1.size)
        self.assertEqual(FILE2_1_LEN, file2_1.subtree_size)
        self.assertEqual(datetime(2019, 11, 19, 14, 39, 27) - timedelta(days=2),
                         file2_1.atime)
        self.assertEqual(datetime(2019, 11, 19, 14, 39, 27) - timedelta(days=2),
                         file2_1.subtree_atime)
        self.assertEqual(1000, file2_1.uid)
        self.assertEqual(1000, file2_1.gid)
        self.assertEqual("", file2_1.owner)
        self.assertEqual(1, file2_1.num_subtree_nodes)
        self.assertEqual(0, len(file2_1.children))

        # Check file2_2
        file2_2 = dir2.children[1]
        self.assertIsNotNone(file2_2)
        self.assertEqual(FILE2_2, file2_2.path)
        self.assertFalse(file2_2.isdir)
        self.assertEqual(FILE2_2_LEN, file2_2.size)
        self.assertEqual(FILE2_2_LEN, file2_2.subtree_size)
        self.assertEqual(datetime(2019, 11, 19, 14, 39, 27) - timedelta(days=4),
                         file2_2.atime)
        self.assertEqual(datetime(2019, 11, 19, 14, 39, 27) - timedelta(days=4),
                         file2_2.subtree_atime)
        self.assertEqual(1000, file2_2.uid)
        self.assertEqual(1000, file2_2.gid)
        self.assertEqual("", file2_2.owner)
        self.assertEqual(1, file2_2.num_subtree_nodes)
        self.assertEqual(0, len(file2_2.children))

        # Check file1
        file1 = test_dir.children[2]
        self.assertIsNotNone(file1)
        self.assertEqual(FILE1, file1.path)
        self.assertFalse(file1.isdir)
        self.assertEqual(FILE1_LEN, file1.size)
        self.assertEqual(FILE1_LEN, file1.subtree_size)
        self.assertEqual(datetime(2019, 11, 19, 14, 39, 27) - timedelta(days=3),
                         file1.atime)
        self.assertEqual(datetime(2019, 11, 19, 14, 39, 27) - timedelta(days=3),
                         file1.subtree_atime)
        self.assertEqual(1000, file1.uid)
        self.assertEqual(1000, file1.gid)
        self.assertEqual("", file1.owner)
        self.assertEqual(1, file1.num_subtree_nodes)
        self.assertEqual(0, len(file1.children))

    @patch("os.listdir")
    @patch("os.path.islink")
    @patch("os.path.isdir")
    @patch("os.stat")
    def test_find_overweight_nodes(self,
                                   mock_stat,
                                   mock_isdir,
                                   mock_islink,
                                   mock_listdir):
        mock_stat.side_effect = stat_side_effect
        mock_isdir.side_effect = isdir_side_effect
        mock_islink.return_value = False
        mock_listdir.side_effect = listdir_side_effect

        config = {
            "path": TEST_DIR,
            "overweight_threshold": 10000,
            "expiry_days": 1
        }
        tree = PathTree(config)
        tree.create_tree()
        overweight_nodes = tree.find_overweight_nodes()

        test_dir = tree.root
        self.assertEqual(2, len(overweight_nodes))
        self.assertIn(test_dir, overweight_nodes)
        self.assertIn(test_dir.children[2], overweight_nodes)

    @patch("datetime.now")
    @patch("os.listdir")
    @patch("os.path.islink")
    @patch("os.path.isdir")
    @patch("os.stat")
    def test_find_expired_nodes(self,
                                mock_stat,
                                mock_isdir,
                                mock_islink,
                                mock_listdir,
                                mock_now):
        mock_stat.side_effect = stat_side_effect
        mock_isdir.side_effect = isdir_side_effect
        mock_islink.return_value = False
        mock_listdir.side_effect = listdir_side_effect
        mock_now.return_value = 1574203167

        config = {
            "path": TEST_DIR,
            "overweight_threshold": 10000,
            "expiry_days": 1
        }
        tree = PathTree(config)
        tree.create_tree()
        expired_nodes = tree.find_expired_nodes()

        test_dir = tree.root
        file1 = test_dir.children[2]
        dir2 = test_dir.children[1]
        file2_1 = test_dir.children[1].children[0]
        file2_2 = test_dir.children[1].children[1]

        self.assertEqual(4, len(expired_nodes))
        self.assertIn(file1, expired_nodes)
        self.assertIn(dir2, expired_nodes)
        self.assertIn(file2_1, expired_nodes)
        self.assertIn(file2_2, expired_nodes)

