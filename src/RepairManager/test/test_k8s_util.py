import unittest
import mock
from utils import k8s_util
from kubernetes.client.models.v1_node import V1Node
from kubernetes.client.models.v1_node_list import V1NodeList
from kubernetes.client.models.v1_node_status import V1NodeStatus
from kubernetes.client.models.v1_node_address import V1NodeAddress
from kubernetes.client.models.v1_pod_list import V1PodList
from kubernetes.client.models.v1_pod import V1Pod
from kubernetes.client.models.v1_object_meta import V1ObjectMeta
from kubernetes.client.models.v1_pod_spec import V1PodSpec

def _mock_v1_node(internal_ip, hostname):
    node = V1Node()
    address_ip = V1NodeAddress(internal_ip, "InternalIP")
    address_hostname = V1NodeAddress(hostname, "Hostname")
    node.status = V1NodeStatus(addresses=[address_ip, address_hostname])
    return node

def _mock_v1_pod(jobId, userName, vcName, nodeName):
    pod = V1Pod()
    pod.metadata = V1ObjectMeta()
    pod.metadata.labels = {
        "jobId": jobId,
        "type": "job",
        "userName": userName,
        "vcName": vcName
    }
    pod.spec = V1PodSpec(containers=[])
    pod.spec.node_name = nodeName
    return pod

class TestK8sUtil(unittest.TestCase):

    @mock.patch('utils.k8s_util.list_namespaced_pod')
    def test_get_job_info_indexed_by_job_id(self, mock_list_namespaced_pod):
        pod_one = _mock_v1_pod("87654321-wxyz", "user1", "vc1", "node1")
        pod_two = _mock_v1_pod("12345678-abcd", "user2", "vc2", "node1")
        pod_three = _mock_v1_pod("12345678-abcd", "user2", "vc2", "node2")
        pod_four = _mock_v1_pod("99999999-efgh", "user3", "vc3", "node3")
        mock_pod_list = V1PodList(items=[pod_one, pod_two, pod_three, pod_four])
        mock_list_namespaced_pod.return_value = mock_pod_list

        job_response = k8s_util.get_job_info_indexed_by_job_id(
            ["node1", "node2"], "dlts.domain.com", "cluster1")

        self.assertTrue("87654321-wxyz" in job_response)
        self.assertEqual(1, len(job_response["87654321-wxyz"]["node_names"]))
        self.assertTrue("node1" in job_response["87654321-wxyz"]["node_names"])
        self.assertEqual("https://dlts.domain.com/job/vc1/cluster1/87654321-wxyz",
         job_response["87654321-wxyz"]["job_link"])

        self.assertTrue("12345678-abcd" in job_response)
        self.assertEqual(2, len(job_response["12345678-abcd"]["node_names"]))
        self.assertTrue("node1" in job_response["12345678-abcd"]["node_names"])
        self.assertTrue("node2" in job_response["12345678-abcd"]["node_names"])
        self.assertEqual("https://dlts.domain.com/job/vc2/cluster1/12345678-abcd", 
        job_response["12345678-abcd"]["job_link"])


    @mock.patch('utils.k8s_util.list_namespaced_pod')
    def test_get_job_info_indexed_by_node(self, mock_list_namespaced_pod):
        pod_one = _mock_v1_pod("87654321-wxyz", "user1", "vc1", "node1")
        pod_two = _mock_v1_pod("12345678-abcd", "user2", "vc2", "node1")
        pod_three = _mock_v1_pod("12345678-abcd", "user2", "vc2", "node2")
        pod_four = _mock_v1_pod("99999999-efgh", "user3", "vc3", "node3")
        mock_pod_list = V1PodList(items=[pod_one, pod_two, pod_three, pod_four])
        mock_list_namespaced_pod.return_value = mock_pod_list

        job_response = k8s_util.get_job_info_indexed_by_node(
            ["node1", "node2"], "dlts.domain.com", "cluster1")

        self.assertEqual(2, len(job_response))

        self.assertTrue("node1" in job_response)
        self.assertEqual(2, len(job_response["node1"]))
        self.assertTrue("87654321-wxyz" in job_response["node1"][0]["job_id"])
        self.assertTrue("user1" in job_response["node1"][0]["user_name"])
        self.assertTrue("vc1" in job_response["node1"][0]["vc_name"])
        self.assertEqual("https://dlts.domain.com/job/vc1/cluster1/87654321-wxyz",
        job_response["node1"][0]["job_link"])

        self.assertTrue("12345678-abcd" in job_response["node1"][1]["job_id"])
        self.assertTrue("user2" in job_response["node1"][1]["user_name"])
        self.assertTrue("vc2" in job_response["node1"][1]["vc_name"])
        self.assertEqual("https://dlts.domain.com/job/vc2/cluster1/12345678-abcd",
        job_response["node1"][1]["job_link"])

        self.assertTrue("node2" in job_response)
        self.assertEqual(1, len(job_response["node2"]))
        self.assertTrue("12345678-abcd" in job_response["node2"][0]["job_id"])
        self.assertTrue("user2" in job_response["node2"][0]["user_name"])
        self.assertTrue("vc2" in job_response["node2"][0]["vc_name"])
        self.assertEqual("https://dlts.domain.com/job/vc2/cluster1/12345678-abcd",
        job_response["node2"][0]["job_link"])


    @mock.patch('utils.k8s_util.list_node')
    def test_get_node_address_info(self, mock_list_node):
        node_one = _mock_v1_node("192.168.0.1", "mock-worker-one")
        node_two = _mock_v1_node("192.168.0.2", "mock-worker-two")
        mock_list_node.return_value = V1NodeList(items=[node_one, node_two])

        address_info = k8s_util.get_node_address_info()

        self.assertEqual(len(address_info), 2)
        self.assertTrue('192.168.0.1' in address_info)
        self.assertEqual(address_info['192.168.0.1'], "mock-worker-one")
        self.assertTrue('192.168.0.2' in address_info)
        self.assertEqual(address_info['192.168.0.2'], "mock-worker-two")


    @mock.patch('utils.k8s_util.list_node')
    def test_get_node_address_info_empty(self, mock_list_node):
        mock_list_node.return_value = V1NodeList(items=[])

        address_info = k8s_util.get_node_address_info()

        self.assertEqual(len(address_info), 0)
