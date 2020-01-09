import os
import platform

from unittest import TestCase
from unittest.mock import patch
from path_tree import PathTree
from utils import DAY
from testcase_utils import DummyNodeStat


SYSTEM = platform.system()
WINDOWS = "Windows"
LINUX = "Linux"

EMPTY_DIR_SIZE = 4096 if SYSTEM is LINUX else 0

"""Test Example:

test_dir
  |- dir1
  |- dir2
  |   |- file2_1
  |   |- file2_2
  |- file1
"""

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
    def test_walk_on_invalid_path(self):
        config = {
            "path": "dummy",
            "overweight_threshold": 1000,
            "expiry_days": 1,
            "now": 1574203167
        }
        tree = PathTree(config)
        tree.walk()
        self.assertEqual(None, tree.root)

    @patch("os.listdir")
    @patch("os.path.islink")
    @patch("os.path.isdir")
    @patch("os.stat")
    def test_walk_on_valid_path(self,
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
            "expiry_days": 1,
            "now": 1574203167
        }
        tree = PathTree(config)
        tree.walk()

        self.assertEqual(1, len(tree.overweight_boundary_nodes))
        self.assertEqual(2, len(tree.expired_boundary_nodes))
        self.assertEqual(1, len(tree.empty_boundary_nodes))
