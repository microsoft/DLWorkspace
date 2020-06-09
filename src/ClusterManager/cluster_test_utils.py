#!/usr/bin/env python3

import json
import os
import sys

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
from cluster_status import ClusterStatus
from virtual_cluster_status import VirtualClusterStatus

sys.path.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../utils"))

from resource_stat import Gpu, Cpu, Memory


class MockK8sNodeConfig(object):
    def __init__(self):
        self.name = None
        self.labels = None
        self.capacity = None
        self.allocatable = None
        self.internal_ip = None
        self.unschedulable = None
        self.ready = None


class MockK8sPodConfig(object):
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

    node = V1Node()

    node.metadata = V1ObjectMeta(name=config.name, labels=config.labels)

    node.spec = V1NodeSpec(unschedulable=config.unschedulable)

    address_ip = V1NodeAddress(config.internal_ip, "InternalIP")
    conditions = [V1NodeCondition(type="Ready", status=config.ready)]
    node.status = V1NodeStatus(addresses=[address_ip],
                               conditions=conditions,
                               capacity=config.capacity,
                               allocatable=config.allocatable)

    return node


def mock_k8s_pod(config):
    if not isinstance(config, MockK8sPodConfig):
        raise TypeError("Wrong config type")

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


class BaseTestClusterSetup(object):
    def __init__(self):
        self.nodes = self.get_nodes()
        self.pods = self.get_pods()
        self.jobs = self.get_jobs()
        self.vc_list = self.get_vc_list()

        self.node_status = self.get_node_status()
        self.pod_status = self.get_pod_status()

        self.cluster_status = self.get_cluster_status()
        self.vc_statuses = self.get_vc_statuses()

    def get_nodes(self):
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
        n2_config.labels = {"sku": "m_type2", "worker": "active"}
        n2_config.capacity = {"cpu": "20", "memory": "409600Mi"}
        n2_config.allocatable = {"cpu": "20", "memory": "409600Mi"}
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

        return [node1, node2, node3]

    def get_pods(self):
        """
        5 pods
          pod1:
            node:
              node1
            gpu:
              P40: 1
            cpu: 4
            memory: 81920Mi
            user: user1
            vc: vc1
          pod2:
            node:
              node2
            gpu:
              P40: 0
            cpu: 16
            memory: 348160Mi
            user: user2
            vc: vc1
          pod3:
            node:
              node1
            gpu:
              P40: 2
            cpu: 2
            memory: 2048Mi
            user: user3
            vc: vc2
          pod4:
            node:
              node3
            gpu:
              P40: 2
            cpu: 6
            memory: 61440Mi
            user: user1
            vc: vc2
          # pod5 is not assigned to any node
          pod5:
            node:
              None
            gpu:
              P40: 1
            cpu: 1
            memory: 10240Mi
            user: user1
            vc: vc2
        """
        # Create pod1
        p1_config = MockK8sPodConfig()
        p1_config.name = "pod1"
        p1_config.labels = {
            "gpuType": "P40",
            "userName": "user1",
            "vcName": "vc1",
            "jobId": "j1",
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
            "userName": "user2",
            "vcName": "vc1",
            "jobId": "j2",
        }
        p2_config.node_selector = {"sku": "m_type2"}
        p2_config.namespace = "default"
        p2_config.phase = "Running"
        p2_config.node_name = "node2"
        p2_config.container_requests = [{"cpu": "16", "memory": "348160Mi"}]
        pod2 = mock_k8s_pod(p2_config)

        # Create pod3
        p3_config = MockK8sPodConfig()
        p3_config.name = "pod3"
        p3_config.labels = {
            "gpuType": "P40",
            "userName": "user3",
            "vcName": "vc2",
            "jobId": "j3",
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
            "userName": "user1",
            "vcName": "vc2",
            "jobId": "j4",
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

        # Create pod5 (not assigned to any node)
        p5_config = MockK8sPodConfig()
        p5_config.name = "pod5"
        p5_config.labels = {
            "gpuType": "P40",
            "userName": "user1",
            "vcName": "vc1",
            "jobId": "j7",
        }
        p5_config.node_selector = {"sku": "m_type1"}
        p5_config.namespace = "default"
        p5_config.phase = "Pending"
        p5_config.node_name = None
        p5_config.container_requests = [{
            "nvidia.com/gpu": "1",
            "cpu": "1",
            "memory": "10240Mi"
        }]
        pod5 = mock_k8s_pod(p5_config)

        return [pod1, pod2, pod3, pod4, pod5]

    def get_jobs(self):
        job1 = {
            "jobId": "j1",
            "vcName": "vc1",
            "jobParams": {},
        }
        job2 = {
            "jobId": "j2",
            "vcName": "vc1",
            "jobParams": {},
        }
        job3 = {
            "jobId": "j3",
            "vcName": "vc2",
            "jobParams": {},
        }
        job4 = {
            "jobId": "j4",
            "vcName": "vc2",
            "jobParams": {},
        }
        # job5 and job6 have not yet been scheduled on k8s
        job5 = {
            "jobId": "j5",
            "vcName": "vc2",
            "userName": "user3",
            "jobParams": {
                "jobtrainingtype": "RegularJob",
                "sku": "m_type2",
                "preemptionAllowed": False,
            }
        }
        job6 = {
            "jobId": "j6",
            "vcName": "vc2",
            "userName": "user3",
            "jobParams": {
                "jobtrainingtype": "RegularJob",
                "sku": "m_type2",
                "preemptionAllowed": True,
            }
        }
        job7 = {
            "jobId": "j7",
            "vcName": "vc1",
            "jobParams": {},
        }
        return [job1, job2, job3, job4, job5, job6, job7]

    def get_vc_list(self):
        vc_list = [{
            "vcName":
                "vc1",
            "resourceQuota":
                json.dumps(
                    {
                        "cpu": {
                            "m_type1": 8,
                            "m_type2": 16,
                        },
                        "memory": {
                            "m_type1": "92160Mi",
                            "m_type2": "348160Mi",
                        },
                        "gpu": {
                            "m_type1": 2,
                            "m_type2": 0,
                        },
                    },
                    separators=(",", ":")),
        }, {
            "vcName":
                "vc2",
            "resourceQuota":
                json.dumps(
                    {
                        "cpu": {
                            "m_type1": 2,
                            "m_type2": 4,
                            "m_type3": 12,
                        },
                        "memory": {
                            "m_type1": "10240Mi",
                            "m_type2": "61440Mi",
                            "m_type3": "102400Mi",
                        },
                        "gpu": {
                            "m_type1": 2,
                            "m_type2": 0,
                            "m_type3": 4,
                        },
                    },
                    separators=(",", ":")),
        }]
        return vc_list

    def get_node_status(self):
        # Cluster node status
        node1_status = {
            "name": "node1",
            "labels": {
                "gpuType": "P40",
                "sku": "m_type1",
                "worker": "active"
            },
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
            "memory_allocatable": Memory({"m_type1": "102400Mi"}),
            "memory_capacity": Memory({"m_type1": "102400Mi"}),
            "memory_used": Memory({"m_type1": "83968Mi"}),
            "memory_preemptable_used": Memory({}),
            "InternalIP": "10.0.0.1",
            "pods": ["pod1 : user1 (gpu #:1)"],
            "unschedulable": False
        }

        node2_status = {
            "name": "node2",
            "labels": {
                "sku": "m_type2",
                "worker": "active"
            },
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
            "memory_allocatable": Memory({"m_type2": "409600Mi"}),
            "memory_capacity": Memory({"m_type2": "409600Mi"}),
            "memory_used": Memory({"m_type2": "348160Mi"}),
            "memory_preemptable_used": Memory({}),
            "InternalIP": "10.0.0.2",
            "pods": ["pod2 : user2 (gpu #:0)"],
            "unschedulable": False
        }

        node3_status = {
            "name": "node3",
            "labels": {
                "gpuType": "P40",
                "sku": "m_type3",
                "worker": "active"
            },
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
            "memory_allocatable": Memory({"m_type3": "102400Mi"}),
            "memory_capacity": Memory({"m_type3": "102400Mi"}),
            "memory_used": Memory({"m_type3": "61440Mi"}),
            "memory_preemptable_used": Memory({}),
            "InternalIP": "10.0.0.3",
            "pods": ["pod4 : user1 (gpu #:2)"],
            "unschedulable": True
        }

        return [node1_status, node2_status, node3_status]

    def get_pod_status(self):
        # Cluster pod status
        pod1_status = {
            "name": "pod1",
            "pod_name": "pod1 : user1 (gpu #:1)",
            "job_id": "j1",
            "vc_name": "vc1",
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
            "gpu_usage": None,
            "is_interactive": False,
        }

        pod2_status = {
            "name": "pod2",
            "pod_name": "pod2 : user2 (gpu #:0)",
            "job_id": "j2",
            "vc_name": "vc1",
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
            "gpu_usage": None,
            "is_interactive": False,
        }

        pod3_status = {
            "name": "pod3",
            "pod_name": "pod3 : user3 (gpu #:2)",
            "job_id": "j3",
            "vc_name": "vc2",
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
            "gpu_usage": None,
            "is_interactive": False,
        }

        pod4_status = {
            "name": "pod4",
            "pod_name": "pod4 : user1 (gpu #:2)",
            "job_id": "j4",
            "vc_name": "vc2",
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
            "gpu_usage": None,
            "is_interactive": False,
        }

        pod5_status = {
            "name": "pod5",
            "pod_name": "pod5 : user1 (gpu #:1)",
            "job_id": "j7",
            "vc_name": "vc1",
            "namespace": "default",
            "node_name": None,
            "username": "user1",
            "preemption_allowed": False,
            "gpu": Gpu({"m_type1": 1}),
            "preemptable_gpu": Gpu(),
            "cpu": Cpu({"m_type1": 1}),
            "preemptable_cpu": Cpu(),
            "memory": Memory({"m_type1": "10240Mi"}),
            "preemptable_memory": Memory(),
            "gpuType": "P40",
            "gpu_usage": None,
            "is_interactive": False,
        }

        return [pod1_status, pod2_status, pod3_status, pod4_status, pod5_status]

    def get_cluster_status(self):
        cs = ClusterStatus({}, {}, [])

        # Set resource count
        cs.gpu_capacity = Gpu({"m_type1": 4, "m_type3": 4})
        cs.gpu_used = Gpu({"m_type1": 4, "m_type3": 2})
        cs.gpu_preemptable_used = Gpu()
        cs.gpu_available = Gpu({"m_type1": 0})
        cs.gpu_unschedulable = Gpu({"m_type3": 4})
        cs.gpu_reserved = Gpu({"m_type3": 2})

        cs.cpu_capacity = Cpu({"m_type1": 10, "m_type2": 20, "m_type3": 12})
        cs.cpu_used = Cpu({"m_type1": 7, "m_type2": 17, "m_type3": 6})
        cs.cpu_preemptable_used = Cpu({"m_type2": 1})
        cs.cpu_available = Cpu({"m_type1": 3, "m_type2": 3})
        cs.cpu_unschedulable = Cpu({"m_type3": 12})
        cs.cpu_reserved = Cpu({"m_type3": 6})

        cs.memory_capacity = Memory({
            "m_type1": "102400Mi",
            "m_type2": "409600Mi",
            "m_type3": "102400Mi",
        })
        cs.memory_used = Memory({
            "m_type1": "94208Mi",
            "m_type2": "348160Mi",
            "m_type3": "61440Mi",
        })
        cs.memory_preemptable_used = Memory()
        cs.memory_available = Memory({
            "m_type1": "8192Mi",
            "m_type2": "61440Mi",
        })
        cs.memory_unschedulable = Memory({"m_type3": "102400Mi"})
        cs.memory_reserved = Memory({"m_type3": "40960Mi"})

        # Set node and pod status
        cs.node_status = self.node_status
        cs.pod_status = self.pod_status

        # Set cluster user status
        user_status = [
            {
                "userName":
                    "user1",
                "userGPU":
                    Gpu({
                        "m_type1": 2,
                        "m_type3": 2
                    }),
                "userCPU":
                    Cpu({
                        "m_type1": 5,
                        "m_type3": 6
                    }),
                "userMemory":
                    Memory({
                        "m_type1": "92160Mi",
                        "m_type3": "61440Mi"
                    }),
            },
            {
                "userName": "user2",
                "userGPU": Gpu(),
                "userCPU": Cpu({"m_type2": 16}),
                "userMemory": Memory({"m_type2": "348160Mi"}),
            },
            {
                "userName": "user3",
                "userGPU": Gpu({"m_type1": 2}),
                "userCPU": Cpu({
                    "m_type1": 2,
                    "m_type2": 1
                }),
                "userMemory": Memory({"m_type1": "2048Mi"}),
            },
        ]
        cs.user_status = user_status

        user_status_preemptable = [{
            "userName": "user%s" % i,
            "userGPU": Gpu(),
            "userCPU": Cpu(),
            "userMemory": Memory(),
        } for i in range(1, 3)]
        user_status_preemptable.append({
            "userName": "user3",
            "userGPU": Gpu(),
            "userCPU": Cpu({"m_type2": 1}),
            "userMemory": Memory(),
        })
        cs.user_status_preemptable = user_status_preemptable

        # Cluster active jobs
        cs.jobs = self.jobs
        cs.available_job_num = 7

        return cs

    def get_vc_statuses(self):
        vc_statuses = {
            "vc1":
                VirtualClusterStatus("vc1", {}, self.cluster_status, {}, {},
                                     {}),
            "vc2":
                VirtualClusterStatus("vc2", {}, self.cluster_status, {}, {},
                                     {}),
        }
        vc1_status = vc_statuses["vc1"]
        vc2_status = vc_statuses["vc2"]

        # Set vc1 resource count
        vc1_status.gpu_capacity = Gpu({"m_type1": 2, "m_type2": 0})
        vc1_status.gpu_used = Gpu({"m_type1": 2, "m_type2": 0})
        vc1_status.gpu_preemptable_used = Gpu()
        vc1_status.gpu_available = Gpu({"m_type1": 0, "m_type2": 0})
        vc1_status.gpu_unschedulable = Gpu()
        vc1_status.gpu_reserved = Gpu()

        vc1_status.cpu_capacity = Cpu({"m_type1": 8, "m_type2": 16})
        vc1_status.cpu_used = Cpu({"m_type1": 5, "m_type2": 16})
        vc1_status.cpu_preemptable_used = Cpu()
        vc1_status.cpu_available = Cpu({"m_type1": 3, "m_type2": 0})
        vc1_status.cpu_unschedulable = Cpu()
        vc1_status.cpu_reserved = Cpu()

        vc1_status.memory_capacity = Memory({
            "m_type1": "92160Mi",
            "m_type2": "348160Mi"
        })
        vc1_status.memory_used = Memory({
            "m_type1": "92160Mi",
            "m_type2": "348160Mi"
        })
        vc1_status.memory_preemptable_used = Memory()
        vc1_status.memory_available = Memory({
            "m_type1": "0Mi",
            "m_type2": "0Mi"
        })
        vc1_status.memory_unschedulable = Memory()
        vc1_status.memory_reserved = Memory()

        # Set vc1 node and pod status
        vc1_status.node_status = self.node_status
        vc1_status.pod_status = [self.pod_status[i] for i in [0, 1, 4]]

        # Set vc1 user status
        user_status = [
            {
                "userName": "user1",
                "userGPU": Gpu({"m_type1": 2}),
                "userCPU": Cpu({"m_type1": 5}),
                "userMemory": Memory({"m_type1": "92160Mi"}),
            },
            {
                "userName": "user2",
                "userGPU": Gpu(),
                "userCPU": Cpu({"m_type2": 16}),
                "userMemory": Memory({"m_type2": "348160Mi"}),
            },
        ]
        vc1_status.user_status = user_status

        user_status_preemptable = [{
            "userName": "user%s" % i,
            "userGPU": Gpu(),
            "userCPU": Cpu(),
            "userMemory": Memory(),
        } for i in [1, 2]]
        vc1_status.user_status_preemptable = user_status_preemptable

        # Set vc1 active job count
        vc1_status.available_job_num = 3

        # Set vc2 resource count
        vc2_status.gpu_capacity = Gpu({
            "m_type1": 2,
            "m_type2": 0,
            "m_type3": 4
        })
        vc2_status.gpu_used = Gpu({"m_type1": 2, "m_type2": 0, "m_type3": 2})
        vc2_status.gpu_preemptable_used = Gpu()
        vc2_status.gpu_available = Gpu({
            "m_type1": 0,
            "m_type2": 0,
            "m_type3": 0
        })
        vc2_status.gpu_unschedulable = Gpu({
            "m_type1": 0,
            "m_type2": 0,
            "m_type3": 2
        })
        vc2_status.gpu_reserved = Gpu({
            "m_type1": 0,
            "m_type2": 0,
            "m_type3": 2
        })

        vc2_status.cpu_capacity = Cpu({
            "m_type1": 2,
            "m_type2": 4,
            "m_type3": 12
        })
        vc2_status.cpu_used = Cpu({"m_type1": 2, "m_type2": 1, "m_type3": 6})
        vc2_status.cpu_preemptable_used = Cpu({"m_type2": 1})
        vc2_status.cpu_available = Cpu({
            "m_type1": 0,
            "m_type2": 3,
            "m_type3": 0
        })
        vc2_status.cpu_unschedulable = Cpu({
            "m_type1": 0,
            "m_type2": 0,
            "m_type3": 6
        })
        vc2_status.cpu_reserved = Cpu({
            "m_type1": 0,
            "m_type2": 0,
            "m_type3": 6
        })

        vc2_status.memory_capacity = Memory({
            "m_type1": "10240Mi",
            "m_type2": "61440Mi",
            "m_type3": "102400Mi"
        })
        vc2_status.memory_used = Memory({
            "m_type1": "2048Mi",
            "m_type2": "0Mi",
            "m_type3": "61440Mi"
        })
        vc2_status.memory_preemptable_used = Memory()
        vc2_status.memory_available = Memory({
            "m_type1": "8192Mi",
            "m_type2": "61440Mi",
            "m_type3": "0Mi"
        })
        vc2_status.memory_unschedulable = Memory({
            "m_type1": "0Mi",
            "m_type2": "0Mi",
            "m_type3": "40960Mi"
        })
        vc2_status.memory_reserved = Memory({
            "m_type1": "0Mi",
            "m_type2": "0Mi",
            "m_type3": "40960Mi"
        })

        # Set vc2 node and pod status
        vc2_status.node_status = self.node_status
        vc2_status.pod_status = self.pod_status[2:4]

        # Set vc2 user status
        user_status = [
            {
                "userName": "user1",
                "userGPU": Gpu({"m_type3": 2}),
                "userCPU": Cpu({"m_type3": 6}),
                "userMemory": Memory({"m_type3": "61440Mi"}),
            },
            {
                "userName": "user3",
                "userGPU": Gpu({
                    "m_type1": 2,
                    "m_type2": 0
                }),
                "userCPU": Cpu({
                    "m_type1": 2,
                    "m_type2": 1
                }),
                "userMemory": Memory({
                    "m_type1": "2048Mi",
                    "m_type2": "0Mi"
                }),
            },
        ]
        vc2_status.user_status = user_status

        user_status_preemptable = [{
            "userName": "user1",
            "userGPU": Gpu(),
            "userCPU": Cpu(),
            "userMemory": Memory(),
        }, {
            "userName": "user3",
            "userGPU": Gpu(),
            "userCPU": Cpu({"m_type2": 1}),
            "userMemory": Memory(),
        }]
        vc2_status.user_status_preemptable = user_status_preemptable

        # Set vc2 active job count
        vc2_status.available_job_num = 4

        return vc_statuses
