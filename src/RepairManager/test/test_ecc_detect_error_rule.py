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

    def test_get_node_address_info(self):
        node_one = _mock_v1_node("192.168.0.1", "mock-worker-one")
        node_two = _mock_v1_node("192.168.0.2", "mock-worker-two")
        mock_node_list = V1NodeList(items=[node_one, node_two])

        address_info = ecc_detect_error_rule.get_node_address_info(mock_node_list)

        self.assertEqual(len(address_info), 2)
        self.assertTrue('192.168.0.1' in address_info)
        self.assertEqual(address_info['192.168.0.1'], "mock-worker-one")
        self.assertTrue('192.168.0.2' in address_info)
        self.assertEqual(address_info['192.168.0.2'], "mock-worker-two")


    def test_get_node_address_info_empty(self):
        mock_node_list = V1NodeList(items=[])
        address_info = ecc_detect_error_rule.get_node_address_info(mock_node_list)
        self.assertEqual(len(address_info), 0)

    
    def test_extract_ips_from_ecc_data(self):
        prometheus_error_data = {
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

        ecc_node_ips = ecc_detect_error_rule.extract_ips_from_ecc_data(prometheus_error_data)

        self.assertEqual(len(ecc_node_ips), 2)
        self.assertTrue('192.168.0.1' in ecc_node_ips)
        self.assertTrue('192.168.0.2' in ecc_node_ips)


    def test_extract_ips_from_ecc_data_None(self):
        prometheus_error_data = {
            "status":
                "success",
                "data": {
                    "result": []
                }
        }

        ecc_node_ips = ecc_detect_error_rule.extract_ips_from_ecc_data(prometheus_error_data)

        self.assertIsNone(ecc_node_ips)


    @mock.patch('rules.ecc_detect_error_rule.get_node_address_info')
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler')
    @mock.patch('rules.ecc_detect_error_rule.k8s_util.list_node')
    @mock.patch('rules.ecc_detect_error_rule.requests.get')
    @mock.patch('rules.ecc_detect_error_rule.ECCDetectErrorRule.load_ecc_config')
    def test_check_status_ecc_error_found(self, 
            mock_load_ecc_config,
            mock_request_get,
            mock_list_node,
            mock_rule_alert_handler,
            mock_get_node_address_info):

        rule_config = {}

        mock_load_ecc_config.return_value = {
            "prometheus": {
                "ip": "localhost",
                "port": 9091,
                "ecc_error_query": 'nvidiasmi_ecc_error_count{type="volatile_double"}>0',
                "step": "1m",
                "interval": 9,
                "percent_threshold": 90
            }
        }


        mock_request_get.return_value.json.return_value = {
            "status":
                "success",
                "data": {
                    "result": [{
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
                            [1578453042, "2"], [1578453042, "2"],
                            [1578453042, "2"], [1578453042, "2"],
                            [1578453042, "2"], [1578453042, "2"],
                            [1578453042, "2"], [1578453042, "2"],
                            [1578453042, "2"]   
                        ]
                    }]
                }
        }

        mock_get_node_address_info.return_value = {
            "192.168.0.1": "mock-worker-one",
            "192.168.0.2": "mock-worker-two"
        }

        ecc_rule_instance = ECCDetectErrorRule(mock_rule_alert_handler, rule_config)
        check_status_response = ecc_rule_instance.check_status()

        self.assertTrue(check_status_response)
        self.assertEqual(len(ecc_rule_instance.ecc_node_hostnames), 1)
        self.assertEqual(ecc_rule_instance.ecc_node_hostnames[0], "mock-worker-two")


    @mock.patch('rules.ecc_detect_error_rule.get_node_address_info')
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

        rule_config = {}

        mock_load_ecc_config.return_value = {
            "prometheus": {
                "ip": "localhost",
                "port": 9091,
                "ecc_error_query": 'nvidiasmi_ecc_error_count{type="volatile_double"}>0',
                "step": "1m",
                "interval": 9,
                "percent_threshold": 90
            }
        }


        mock_request_get.return_value.json.return_value = {
            "status":
                "success",
                "data": {
                    "result": []
                }
        }

        mock_get_node_address_info.return_value = {
            "192.168.0.1": "mock-worker-one",
            "192.168.0.2": "mock-worker-two"
        }

        ecc_rule_instance = ECCDetectErrorRule(mock_rule_alert_handler, rule_config)
        check_status_response = ecc_rule_instance.check_status()

        self.assertFalse(check_status_response)
        self.assertEqual(len(ecc_rule_instance.ecc_node_hostnames), 0)


    @mock.patch('rules.ecc_detect_error_rule.ECCDetectErrorRule.create_email_for_DRIs')
    @mock.patch('rules.ecc_detect_error_rule.k8s_util.cordon_node')
    @mock.patch('rules.ecc_detect_error_rule.k8s_util.is_node_cordoned')
    @mock.patch('utils.email_util.EmailHandler')
    @mock.patch('rules.ecc_detect_error_rule.ECCDetectErrorRule.load_ecc_config')
    def test_take_action_new_ecc_found(self,
            mock_load_ecc_config,
            mock_email_handler,
            mock_is_node_cordoned,
            mock_cordon_node,
            mock_create_email_for_DRIs):

        rule_config = {
            "cluster_name": "mock_cluster"
        }

        mock_load_ecc_config.return_value = {
            "cordon_dry_run": False,
            "prometheus": {
                "ip": "localhost",
                "port": 9091,
                "ecc_error_query": 'nvidiasmi_ecc_error_count{type="volatile_double"}>0',
                "step": "1m",
                "interval": 9,
                "percent_threshold": 90
            },
            "alert_job_owners": False
        }

        # second node is already cordoned
        mock_is_node_cordoned.side_effect = [False, True]

        alert = rule_alert_handler.RuleAlertHandler()
        ecc_rule_instance = ECCDetectErrorRule(alert, rule_config)
        ecc_rule_instance.ecc_node_hostnames = {"mock_worker_one", "mock_worker_two"}

        ecc_rule_instance.take_action()

        # assert only one node was cordoned
        self.assertEqual(1, mock_cordon_node.call_count)

        # assert DRIs were alerted for both nodes
        self.assertEqual(2, mock_create_email_for_DRIs.call_count)

        # assert rule cache is updated for both nodes
        self.assertTrue("ecc_rule" in alert.rule_cache)
        self.assertTrue("mock_worker_one" in alert.rule_cache["ecc_rule"])
        self.assertTrue("mock_worker_two" in alert.rule_cache["ecc_rule"])



    @mock.patch('rules.ecc_detect_error_rule.ECCDetectErrorRule.create_email_for_DRIs')
    @mock.patch('rules.ecc_detect_error_rule.k8s_util.cordon_node')
    @mock.patch('rules.ecc_detect_error_rule.k8s_util.is_node_cordoned')
    @mock.patch('utils.email_util.EmailHandler')
    @mock.patch('rules.ecc_detect_error_rule.ECCDetectErrorRule.load_ecc_config')
    def test_take_action_new_ecc_not_found(self,
            mock_load_ecc_config,
            mock_email_handler,
            mock_is_node_cordoned,
            mock_cordon_node,
            mock_create_email_for_DRIs):

        rule_config = {
            "cluster_name": "mock_cluster"
        }

        mock_load_ecc_config.return_value = {
            "cordon_dry_run": False,
            "prometheus": {
                "ip": "localhost",
                "port": 9091,
                "ecc_error_query": 'nvidiasmi_ecc_error_count{type="volatile_double"}>0',
                "step": "1m",
                "interval": 9,
                "percent_threshold": 90
            },
            "alert_job_owners": False
        }

        alert = rule_alert_handler.RuleAlertHandler()
        # simulate ecc error detected in previous run
        alert.rule_cache["ecc_rule"] = {
            "mock_worker_one": {"time_found": datetime.datetime.now},
            "mock_worker_two": {"time_found": datetime.datetime.now}
            }

        # second node is already cordoned
        mock_is_node_cordoned.side_effect = [False, True]

        ecc_rule_instance = ECCDetectErrorRule(alert, rule_config)
        ecc_rule_instance.ecc_node_hostnames = {"mock_worker_one", "mock_worker_two"}
        ecc_rule_instance.take_action()

        # assert only one node was cordoned
        self.assertEqual(1, mock_cordon_node.call_count)

        # assert DRIs were alerted for one of the nodes
        self.assertEqual(1, mock_create_email_for_DRIs.call_count)


    @mock.patch('rules.ecc_detect_error_rule.k8s_util.list_pod_for_all_namespaces')
    def test_get_job_info_from_nodes(self, mock_pod_info):
        pod_one = _mock_v1_pod("87654321-wxyz", "user1", "vc1", "node1")
        pod_two = _mock_v1_pod("12345678-abcd", "user2", "vc2", "node1")
        pod_three = _mock_v1_pod("12345678-abcd", "user2", "vc2", "node2")
        pod_four = _mock_v1_pod("99999999-efgh", "user3", "vc3", "node3")
        mock_pod_list = V1PodList(items=[pod_one, pod_two, pod_three, pod_four])
        mock_pod_info.return_value = mock_pod_list

        job_response = ecc_detect_error_rule.get_job_info_from_nodes(["node1", "node2"], "cluster1")

        self.assertTrue("87654321-wxyz" in job_response)
        self.assertEqual(1, len(job_response["87654321-wxyz"]["nodeName"]))
        self.assertTrue("node1" in job_response["87654321-wxyz"]["nodeName"])
        self.assertEqual("/job/vc1/cluster1/87654321-wxyz", job_response["87654321-wxyz"]["jobLink"])

        self.assertTrue("12345678-abcd" in job_response)
        self.assertEqual(2, len(job_response["12345678-abcd"]["nodeName"]))
        self.assertTrue("node1" in job_response["12345678-abcd"]["nodeName"])
        self.assertTrue("node2" in job_response["12345678-abcd"]["nodeName"])
        self.assertEqual("/job/vc2/cluster1/12345678-abcd", job_response["12345678-abcd"]["jobLink"])


    ###############################################################################
    ###        Please uncomment and fill in [CONFIGURATIONS] below              ###
    ###         to test and receive emails                                      ###
    ###############################################################################
    # @mock.patch('rules.ecc_detect_error_rule.k8s_util.list_pod_for_all_namespaces')
    # @mock.patch('rules.ecc_detect_error_rule.k8s_util.cordon_node')
    # @mock.patch('rules.ecc_detect_error_rule.k8s_util.is_node_cordoned')
    # @mock.patch('utils.email_util.EmailHandler.load_config')
    # @mock.patch('rules.ecc_detect_error_rule.ECCDetectErrorRule.load_ecc_config')
    # def test_take_action_send_emails(self,
    #         mock_load_ecc_config,
    #         mock_email_load_config,
    #         mock_is_node_cordoned,
    #         mock_cordon_node,
    #         mock_pod_info):
    
    #     # Mock Job and Job Owner Info
    #     pod_one = _mock_v1_pod("87654321-wxyz", "[JOB_OWNER_USERNAME]", "vc1", "mock_worker_one")
    #     pod_two = _mock_v1_pod("12345678-abcd", "[JOB_OWNER_USERNAME]", "vc2", "mock_worker_one")
    #     pod_three = _mock_v1_pod("12345678-abcd", "[JOB_OWNER_USERNAME]", "vc2", "mock_worker_two")
    #     pod_four = _mock_v1_pod("99999999-efgh", "[JOB_OWNER_USERNAME]", "vc3", "mock_worker_three")
    #     mock_pod_list = V1PodList(items=[pod_one, pod_two, pod_three, pod_four])
    #     mock_pod_info.return_value = mock_pod_list

    #     rule_config = {
    #         "cluster_name": "Mock-Cluster"
    #     }

    #     mock_load_ecc_config.return_value = {
    #         "cordon_dry_run": False,
    #         "prometheus": {
    #             "ip": "localhost",
    #             "port": 9091,
    #             "ecc_error_query": 'nvidiasmi_ecc_error_count{type="volatile_double"}>0',
    #             "step": "1m",
    #             "interval": 9
    #         },
    #         "alert_job_owners": True,
    #         "job_owner_domain": '[JOB_OWNER_DOMAIN]',

    #         "days_until_node_reboot": 5,

    #         "dri_email": "[DRI_EMAIL]"
    #     }

    #     mock_email_load_config.return_value = {
    #         "smtp_url": '[SMTP_URL]',
    #         "login": '[LOGIN]',
    #         "password": '[PASSWORD]',
    #         "sender": '[SENDER]'
    #     }

    #     mock_cordon_node.return_value = "node cordoned successfully"

    #     alert = rule_alert_handler.RuleAlertHandler()

    #     # second node is already cordoned
    #     mock_is_node_cordoned.side_effect = [False, True]

    #     ecc_rule_instance = ECCDetectErrorRule(alert, rule_config)
    #     ecc_rule_instance.ecc_node_hostnames = {"mock_worker_one", "mock_worker_two"}
    #     ecc_rule_instance.take_action()


if __name__ == '__main__':
    unittest.main()
