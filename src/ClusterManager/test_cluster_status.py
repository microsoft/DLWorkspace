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
from cluster_status import str2bool, ClusterStatus, ClusterStatusFactory
from resource_stat import Cpu, Memory, Gpu


Mi = 1024 * 1024


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
        self.node_selector = None
        self.namespace = None
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
                                labels=config.labels,
                                namespace=config.namespace)

    containers = []
    for i, requests in enumerate(config.container_requests):
        r = V1ResourceRequirements(requests=requests)
        c = V1Container(name=config.name + str(i), resources=r)
        containers.append(c)

    pod.spec = V1PodSpec(node_name=config.node_name,
                         containers=containers,
                         node_selector=config.node_selector)

    pod.status = V1PodStatus(phase=config.phase)

    return pod


class TestUtils(TestCase):
    def test_str2bool(self):
        self.assertTrue(str2bool("True"))
        self.assertTrue(str2bool("1"))
        self.assertTrue(str2bool("Y"))
        self.assertTrue(str2bool("Yes"))
        self.assertTrue(str2bool("T"))
        self.assertFalse(str2bool("false"))
        self.assertFalse(str2bool("0"))


class TestClusterStatus(TestCase):
    def test_to_dict(self):
        inclusion = [
            "gpu_capacity",
            "gpu_used",
            "gpu_preemptable_used",
            "gpu_available",
            "gpu_unschedulable",
            "gpu_reserved",
            "cpu_capacity",
            "cpu_used",
            "cpu_preemptable_used",
            "cpu_available",
            "cpu_unschedulable",
            "cpu_reserved",
            "memory_capacity",
            "memory_used",
            "memory_preemptable_used",
            "memory_available",
            "memory_unschedulable",
            "memory_reserved",
            "node_status",
            "pod_status",
            "user_status",
            "user_status_preemptable",
            "available_job_num",
        ]
        exclusion = [
            "jobs",
            "node_statuses",
            "pod_statuses",
            "user_statuses",
            "user_statuses_preemptable",
        ]

        cs = ClusterStatus({}, {}, [])
        d = cs.to_dict()

        for inc in inclusion:
            self.assertTrue(inc in d)

        for exc in exclusion:
            self.assertFalse(exc in d)

    def test_compute_cluster_status(self):
        """
        3 nodes
          node1:
            sku: m_type1
            gpu:
              P40: 4
            cpu: 10
            memory: 102400Mi
          node2:
            sku: m_type2
            gpu:
              P40: 0
            cpu: 20
            memory: 409600Mi
          node3:
            sku: m_type3
            gpu:
              P40: 4
            unschedulable: True
            cpu: 12
            memory: 102400Mi

        4 pods
          pod1:
            node:
              node1
            gpu:
              P40: 1
            cpu: 4
            memory: 81920Mi
            user: user1
          pod2:
            node:
              node2
            gpu:
              P40: 0
            cpu: 16
            memory: 348160Mi
            user: user2
          pod3:
            node:
              node1
            gpu:
              P40: 2
            cpu: 2
            memory: 2048Mi
            user: user3
          pod4:
            node:
              node3
            gpu:
              P40: 2
            cpu: 6
            memory: 61440Mi
            user: user1
        """
        # Create node1
        n1_config = MockK8sNodeConfig()
        n1_config.name = "node1"
        n1_config.labels = {
            "gpuType": "P40",
            "sku": "m_type1",
            "worker": "active"
        }
        n1_config.capacity = {
            "nvidia.com/gpu": "4",
            "cpu": "10",
            "memory": "102400Mi"
        }
        n1_config.allocatable = {
            "nvidia.com/gpu": "4",
            "cpu": "10",
            "memory": "102400Mi"
        }
        n1_config.internal_ip = "10.0.0.1"
        n1_config.unschedulable = False
        n1_config.ready = "True"
        node1 = mock_k8s_node(n1_config)

        # Create node2
        n2_config = MockK8sNodeConfig()
        n2_config.name = "node2"
        n2_config.labels = {
            "sku": "m_type2",
            "worker": "active"
        }
        n2_config.capacity = {
            "cpu": "20",
            "memory": "409600Mi"
        }
        n2_config.allocatable = {
            "cpu": "20",
            "memory": "409600Mi"
        }
        n2_config.internal_ip = "10.0.0.2"
        n2_config.unschedulable = False
        n2_config.ready = "True"
        node2 = mock_k8s_node(n2_config)

        # Create node3
        n3_config = MockK8sNodeConfig()
        n3_config.name = "node3"
        n3_config.labels = {
            "gpuType": "P40",
            "sku": "m_type3",
            "worker": "active"
        }
        n3_config.capacity = {
            "nvidia.com/gpu": "4",
            "cpu": "12",
            "memory": "102400Mi"
        }
        n3_config.allocatable = {
            "nvidia.com/gpu": "4",
            "cpu": "12",
            "memory": "102400Mi"
        }
        n3_config.internal_ip = "10.0.0.3"
        n3_config.unschedulable = False
        n3_config.ready = "Unknown"
        node3 = mock_k8s_node(n3_config)

        # Create nodes list
        nodes = [node1, node2, node3]

        # Create pod1
        p1_config = MockK8sPodConfig()
        p1_config.name = "pod1"
        p1_config.labels = {
            "gpuType": "P40",
            "userName": "user1"
        }
        p1_config.node_selector = {"sku": "m_type1"}
        p1_config.namespace = "default"
        p1_config.phase = "Running"
        p1_config.node_name = "node1"
        p1_config.container_requests = [{
            "nvidia.com/gpu": "1",
            "cpu": "4",
            "memory": "81920Mi"
        }]
        pod1 = mock_k8s_pod(p1_config)

        # Create pod2
        p2_config = MockK8sPodConfig()
        p2_config.name = "pod2"
        p2_config.labels = {
            "userName": "user2"
        }
        p2_config.node_selector = {"sku": "m_type2"}
        p2_config.namespace = "default"
        p2_config.phase = "Running"
        p2_config.node_name = "node2"
        p2_config.container_requests = [{
            "cpu": "16",
            "memory": "348160Mi"
        }]
        pod2 = mock_k8s_pod(p2_config)

        # Create pod3
        p3_config = MockK8sPodConfig()
        p3_config.name = "pod3"
        p3_config.labels = {
            "gpuType": "P40",
            "userName": "user3"
        }
        p3_config.node_selector = {"sku": "m_type1"}
        p3_config.namespace = "kube-system"
        p3_config.phase = "Running"
        p3_config.node_name = "node1"
        p3_config.container_requests = [{
            "nvidia.com/gpu": "2",
            "cpu": "2",
            "memory": "2048Mi"
        }]
        pod3 = mock_k8s_pod(p3_config)

        # Create pod4
        p4_config = MockK8sPodConfig()
        p4_config.name = "pod4"
        p4_config.labels = {
            "gpuType": "P40",
            "userName": "user1"
        }
        p4_config.node_selector = {"sku": "m_type3"}
        p4_config.namespace = "default"
        p4_config.phase = "Running"
        p4_config.node_name = "node3"
        p4_config.container_requests = [{
            "nvidia.com/gpu": "2",
            "cpu": "6",
            "memory": "61440Mi"
        }]
        pod4 = mock_k8s_pod(p4_config)

        # Create pods list
        pods = [pod1, pod2, pod3, pod4]

        factory = ClusterStatusFactory({}, nodes, pods, [])
        cs = factory.make()

        # Cluster GPU status
        self.assertEqual(
            Gpu({'m_type1': 4, 'm_type3': 4}),
            cs.gpu_capacity)
        self.assertEqual(
            Gpu({'m_type1': 3, 'm_type3': 2}),
            cs.gpu_used)
        self.assertEqual(
            Gpu(),
            cs.gpu_preemptable_used)
        self.assertEqual(
            Gpu({'m_type1': 1}),
            cs.gpu_available)
        self.assertEqual(
            Gpu({"m_type3": 4}),
            cs.gpu_unschedulable)
        self.assertEqual(
            Gpu({"m_type3": 2}),
            cs.gpu_reserved)

        # Cluster CPU status
        self.assertEqual(
            Cpu({
                "m_type1": 10,
                "m_type2": 20,
                "m_type3": 12
            }),
            cs.cpu_capacity)
        self.assertEqual(
            Cpu({
                "m_type1": 6,
                "m_type2": 16,
                "m_type3": 6
            }),
            cs.cpu_used)
        self.assertEqual(
            Cpu(),
            cs.cpu_preemptable_used)
        self.assertEqual(
            Cpu({
                "m_type1": 4,
                "m_type2": 4
            }),
            cs.cpu_available)
        self.assertEqual(
            Cpu({
                "m_type3": 12
            }),
            cs.cpu_unschedulable)
        self.assertEqual(
            Cpu({
                "m_type3": 6
            }),
            cs.cpu_reserved)

        # Cluster memory status
        self.assertEqual(
            Memory({
                "m_type1": 102400 * Mi,
                "m_type2": 409600 * Mi,
                "m_type3": 102400 * Mi
            }),
            cs.memory_capacity)
        self.assertEqual(
            Memory({
                "m_type1": 83968 * Mi,
                "m_type2": 348160 * Mi,
                "m_type3": 61440 * Mi
            }),
            cs.memory_used)
        self.assertEqual(
            Memory(),
            cs.memory_preemptable_used)
        self.assertEqual(
            Memory({
                "m_type1": 18432 * Mi,
                "m_type2": 61440 * Mi
            }),
            cs.memory_available)
        self.assertEqual(
            Memory({
                "m_type3": 102400 * Mi
            }),
            cs.memory_unschedulable)
        self.assertEqual(
            Memory({
                "m_type3": 40960 * Mi
            }),
            cs.memory_reserved)

        # Cluster node status
        t_node1_status = {
            "name": "node1",
            "labels": {"gpuType": "P40", "sku": "m_type1", "worker": "active"},
            "gpuType": "P40",
            "scheduled_service": ["P40", "m_type1", "worker"],
            "gpu_allocatable": Gpu({"m_type1": 4}),
            "gpu_capacity": Gpu({"m_type1": 4}),
            "gpu_used": Gpu({"m_type1": 3}),
            "gpu_preemptable_used": Gpu({}),
            "cpu_allocatable": Cpu({"m_type1": 10}),
            "cpu_capacity": Cpu({"m_type1": 10}),
            "cpu_used": Cpu({"m_type1": 6}),
            "cpu_preemptable_used": Cpu({}),
            "memory_allocatable": Memory({"m_type1": 102400 * Mi}),
            "memory_capacity": Memory({"m_type1": 102400 * Mi}),
            "memory_used": Memory({"m_type1": 83968 * Mi}),
            "memory_preemptable_used": Memory({}),
            "InternalIP": "10.0.0.1",
            "pods": [
                "pod1 : user1 (gpu #:1)"
            ],
            "unschedulable": False
        }

        t_node2_status = {
            "name": "node2",
            "labels": {"sku": "m_type2", "worker": "active"},
            "gpuType": "",
            "scheduled_service": ["m_type2", "worker"],
            "gpu_allocatable": Gpu({}),
            "gpu_capacity": Gpu({}),
            "gpu_used": Gpu({}),
            "gpu_preemptable_used": Gpu({}),
            "cpu_allocatable": Cpu({"m_type2": 20}),
            "cpu_capacity": Cpu({"m_type2": 20}),
            "cpu_used": Cpu({"m_type2": 16}),
            "cpu_preemptable_used": Cpu({}),
            "memory_allocatable": Memory({"m_type2": 409600 * Mi}),
            "memory_capacity": Memory({"m_type2": 409600 * Mi}),
            "memory_used": Memory({"m_type2": 348160 * Mi}),
            "memory_preemptable_used": Memory({}),
            "InternalIP": "10.0.0.2",
            "pods": [
                "pod2 : user2 (gpu #:0)"
            ],
            "unschedulable": False
        }

        t_node3_status = {
            "name": "node3",
            "labels": {"gpuType": "P40", "sku": "m_type3", "worker": "active"},
            "gpuType": "P40",
            "scheduled_service": ["P40", "m_type3", "worker"],
            "gpu_allocatable": Gpu({"m_type3": 4}),
            "gpu_capacity": Gpu({"m_type3": 4}),
            "gpu_used": Gpu({"m_type3": 2}),
            "gpu_preemptable_used": Gpu({}),
            "cpu_allocatable": Cpu({"m_type3": 12}),
            "cpu_capacity": Cpu({"m_type3": 12}),
            "cpu_used": Cpu({"m_type3": 6}),
            "cpu_preemptable_used": Cpu({}),
            "memory_allocatable": Memory({"m_type3": 102400 * Mi}),
            "memory_capacity": Memory({"m_type3": 102400 * Mi}),
            "memory_used": Memory({"m_type3": 61440 * Mi}),
            "memory_preemptable_used": Memory({}),
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

        # Cluster pod status
        t_pod1_status = {
            "pod_name": "pod1 : user1 (gpu #:1)",
            "job_id": None,
            "vc_name": None,
            "namespace": "default",
            "node_name": "node1",
            "username": "user1",
            "preemption_allowed": False,
            "gpu": Gpu({"m_type1": 1}),
            "preemptable_gpu": Gpu(),
            "cpu": Cpu({"m_type1": 4}),
            "preemptable_cpu": Cpu(),
            "memory": Memory({"m_type1": "81920Mi"}),
            "preemptable_memory": Memory(),
            "gpuType": "P40",
        }

        t_pod2_status = {
            "pod_name": "pod2 : user2 (gpu #:0)",
            "job_id": None,
            "vc_name": None,
            "namespace": "default",
            "node_name": "node2",
            "username": "user2",
            "preemption_allowed": False,
            "gpu": Gpu(),
            "preemptable_gpu": Gpu(),
            "cpu": Cpu({"m_type2": 16}),
            "preemptable_cpu": Cpu(),
            "memory": Memory({"m_type2": "348160Mi"}),
            "preemptable_memory": Memory(),
            "gpuType": "",
        }

        t_pod3_status = {
            "pod_name": "pod3 : user3 (gpu #:2)",
            "job_id": None,
            "vc_name": None,
            "namespace": "kube-system",
            "node_name": "node1",
            "username": "user3",
            "preemption_allowed": False,
            "gpu": Gpu({"m_type1": 2}),
            "preemptable_gpu": Gpu(),
            "cpu": Cpu({"m_type1": 2}),
            "preemptable_cpu": Cpu(),
            "memory": Memory({"m_type1": "2048Mi"}),
            "preemptable_memory": Memory(),
            "gpuType": "P40",
        }

        t_pod4_status = {
            "pod_name": "pod4 : user1 (gpu #:2)",
            "job_id": None,
            "vc_name": None,
            "namespace": "default",
            "node_name": "node3",
            "username": "user1",
            "preemption_allowed": False,
            "gpu": Gpu({"m_type3": 2}),
            "preemptable_gpu": Gpu(),
            "cpu": Cpu({"m_type3": 6}),
            "preemptable_cpu": Cpu(),
            "memory": Memory({"m_type3": "61440Mi"}),
            "preemptable_memory": Memory(),
            "gpuType": "P40",
        }

        t_pod_status = [
            t_pod1_status,
            t_pod2_status,
            t_pod3_status,
            t_pod4_status,
        ]

        self.assertEqual(t_pod_status, cs.pod_status)

        # Cluster user status
        t_user_status = [
            {
                "userName": "user1",
                "userGPU": Gpu({
                    "m_type1": 1,
                    "m_type3": 2
                }),
                "userCPU": Cpu({
                    "m_type1": 4,
                    "m_type3": 6,
                }),
                "userMemory": Memory({
                    "m_type1": 81920 * Mi,
                    "m_type3": 61440 * Mi,
                }),
            },
            {
                "userName": "user2",
                "userGPU": Gpu({}),
                "userCPU": Cpu({"m_type2": 16}),
                "userMemory": Memory({"m_type2": 348160 * Mi}),
            },
            {
                "userName": "user3",
                "userGPU": Gpu({"m_type1": 2}),
                "userCPU": Cpu({"m_type1": 2}),
                "userMemory": Memory({"m_type1": 2048 * Mi}),
            },
        ]
        self.assertEqual(t_user_status, cs.user_status)

        t_user_status_preemptable = [
            {
                "userName": "user%s" % i,
                "userGPU": Gpu({}),
                "userCPU": Cpu({}),
                "userMemory": Memory({}),
            }
            for i in range(1, 4)
        ]
        self.assertEqual(t_user_status_preemptable,
                         cs.user_status_preemptable)

        self.assertEqual(0, cs.available_job_num)
