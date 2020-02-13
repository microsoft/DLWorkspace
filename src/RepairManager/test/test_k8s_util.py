import unittest
import mock
from utils import k8s_util
from kubernetes.client.models.v1_node import V1Node
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

class Testing(unittest.TestCase):

    def test_get_job_info_from_nodes(self):
        pod_one = _mock_v1_pod("87654321-wxyz", "user1", "vc1", "node1")
        pod_two = _mock_v1_pod("12345678-abcd", "user2", "vc2", "node1")
        pod_three = _mock_v1_pod("12345678-abcd", "user2", "vc2", "node2")
        pod_four = _mock_v1_pod("99999999-efgh", "user3", "vc3", "node3")
        mock_pod_list = V1PodList(items=[pod_one, pod_two, pod_three, pod_four])


        job_response = k8s_util._get_job_info_from_nodes(
            mock_pod_list, ["node1", "node2"], "dlts.domain.com", "cluster1")

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
