import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import mock
import datetime
from mock import call
from rules import ecc_detect_error_rule
from rules.ecc_detect_error_rule import ECCDetectErrorRule
from utils import k8s_util, rule_alert_handler
from kubernetes.client.models.v1_node_list import V1NodeList
from kubernetes.client.models.v1_node import V1Node
from kubernetes.client.models.v1_node_status import V1NodeStatus
from kubernetes.client.models.v1_node_address import V1NodeAddress
from kubernetes.client.models.v1_pod_list import V1PodList
from kubernetes.client.models.v1_pod import V1Pod
from kubernetes.client.models.v1_object_meta import V1ObjectMeta
from kubernetes.client.models.v1_pod_spec import V1PodSpec

### Please fill in SMTP info and enable tests to receive emails ###
SMTP_URL = '[SMTP_URL]'
LOGIN = '[LOGIN]'
PASSWORD = '[PASSWORD]'
SENDER = '[SENDER]'
JOB_OWNER_EMAIL = '[JOB_OWNER_EMAIL]'
DRI_EMAIL = '[DRI_EMAIL]'


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

def _mock_rule_config():
    rule_config = {
        "cluster_name": "mock-cluster",
        "portal_url": "dltshub.example.com",
        "job_owner_email_domain": "example.com",
        "restore_from_rule_cache_dump": False
    }
    return rule_config

def _mock_ecc_config():
    mock_ecc_config = {
            "cordon_dry_run": False,
            "prometheus": {
                "ip": "localhost",
                "port": 9091,
                "ecc_error_query": 'nvidiasmi_ecc_error_count{type="volatile_double"}>0'
            },
            "alert_job_owners": False,
            "dri_email": "dri@email.com",
            "reboot_dry_run": False,
            "days_until_node_reboot": 5
        }
    return mock_ecc_config

def _mock_empty_prometheus_error_data():
    empty_prometheus_error_data = {
            "status":
                "success",
                "data": {
                    "result": []
                }
        }
    return empty_prometheus_error_data

def _mock_prometheus_error_data():
    mock_prometheus_error_data = {
            "status":
                "success",
                "data": {
                    "result": [{
                        "metric": {
                            "__name__": "nvidiasmi_ecc_error_count",
                            "exporter_name": "job-exporter",
                            "instance": "192.168.0.1:9102",
                            "job": "serivce_exporter",
                            "minor_number": "1",
                            "scraped_from": "job-exporter-jmgn4",
                            "type": "volatile_double"
                        },
                        "values": [
                            [1578453042, "2"], [1578453042, "2"]  
                        ]
                    },
                    {
                        "metric": {
                            "__name__": "nvidiasmi_ecc_error_count",
                            "exporter_name": "job-exporter",
                            "instance": "192.168.0.2:9102",
                            "job": "serivce_exporter",
                            "minor_number": "1",
                            "scraped_from": "job-exporter-jmgn4",
                            "type": "volatile_double"
                        },
                        "values": [
                            [1578453042, "2"], [1578453042, "2"], [1578453042, "2"]
                        ]
                    }]
                }
        }
    return mock_prometheus_error_data

class Testing(unittest.TestCase):

    def test_get_node_address_info(self):
        node_one = _mock_v1_node("192.168.0.1", "mock-worker-one")
        node_two = _mock_v1_node("192.168.0.2", "mock-worker-two")
        mock_node_list = V1NodeList(items=[node_one, node_two])

        address_info = ecc_detect_error_rule._get_node_address_info(mock_node_list)

        self.assertEqual(len(address_info), 2)
        self.assertTrue('192.168.0.1' in address_info)
        self.assertEqual(address_info['192.168.0.1'], "mock-worker-one")
        self.assertTrue('192.168.0.2' in address_info)
        self.assertEqual(address_info['192.168.0.2'], "mock-worker-two")


    def test_get_node_address_info_empty(self):
        mock_node_list = V1NodeList(items=[])

        address_info = ecc_detect_error_rule._get_node_address_info(mock_node_list)

        self.assertEqual(len(address_info), 0)

    
    def test_extract_ips_from_ecc_data(self):
        prometheus_error_data = _mock_prometheus_error_data()

        ecc_node_ips = ecc_detect_error_rule._extract_ips_from_ecc_data(prometheus_error_data)

        self.assertEqual(len(ecc_node_ips), 2)
        self.assertTrue('192.168.0.1' in ecc_node_ips)
        self.assertTrue('192.168.0.2' in ecc_node_ips)


    def test_extract_ips_from_ecc_data_empty(self):
        prometheus_error_data = _mock_empty_prometheus_error_data()

        ecc_node_ips = ecc_detect_error_rule._extract_ips_from_ecc_data(prometheus_error_data)

        self.assertIsNone(ecc_node_ips)


    @mock.patch('utils.email_util.EmailHandler')
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler.load_config')
    @mock.patch('rules.ecc_detect_error_rule.k8s_util.list_node')
    @mock.patch('rules.ecc_detect_error_rule.requests.get')
    @mock.patch('rules.ecc_detect_error_rule.ECCDetectErrorRule.load_ecc_config')
    def test_check_status_ecc_error_detected(self, 
            mock_load_ecc_config,
            mock_request_get,
            mock_list_node,
            mock_rule_alert_handler_load_config,
            mock_email_handler):

        mock_rule_config = _mock_rule_config()
        mock_rule_alert_handler_load_config.return_value = mock_rule_config
        mock_load_ecc_config.return_value = _mock_ecc_config()
        mock_rule_alert_handler = rule_alert_handler.RuleAlertHandler()
        mock_request_get.return_value.json.return_value = _mock_prometheus_error_data()
        mock_node_one = _mock_v1_node("192.168.0.1", "mock-worker-one")
        mock_node_two = _mock_v1_node("192.168.0.2", "mock-worker-two")
        mock_node_list = V1NodeList(items=[mock_node_one, mock_node_two])
        mock_list_node.return_value = mock_node_list

        ecc_rule_instance = ECCDetectErrorRule(mock_rule_alert_handler, mock_rule_config)
        check_status_response = ecc_rule_instance.check_status()

        self.assertTrue(check_status_response)
        self.assertEqual(len(ecc_rule_instance.new_bad_nodes), 2)
        self.assertTrue("mock-worker-one" in ecc_rule_instance.new_bad_nodes)
        self.assertTrue("mock-worker-two" in ecc_rule_instance.new_bad_nodes)

    
    @mock.patch('utils.email_util.EmailHandler')
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler.load_config')
    @mock.patch('rules.ecc_detect_error_rule.k8s_util.list_node')
    @mock.patch('rules.ecc_detect_error_rule.requests.get')
    @mock.patch('rules.ecc_detect_error_rule.ECCDetectErrorRule.load_ecc_config')
    def test_check_status_ecc_error_already_detected(self, 
            mock_load_ecc_config,
            mock_request_get,
            mock_list_node,
            mock_rule_alert_handler_load_config,
            mock_email_handler):

        mock_rule_config = _mock_rule_config()
        mock_rule_alert_handler_load_config.return_value = mock_rule_config
        mock_load_ecc_config.return_value = _mock_ecc_config()
        mock_rule_alert_handler = rule_alert_handler.RuleAlertHandler()
        # nodes already detected in previous run
        mock_rule_alert_handler.rule_cache = {
            "ecc_rule": {
                "mock-worker-one": {
                    "time_found": "2020-02-18 21:14:20.351019",
                    "instance": "192.168.0.1"
                }
            }
        }
        mock_request_get.return_value.json.return_value = _mock_prometheus_error_data()
        node_one = _mock_v1_node("192.168.0.1", "mock-worker-one")
        node_two = _mock_v1_node("192.168.0.2", "mock-worker-two")
        mock_node_list = V1NodeList(items=[node_one, node_two])
        mock_list_node.return_value = mock_node_list

        ecc_rule_instance = ECCDetectErrorRule(mock_rule_alert_handler, mock_rule_config)
        check_status_response = ecc_rule_instance.check_status()

        self.assertTrue(check_status_response)
        self.assertEqual(len(ecc_rule_instance.new_bad_nodes), 1)
        self.assertTrue("mock-worker-two" in ecc_rule_instance.new_bad_nodes)


    @mock.patch('rules.ecc_detect_error_rule._get_node_address_info')
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler')
    @mock.patch('rules.ecc_detect_error_rule.k8s_util.list_node')
    @mock.patch('rules.ecc_detect_error_rule.requests.get')
    @mock.patch('rules.ecc_detect_error_rule.ECCDetectErrorRule.load_ecc_config')
    def test_check_status_ecc_error_not_found(self, 
            mock_load_ecc_config,
            mock_request_get,
            mock_list_node,
            mock_rule_alert_handler,
            mock_get_node_address_info):
        mock_load_ecc_config.return_value = _mock_ecc_config()

        mock_request_get.return_value.json.return_value = _mock_empty_prometheus_error_data()

        ecc_rule_instance = ECCDetectErrorRule(mock_rule_alert_handler, _mock_rule_config())
        check_status_response = ecc_rule_instance.check_status()

        self.assertFalse(check_status_response)
        self.assertEqual(len(ecc_rule_instance.new_bad_nodes), 0)


    @mock.patch('rules.ecc_detect_error_rule._create_email_for_dris')
    @mock.patch('rules.ecc_detect_error_rule.k8s_util.cordon_node')
    @mock.patch('rules.ecc_detect_error_rule.k8s_util.list_namespaced_pod')
    @mock.patch('utils.email_util.EmailHandler')
    @mock.patch('rules.ecc_detect_error_rule.ECCDetectErrorRule.load_ecc_config')
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler.load_config')
    def test_take_action_new_ecc_found(self,
            mock_load_rule_config,
            mock_load_ecc_config,
            mock_email_handler,
            mock_pod_list,
            mock_cordon_node,
            mock_create_email_for_dris):
        mock_rule_config = _mock_rule_config()
        mock_load_rule_config.return_value = mock_rule_config
        mock_load_ecc_config.return_value = _mock_ecc_config()

        alert = rule_alert_handler.RuleAlertHandler()
        ecc_rule_instance = ECCDetectErrorRule(alert, mock_rule_config)
        ecc_rule_instance.new_bad_nodes = {
            "mock_worker_one": "192.168.0.1",
            "mock_worker_two": "192.168.0.2"
        }

        pod_one = _mock_v1_pod("87654321-wxyz", "user1", "vc1", "node1")
        pod_two = _mock_v1_pod("12345678-abcd", "user2", "vc2", "node1")
        pod_three = _mock_v1_pod("12345678-abcd", "user2", "vc2", "node2")
        pod_four = _mock_v1_pod("99999999-efgh", "user3", "vc3", "node3")
        mock_pod_list.return_value = V1PodList(items=[pod_one, pod_two, pod_three, pod_four])

        ecc_rule_instance.take_action()

        self.assertEqual(2, mock_cordon_node.call_count)
        self.assertEqual(1, mock_create_email_for_dris.call_count)

        self.assertTrue("ecc_rule" in alert.rule_cache)
        self.assertTrue("mock_worker_one" in alert.rule_cache["ecc_rule"])
        self.assertEqual("192.168.0.1", alert.rule_cache["ecc_rule"]["mock_worker_one"]["instance"])
        self.assertTrue("mock_worker_two" in alert.rule_cache["ecc_rule"])
        self.assertEqual("192.168.0.2", alert.rule_cache["ecc_rule"]["mock_worker_two"]["instance"])


    @mock.patch('rules.ecc_detect_error_rule.k8s_util.list_namespaced_pod')
    @mock.patch('rules.ecc_detect_error_rule.k8s_util.cordon_node')
    @mock.patch('rules.ecc_detect_error_rule.k8s_util.is_node_cordoned')
    @mock.patch('utils.email_util.EmailHandler.load_config')
    @mock.patch('rules.ecc_detect_error_rule.ECCDetectErrorRule.load_ecc_config')
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler.load_config')
    def test_take_action_send_emails(self,
            mock_load_rule_config,
            mock_load_ecc_config,
            mock_email_load_config,
            mock_is_node_cordoned,
            mock_cordon_node,
            mock_pod_info):

        #####################################################
        ##  Please fill in SMTP info above to send emails  ##
        #####################################################
        enable_test = False
        ####################################################

        if enable_test:
            mock_load_ecc_config.return_value = _mock_ecc_config()
            mock_load_ecc_config.return_value["alert_job_owners"] = True
            mock_load_ecc_config.return_value["dri_email"] = DRI_EMAIL

            mock_email_load_config.return_value = {
                "smtp_url": SMTP_URL,
                "login": LOGIN,
                "password": PASSWORD,
                "sender": SENDER,
                "default_recepient": DRI_EMAIL

            }

            owner_email_split = JOB_OWNER_EMAIL.split('@')
            mock_job_owner_username = owner_email_split[0]
            mock_job_owner_email_domain = owner_email_split[1]

            # Mock Job and Job Owner Info
            pod_one = _mock_v1_pod("87654321-wxyz", mock_job_owner_username, "vc1", "mock_worker_one")
            pod_two = _mock_v1_pod("12345678-abcd", mock_job_owner_username, "vc2", "mock_worker_one")
            pod_three = _mock_v1_pod("12345678-abcd", mock_job_owner_username, "vc2", "mock_worker_two")
            pod_four = _mock_v1_pod("99999999-efgh", mock_job_owner_username, "vc3", "mock_worker_three")
            mock_pod_list = V1PodList(items=[pod_one, pod_two, pod_three, pod_four])
            mock_pod_info.return_value = mock_pod_list

            mock_cordon_node.return_value = "node cordoned successfully"

            alert = rule_alert_handler.RuleAlertHandler()

            # first node is schedulable
            # second node has already been marked as unschedulable
            mock_is_node_cordoned.side_effect = [False, True]

            mock_rule_config = _mock_rule_config()
            mock_rule_config["job_owner_email_domain"] = mock_job_owner_email_domain
            mock_load_rule_config.return_value = mock_rule_config

            ecc_rule_instance = ECCDetectErrorRule(alert, mock_rule_config)
            ecc_rule_instance.new_bad_nodes = {
                "mock_worker_one": "192.168.0.1",
                "mock_worker_two": "192.168.0.2"
            }
            
            ecc_rule_instance.take_action()


    @mock.patch('rules.ecc_detect_error_rule.k8s_util.list_namespaced_pod')
    @mock.patch('rules.ecc_detect_error_rule.k8s_util.cordon_node')
    @mock.patch('rules.ecc_detect_error_rule.k8s_util.is_node_cordoned')
    @mock.patch('utils.email_util.EmailHandler.load_config')
    @mock.patch('rules.ecc_detect_error_rule.ECCDetectErrorRule.load_ecc_config')
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler.load_config')
    def test_create_email_for_job_owner(self,
            mock_load_rule_config,
            mock_load_ecc_config,
            mock_email_load_config,
            mock_is_node_cordoned,
            mock_cordon_node,
            mock_pod_info):

        #####################################################
        ##  Please fill in SMTP info above to send emails  ##
        #####################################################
        enable_test = False
        ####################################################

        if enable_test:
            mock_load_ecc_config.return_value = _mock_ecc_config()
            mock_load_ecc_config.return_value["alert_job_owners"] = True
            mock_load_ecc_config.return_value["dri_email"] = DRI_EMAIL

            mock_email_load_config.return_value = {
                "smtp_url": SMTP_URL,
                "login": LOGIN,
                "password": PASSWORD,
                "sender": SENDER,
                "default_recepient": DRI_EMAIL
            }

            rule_alert_handler_instance = rule_alert_handler.RuleAlertHandler()

            # reboot_dry_run = True
            email_params = {
                "job_id": "job-abc-123",
                "job_owner_email":  JOB_OWNER_EMAIL,
                "node_names": ["node1", "node2"], 
                "job_link": "example.dlts.com/fake-cluster/fake-link",
                "cluster_name": "mock-cluster",
                "reboot_dry_run": True,
                "days_until_reboot": 5
            }
            message = ecc_detect_error_rule._create_email_for_job_owner(**email_params)
            rule_alert_handler_instance.send_alert(message)

            # reboot_dry_run = False
            email_params = {
                "job_id": "job-abc-123",
                "job_owner_email":  JOB_OWNER_EMAIL,
                "node_names": ["node1", "node2"], 
                "job_link": "example.dlts.com/fake-cluster/fake-link",
                "cluster_name": "mock-cluster",
                "reboot_dry_run": False,
                "days_until_reboot": 5
            }
            message = ecc_detect_error_rule._create_email_for_job_owner(**email_params)
            rule_alert_handler_instance.send_alert(message)            


if __name__ == '__main__':
    unittest.main()
