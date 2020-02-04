import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import mock
from datetime import datetime, timedelta, timezone
from rules import ecc_reboot_node_rule
from utils import rule_alert_handler
from kubernetes.client.models.v1_pod_list import V1PodList
from kubernetes.client.models.v1_pod import V1Pod
from kubernetes.client.models.v1_object_meta import V1ObjectMeta
from kubernetes.client.models.v1_pod_spec import V1PodSpec

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

    def test_extract_node_boot_time_info(self):
        mock_datetime_one = datetime.utcnow()
        mock_timestamp_one = mock_datetime_one.replace(tzinfo=timezone.utc).timestamp()

        mock_datetime_two = datetime.utcnow() + timedelta(days=1)
        mock_timestamp_two = mock_datetime_two.replace(tzinfo=timezone.utc).timestamp()


        mock_response = {
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [
                    {
                        "metric": {
                            "__name__": "node_boot_time_seconds",
                            "exporter_name": "node-exporter",
                            "instance": "192.168.0.1:9090",
                            "job": "serivce_exporter",
                            "scraped_from": "node-exporter-1"
                        },
                        "value": [1580517453.696, str(mock_timestamp_one)]},
                    {
                        "metric": {
                            "__name__": "node_boot_time_seconds",
                            "exporter_name": "node-exporter",
                            "instance": "192.168.0.2:9090",
                            "job": "serivce_exporter",
                            "scraped_from": "node-exporter-2"
                        },
                        "value": [1580517453.696, str(mock_timestamp_two)]
                    }]}}

        result_boot_times = ecc_reboot_node_rule._extract_node_boot_time_info(mock_response)

        self.assertTrue("192.168.0.1:9090" in result_boot_times)
        self.assertEqual(mock_datetime_one, result_boot_times["192.168.0.1:9090"])

        self.assertTrue("192.168.0.2:9090" in result_boot_times)
        self.assertEqual(mock_datetime_two, result_boot_times["192.168.0.2:9090"])


    def test_get_job_info_from_nodes(self):
        
        mock_nodes = {"node1", "node2"}

        pod_one = _mock_v1_pod("87654321-wxyz", "user1", "vc1", "node1")
        pod_two = _mock_v1_pod("12345678-abcd", "user2", "vc2", "node1")
        pod_three = _mock_v1_pod("12345678-abcd", "user2", "vc2", "node2")
        pod_four = _mock_v1_pod("99999999-efgh", "user3", "vc3", "node3")
        mock_pod_list = V1PodList(items=[pod_one, pod_two, pod_three, pod_four])
        
        job_info = ecc_reboot_node_rule._get_job_info_from_nodes(mock_nodes, mock_pod_list, "example.com")

        self.assertTrue("87654321-wxyz" in job_info)
        self.assertEqual("user1@example.com", job_info["87654321-wxyz"]["user_email"])
        self.assertTrue("12345678-abcd" in job_info)
        self.assertEqual("user2@example.com", job_info["12345678-abcd"]["user_email"])
        self.assertEqual(2, len(job_info))



    @mock.patch('rules.ecc_detect_error_rule.requests.get')
    @mock.patch('rules.ecc_reboot_node_rule.ECCRebootNodeRule.load_ecc_config')
    @mock.patch('utils.email_util.EmailHandler')
    def test_check_status_true(self, mock_email_handler,
                                mock_ecc_config,
                                mock_request_get):

        time_six_days_ago = datetime.now() - timedelta(days=6)

        time_five_days_ago = datetime.now() - timedelta(days=5, minutes=1)

        time_three_days_ago = datetime.now() - timedelta(days=3)

        time_one_days_ago = datetime.now() - timedelta(days=1)

        rule_alert_handler_instance = rule_alert_handler.RuleAlertHandler()
        rule_alert_handler_instance.rule_cache["ecc_rule"] = {
            # this node to be rebooted (> 5 days since first detected)
            "node1": {
                "time_found": time_five_days_ago,
                "instance": "192.168.0.1:9090"
            },
            "node2": {
                "time_found": time_three_days_ago,
                "instance": "192.168.0.2:9090"
            },
            "node3": {
                "time_found": time_three_days_ago,
                "instance": "192.168.0.3:9090"
            },
        }

        rule_config = {}

        mock_ecc_config.return_value = {
            "prometheus": {
                "ip": "localhost",
                "port": 9091,
                "node_boot_time_query": 'node_boot_time_seconds'
            },
            "days_until_node_reboot": 5
        }

        mock_request_get.return_value.json.return_value = {
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [
                    {
                        "metric": {
                            "__name__": "node_boot_time_seconds",
                            "exporter_name": "node-exporter",
                            "instance": "192.168.0.1:9090",
                            "job": "serivce_exporter",
                            "scraped_from": "node-exporter-1"
                        },
                        "value": [1580517453.696, str(time_six_days_ago.timestamp())]},
                    {
                        "metric": {
                            "__name__": "node_boot_time_seconds",
                            "exporter_name": "node-exporter",
                            "instance": "192.168.0.2:9090",
                            "job": "serivce_exporter",
                            "scraped_from": "node-exporter-2"
                        },
                        "value": [1580517453.696, str(time_six_days_ago.timestamp())]},
                    {
                        # this node to be removed from cache (reboot time < time ecc error found)
                        "metric": {
                            "__name__": "node_boot_time_seconds",
                            "exporter_name": "node-exporter",
                            "instance": "192.168.0.3:9090",
                            "job": "serivce_exporter",
                            "scraped_from": "node-exporter-3"
                        },
                        "value": [1580517453.696, str(time_one_days_ago.timestamp())]},
                    ]}}

        ecc_reboot_node_rule_instance = ecc_reboot_node_rule.ECCRebootNodeRule(rule_alert_handler_instance, rule_config)

        response = ecc_reboot_node_rule_instance.check_status()

        self.assertTrue(response)
        self.assertEqual(1, len(ecc_reboot_node_rule_instance.nodes_ready_for_action))
        self.assertEqual("node1", ecc_reboot_node_rule_instance.nodes_ready_for_action[0])
        self.assertTrue("node3" not in rule_alert_handler_instance.rule_cache["ecc_rule"])


    @mock.patch('rules.ecc_detect_error_rule.requests.get')
    @mock.patch('rules.ecc_reboot_node_rule.ECCRebootNodeRule.load_ecc_config')
    @mock.patch('utils.email_util.EmailHandler')
    def test_check_status_false(self, mock_email_handler, 
                                mock_ecc_config,
                                mock_request_get):

        time_three_days_ago = datetime.now() - timedelta(days=3)

        rule_alert_handler_instance = rule_alert_handler.RuleAlertHandler()
        rule_alert_handler_instance.rule_cache["ecc_rule"] = {
            "node1": {
                "time_found": time_three_days_ago
            }
        }

        rule_config = {}

        mock_ecc_config.return_value = {
            "prometheus": {
                "ip": "localhost",
                "port": 9091,
                "node_boot_time_query": 'node_boot_time_seconds'
            },
            "days_until_node_reboot": 5
        }

        ecc_reboot_node_rule_instance = ecc_reboot_node_rule.ECCRebootNodeRule(rule_alert_handler_instance, rule_config)

        response = ecc_reboot_node_rule_instance.check_status()

        self.assertFalse(response)
        self.assertEqual(0, len(ecc_reboot_node_rule_instance.nodes_ready_for_action))

    @mock.patch('rules.ecc_detect_error_rule.k8s_util.list_pod_for_all_namespaces')
    @mock.patch('rules.ecc_reboot_node_rule.ECCRebootNodeRule.load_ecc_config')
    @mock.patch('utils.email_util.EmailHandler')
    @mock.patch('rules.ecc_detect_error_rule.requests.get')
    @mock.patch('rules.ecc_reboot_node_rule._get_job_status')
    @mock.patch('rules.ecc_reboot_node_rule._pause_job')
    def test_take_action(self, mock_pause_job,
                               mock_get_job_status, 
                               mock_get_requests,
                               mock_email_handler,
                               mock_load_ecc_config,
                               mock_list_pods):

        mock_pause_job.return_value = {
            "result": "Success, the job is scheduled to be paused."
        }

        rule_alert_handler_instance = rule_alert_handler.RuleAlertHandler()
        rule_alert_handler_instance.rule_cache["ecc_rule"] = {
            "node1": {
                "instance": "192.168.0.1:9090"
            },
            "node2": {
                "instance": "192.168.0.2:9090"
            },
            "node3": {
                "instance": "192.168.0.3:9090"
            }
        }

        rule_config = {
            "job_owner_email_domain": "example.com"
        }

        mock_load_ecc_config.return_value = {
            "days_until_node_reboot": 5,
            "job_pause_resume_url": "http://localhost:5000",
            "time_sleep_after_pausing": 0
        }

        pod_one = _mock_v1_pod("87654321-wxyz", "user1", "vc1", "node1")
        pod_two = _mock_v1_pod("12345678-abcd", "user2", "vc2", "node1")
        pod_three = _mock_v1_pod("99999999-efgh", "user3", "vc3", "node3")
        mock_pod_list = V1PodList(items=[pod_one, pod_two, pod_three])
        mock_list_pods.return_value = mock_pod_list

        mock_get_job_status.return_value = {
            "errorMsg": None,
            "jobStatus":"paused",
            "jobTime":"Thu, 30 Jan 2020 23:43:00 GMT"
            }

        ecc_reboot_node_rule_instance = ecc_reboot_node_rule.ECCRebootNodeRule(rule_alert_handler_instance, rule_config)
        ecc_reboot_node_rule_instance.nodes_ready_for_action = ["node1", "node3"]

        ecc_reboot_node_rule_instance.take_action()

        self.assertTrue("node1" not in rule_alert_handler_instance.rule_cache["ecc_rule"])
        self.assertTrue("node2" in rule_alert_handler_instance.rule_cache["ecc_rule"])
        self.assertTrue("node3" not in rule_alert_handler_instance.rule_cache["ecc_rule"])
        self.assertEqual(1, len(rule_alert_handler_instance.rule_cache["ecc_rule"]))



if __name__ == '__main__':
    unittest.main()
