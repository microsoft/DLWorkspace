#!/usr/bin/env python3

from unittest import TestCase
from kubernetes.client.models.v1_object_meta import V1ObjectMeta
from kubernetes.client.models.v1_node import V1Node
from kubernetes.client.models.v1_node_spec import V1NodeSpec
from kubernetes.client.models.v1_node_status import V1NodeStatus
from kubernetes.client.models.v1_node_address import V1NodeAddress
from kubernetes.client.models.v1_node_condition import V1NodeCondition
from kubernetes.client.models.v1_pod import V1Pod
from kubernetes.client.models.v1_pod_spec import V1PodSpec
from kubernetes.client.models.v1_pod_status import V1PodStatus
from kubernetes.client.models.v1_container import V1Container
from kubernetes.client.models.v1_resource_requirements import \
    V1ResourceRequirements
from cluster_status import str2bool, ClusterStatus


class MockK8sConfig(object):
    def is_initialized(self):
        for _, v in self.__dict__.items():
            if v is None:
                return False
        return True


class MockK8sNodeConfig(MockK8sConfig):
    def __init__(self):
        self.name = None
        self.labels = None
        self.capacity = None
        self.allocatable = None
        self.internal_ip = None
        self.unschedulable = None
        self.ready = None


class MockK8sPodConfig(MockK8sConfig):
    def __int__(self):
        self.name = None
        self.labels = None
        self.phase = None
        self.node_name = None
        # A list of container resource requests
        self.container_requests = None


def mock_k8s_node(config):
    if not isinstance(config, MockK8sNodeConfig):
        raise TypeError("Wrong config type")

    if not config.is_initialized():
        raise ValueError("Config uninitialized")

    node = V1Node()

    node.metadata = V1ObjectMeta(name=config.name,
                                 labels=config.labels)

    node.spec = V1NodeSpec(unschedulable=config.unschedulable)

    address_ip = V1NodeAddress(config.internal_ip, "InternalIP")
    conditions = [
        V1NodeCondition(type="Ready", status=config.ready)
    ]
    node.status = V1NodeStatus(addresses=[address_ip],
                               conditions=conditions,
                               capacity=config.capacity,
                               allocatable=config.allocatable)

    return node


def mock_k8s_pod(config):
    if not isinstance(config, MockK8sPodConfig):
        raise TypeError("Wrong config type")

    if not config.is_initialized():
        raise ValueError("Config uninitialized")

    pod = V1Pod()

    pod.metadata = V1ObjectMeta(name=config.name,
                                labels=config.labels)

    containers = []
    for i, requests in enumerate(config.container_requests):
        r = V1ResourceRequirements(requests=requests)
        c = V1Container(name=config.name + str(i), resources=r)
        containers.append(c)

    pod.spec = V1PodSpec(node_name=config.node_name,
                         containers=containers)

    pod.status = V1PodStatus(phase=config.phase)

    return pod


class TestClusterStatus(TestCase):
    def test_str2bool(self):
        self.assertTrue(str2bool("True"))
        self.assertTrue(str2bool("1"))
        self.assertTrue(str2bool("Y"))
        self.assertTrue(str2bool("Yes"))
        self.assertTrue(str2bool("T"))
        self.assertFalse(str2bool("false"))
        self.assertFalse(str2bool("0"))

    def test_to_dict(self):
        inclusion = [
            "gpu_capacity",
            "gpu_used",
            "gpu_available",
            "gpu_unschedulable",
            "gpu_reserved",
            "node_status",
            "user_status",
            "user_status_preemptable"
        ]
        exclusion = [
            "prometheus_node",
            "nodes",
            "pods",
            "node_statuses",
            "pod_statuses",
            "user_info",
            "user_info_preemptable",
            "dict_exclusion"
        ]

        cs = ClusterStatus({}, [], [])
        d = cs.to_dict()

        for inc in inclusion:
            self.assertTrue(inc in d)

        for exc in exclusion:
            self.assertFalse(exc in d)

    def test_compute_cluster_status(self):
        """
        3 nodes
          node1:
            gpu:
              P40: 4
          node2:
            gpu:
              P40: 0
          node3:
            gpu:
              P40: 4
            unschedulable: True

        4 pods
          pod1:
            node:
              node1
            gpu:
              P40: 1
            user: user1
          pod2:
            node:
              node2
            gpu:
              P40: 0
            user: user2
          pod3:
            node:
              node1
            gpu:
              P40: 2
            user: user3
          pod4:
            node:
              node3
            gpu:
              P40: 2
            user: user1
        """
        # Create node1
        n1_config = MockK8sNodeConfig()
        n1_config.name = "node1"
        n1_config.labels = {"gpuType": "P40"}
        n1_config.capacity = {"nvidia.com/gpu": 4}
        n1_config.allocatable = {"nvidia.com/gpu": 4}
        n1_config.internal_ip = "10.0.0.1"
        n1_config.unschedulable = False
        n1_config.ready = "True"
        node1 = mock_k8s_node(n1_config)

        # Create node2
        n2_config = MockK8sNodeConfig()
        n2_config.name = "node2"
        n2_config.labels = {}
        n2_config.capacity = {}
        n2_config.allocatable = {}
        n2_config.internal_ip = "10.0.0.2"
        n2_config.unschedulable = False
        n2_config.ready = "True"
        node2 = mock_k8s_node(n2_config)

        # Create node3
        n3_config = MockK8sNodeConfig()
        n3_config.name = "node3"
        n3_config.labels = {"gpuType": "P40"}
        n3_config.capacity = {"nvidia.com/gpu": 4}
        n3_config.allocatable = {"nvidia.com/gpu": 4}
        n3_config.internal_ip = "10.0.0.3"
        n3_config.unschedulable = False
        n3_config.ready = "Unknown"
        node3 = mock_k8s_node(n3_config)

        # Create nodes list
        nodes = [node1, node2, node3]

        # Create pod1
        p1_config = MockK8sPodConfig()
        p1_config.name = "pod1"
        p1_config.labels = {"gpuType": "P40", "userName": "user1"}
        p1_config.phase = "Running"
        p1_config.node_name = "node1"
        p1_config.container_requests = [{"nvidia.com/gpu": 1}]
        pod1 = mock_k8s_pod(p1_config)

        # Create pod2
        p2_config = MockK8sPodConfig()
        p2_config.name = "pod2"
        p2_config.labels = {"userName": "user2"}
        p2_config.phase = "Running"
        p2_config.node_name = "node2"
        p2_config.container_requests = [{"nvidia.com/gpu": 0}]
        pod2 = mock_k8s_pod(p2_config)

        # Create pod3
        p3_config = MockK8sPodConfig()
        p3_config.name = "pod3"
        p3_config.labels = {"gpuType": "P40", "userName": "user3"}
        p3_config.phase = "Running"
        p3_config.node_name = "node1"
        p3_config.container_requests = [{"nvidia.com/gpu": 2}]
        pod3 = mock_k8s_pod(p3_config)

        # Create pod4
        p4_config = MockK8sPodConfig()
        p4_config.name = "pod4"
        p4_config.labels = {"gpuType": "P40", "userName": "user1"}
        p4_config.phase = "Running"
        p4_config.node_name = "node3"
        p4_config.container_requests = [{"nvidia.com/gpu": 2}]
        pod4 = mock_k8s_pod(p4_config)

        # Create pods list
        pods = [pod1, pod2, pod3, pod4]

        cs = ClusterStatus({}, nodes, pods)
        cs.compute()

        # Cluster GPU status
        self.assertEqual({"P40": 8}, cs.gpu_capacity)
        self.assertEqual({"P40": 5}, cs.gpu_used)
        self.assertEqual({"P40": 1}, cs.gpu_available)
        self.assertEqual({"P40": 4}, cs.gpu_unschedulable)
        self.assertEqual({"P40": 2}, cs.gpu_reserved)

        # Cluster node status
        t_node1_status = {
            "name": "node1",
            "labels": {"gpuType": "P40"},
            "gpuType": "P40",
            "scheduled_service": ["P40"],
            "gpu_allocatable": {"P40": 4},
            "gpu_capacity": {"P40": 4},
            "gpu_used": {"P40": 3},
            "gpu_preemptable_used": {},
            "InternalIP": "10.0.0.1",
            "pods": [
                "pod1 : user1 (gpu #:1)",
                "pod3 : user3 (gpu #:2)"
            ],
            "unschedulable": False
        }

        t_node2_status = {
            "name": "node2",
            "labels": {},
            "gpuType": "",
            "scheduled_service": [],
            "gpu_allocatable": {},
            "gpu_capacity": {},
            "gpu_used": {},
            "gpu_preemptable_used": {},
            "InternalIP": "10.0.0.2",
            "pods": [
                "pod2 : user2 (gpu #:0)"
            ],
            "unschedulable": False
        }

        t_node3_status = {
            "name": "node3",
            "labels": {"gpuType": "P40"},
            "gpuType": "P40",
            "scheduled_service": ["P40"],
            "gpu_allocatable": {"P40": 4},
            "gpu_capacity": {"P40": 4},
            "gpu_used": {"P40": 2},
            "gpu_preemptable_used": {},
            "InternalIP": "10.0.0.3",
            "pods": [
                "pod4 : user1 (gpu #:2)"
            ],
            "unschedulable": True
        }

        t_node_status = [
            t_node1_status,
            t_node2_status,
            t_node3_status
        ]

        self.assertEqual(t_node_status, cs.node_status)

        # Cluster user status
        t_user_status = [
            {
                "userName": "user1",
                "userGPU": {"P40": 3}
            },
            {
                "userName": "user2",
                "userGPU": {}
            },
            {
                "userName": "user3",
                "userGPU": {"P40": 2}
            }
        ]
        self.assertEqual(t_user_status, cs.user_status)

        t_user_status_preemptable = [
            {
                "userName": "user%s" % i,
                "userGPU": {}
            }
            for i in range(1, 4)
        ]
        self.assertEqual(t_user_status_preemptable,
                         cs.user_status_preemptable)
