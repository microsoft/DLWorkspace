from unittest import TestCase
from unittest.mock import patch
from testcase_utils import DummyNodeStat
from datetime import datetime
from path_node import PathNode

NODE_PATH = "/dummy"
NODE_SIZE = 2147483648
NODE_ATIME = 1574203167
NODE_MTIME = 1574201167
NODE_CTIME = 1574203167
NODE_UID = 635550533
NODE_GID = 600000513
USER_NAME = "dummy"


class TestPathNode(TestCase):
    @patch("os.path.isdir")
    @patch("os.stat")
    def test_path_node(self, mock_stat, mock_isdir):
        mock_isdir.return_value = True
        mock_stat.return_value = DummyNodeStat(size=NODE_SIZE,
                                               atime=NODE_ATIME,
                                               mtime=NODE_MTIME,
                                               ctime=NODE_CTIME,
                                               uid=NODE_UID,
                                               gid=NODE_GID)

        node = PathNode(NODE_PATH)
        self.assertEqual(NODE_PATH, node.path)
        self.assertTrue(node.isdir)
        self.assertEqual(1, node.ino)
        self.assertEqual(1, node.nlink)
        self.assertEqual(NODE_SIZE, node.size)
        self.assertEqual(NODE_SIZE, node.subtree_size)
        self.assertEqual(datetime(2019, 11, 19, 22, 39, 27), node.atime)
        self.assertEqual(datetime(2019, 11, 19, 22, 39, 27), node.subtree_atime)
        self.assertEqual(datetime(2019, 11, 19, 22, 6, 7), node.mtime)
        self.assertEqual(datetime(2019, 11, 19, 22, 6, 7), node.subtree_mtime)
        self.assertEqual(datetime(2019, 11, 19, 22, 39, 27), node.ctime)
        self.assertEqual(datetime(2019, 11, 19, 22, 39, 27), node.subtree_ctime)
        self.assertEqual(datetime(2019, 11, 19, 22, 6, 7), node.time)
        self.assertEqual(datetime(2019, 11, 19, 22, 6, 7), node.subtree_time)
        self.assertEqual(NODE_UID, node.uid)
        self.assertEqual(NODE_GID, node.gid)
        self.assertEqual("", node.owner)
        self.assertEqual([], node.children)
        self.assertEqual(1, node.num_subtree_nodes)
        self.assertEqual(0, node.num_subtree_files)

        mock_isdir.return_value = False
        node = PathNode(NODE_PATH)
        self.assertFalse(node.isdir)
        self.assertEqual(1, node.num_subtree_files)

        uid_to_user = {NODE_UID: USER_NAME}
        node = PathNode(NODE_PATH, uid_to_user)
        self.assertEqual(USER_NAME, node.owner)

        expected = "2019/11/19 22:39:27,2019/11/19 22:06:07," \
                   "2019/11/19 22:39:27,2019/11/19 22:39:27,2G,dummy,/dummy"
        self.assertEqual(expected, str(node))
