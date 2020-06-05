import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kubernetes.client.models.v1_node_list import V1NodeList
from kubernetes.client.models.v1_node import V1Node
from kubernetes.client.models.v1_node_status import V1NodeStatus
from kubernetes.client.models.v1_node_address import V1NodeAddress
from kubernetes.client.models.v1_pod_list import V1PodList
from kubernetes.client.models.v1_pod import V1Pod
from kubernetes.client.models.v1_object_meta import V1ObjectMeta
from kubernetes.client.models.v1_pod_spec import V1PodSpec


def mock_rule_config():
    rule_config = {
        "cluster_name": "mock-cluster",
        "portal_url": "dltshub.example.com",
        "job_owner_email_domain": "example.com",
        "restore_from_rule_cache_dump": False,
        "date_time_format": "%Y-%m-%d %H:%M:%S.%f",
        "prometheus": {
            "ip": "localhost",
            "port": 9091,
            "ecc_error_query": 'nvidiasmi_ecc_error_count{type="volatile_double"}>0',
            "node_boot_time_query": 'node_boot_time_seconds',
            "large_latency_query":
                "histogram_quantile(0.95, sum(rate(cmd_nvidia_smi_latency_seconds_bucket[5m])) " \
                "BY (le, instance)) > 40",
        },
        "rest_url": "http://localhost:9999"
    }
    return rule_config


def mock_ecc_config():
    ecc_config = {
        "enable_cordon": True,
        "enable_reboot": True,
        "enable_alert_job_owners": True,
        "days_until_node_reboot": 5,
        "time_sleep_after_pausing": 0,
        "attempts_for_pause_resume_jobs": 1
    }
    return ecc_config


def mock_etcd_config():
    ecc_config = {
        "data-dir": "/data-dir",
        "listen-peer-urls": "http://0.0.0.0:2381",
        "listen-client-urls": "http://0.0.0.0:2382",
        "advertise-client-urls": "http://127.0.0.1:2382",
        "initial-advertise-peer-urls": "http://127.0.0.1:2381",
        "initial-cluster": "default=http://127.0.0.1:2381",
        "enable-v2": True
    }
    return ecc_config


def mock_latency_config():
    latency_config = {"alert_expiry": 4}
    return latency_config


def mock_empty_prometheus_metric_data():
    empty_prometheus_metric_data = {"status": "success", "data": {"result": []}}
    return empty_prometheus_metric_data


def mock_v1_node(internal_ip, hostname):
    node = V1Node()
    address_ip = V1NodeAddress(internal_ip, "InternalIP")
    address_hostname = V1NodeAddress(hostname, "Hostname")
    node.status = V1NodeStatus(addresses=[address_ip, address_hostname])
    return node


def mock_v1_pod(jobId, userName, vcName, nodeName):
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


def mock_v1_node_list(items):
    mock_node_list = []
    for item in items:
        mock_node = mock_v1_node(item["instance"], item["node_name"])
        mock_node_list.append(mock_node)
    return V1NodeList(items=mock_node_list)


def mock_v1_pod_list(items):
    mock_pod_list = []
    for item in items:
        mock_pod = mock_v1_pod(item["job_name"], item["user_name"],
                               item["vc_name"], item["node_name"])
        mock_pod_list.append(mock_pod)
    return V1PodList(items=mock_pod_list)
