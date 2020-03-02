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


def _mock_rule_config():
    rule_config = {
        "cluster_name": "mock-cluster",
        "portal_url": "dltshub.example.com",
        "job_owner_email_domain": "example.com",
        "restore_from_rule_cache_dump": False,
        "date_time_format": "%Y-%m-%d %H:%M:%S.%f"
    }

    return rule_config

def _mock_ecc_config():
    ecc_config = {
        "prometheus": {
            "ip": "localhost",
            "port": 9091,
            "node_boot_time_query": 'node_boot_time_seconds'
        },
        "dri_email": 'dri@example.com',
        "rest_url": "http://localhost:5000",
        "time_sleep_after_pausing": 0,
        "attempts_for_pause_resume_job": 1,
        "alert_job_owners": False,
        "days_until_node_reboot": 5,
        "reboot_dry_run": False
    }

    return ecc_config


def _mock_prometheus_node_boot_time_response(node_boot_times):
    mock_response = {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": []
        }
    }

    for node_ip in node_boot_times:
        metric = {
            "metric": {
                "__name__": "node_boot_time_seconds",
                            "exporter_name": "node-exporter",
                            "instance": f"{node_ip}:9090",
                            "job": "serivce_exporter",
                            "scraped_from": "node-exporter"
            },
            "value": [1580517453.696, node_boot_times[node_ip]]
        }
        mock_response["data"]["result"].append(metric)

    return mock_response

class Testing(unittest.TestCase):

    def test_extract_node_boot_time_info(self):
        mock_datetime_one = datetime.utcnow()
        mock_timestamp_one = mock_datetime_one.replace(tzinfo=timezone.utc).timestamp()

        mock_datetime_two = datetime.utcnow() + timedelta(days=1)
        mock_timestamp_two = str(mock_datetime_two.replace(tzinfo=timezone.utc).timestamp())

        node_boot_times = {
            "192.168.0.1": str(mock_timestamp_one),
            "192.168.0.2": str(mock_timestamp_two)
        }
        prometheus_resp = _mock_prometheus_node_boot_time_response(node_boot_times)


        result_boot_times = ecc_reboot_node_rule._extract_node_boot_time_info(prometheus_resp)


        self.assertTrue("192.168.0.1" in result_boot_times)
        self.assertEqual(mock_datetime_one, result_boot_times["192.168.0.1"])

        self.assertTrue("192.168.0.2" in result_boot_times)
        self.assertEqual(mock_datetime_two, result_boot_times["192.168.0.2"])


    @mock.patch('rules.ecc_detect_error_rule.requests.get')
    @mock.patch('rules.ecc_reboot_node_rule.ECCRebootNodeRule.load_ecc_config')
    @mock.patch('utils.email_util.EmailHandler')
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler.load_config')
    def test_check_status_time_to_take_action(self,
            mock_load_rule_config,
            mock_email_handler,
            mock_ecc_config,
            mock_request_get):

        rule_config = _mock_rule_config()
        mock_load_rule_config.return_value = rule_config

        mock_ecc_config.return_value = _mock_ecc_config()
        mock_ecc_config.return_value["days_until_node_reboot"] = 5

        time_six_days_ago = datetime.utcnow() - timedelta(days=6)
        time_five_days_ago = datetime.utcnow() - timedelta(days=5, minutes=1)

        #  ecc error detection occured in previous iteration
        rule_alert_handler_instance = rule_alert_handler.RuleAlertHandler()
        rule_alert_handler_instance.rule_cache["ecc_rule"] = {
            "node1": {
                "time_found": time_five_days_ago.strftime(rule_config['date_time_format']),
                "instance": "192.168.0.1"
            }
        }

        node_boot_times = {
            "192.168.0.1": str(time_six_days_ago.replace(tzinfo=timezone.utc).timestamp())
        }
        mock_request_get.return_value.json.return_value = _mock_prometheus_node_boot_time_response(node_boot_times)


        ecc_reboot_node_rule_instance = ecc_reboot_node_rule.ECCRebootNodeRule(rule_alert_handler_instance, rule_config)
        response = ecc_reboot_node_rule_instance.check_status()


        self.assertTrue(response)
        self.assertEqual(1, len(ecc_reboot_node_rule_instance.nodes_ready_for_action))
        self.assertEqual("node1", ecc_reboot_node_rule_instance.nodes_ready_for_action[0])


    @mock.patch('rules.ecc_detect_error_rule.requests.get')
    @mock.patch('rules.ecc_reboot_node_rule.ECCRebootNodeRule.load_ecc_config')
    @mock.patch('utils.email_util.EmailHandler')
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler.load_config')
    def test_check_status_node_rebooted_after_detection(self,
            mock_load_rule_config,
            mock_email_handler,
            mock_ecc_config,
            mock_request_get):

        rule_config = _mock_rule_config()
        mock_load_rule_config.return_value = rule_config

        mock_ecc_config.return_value = _mock_ecc_config()
        mock_ecc_config.return_value["days_until_node_reboot"] = 5

        time_one_days_ago = datetime.utcnow() - timedelta(days=1)
        now = datetime.utcnow()

        #  ecc error detection occured in previous iteration
        rule_alert_handler_instance = rule_alert_handler.RuleAlertHandler()
        rule_alert_handler_instance.rule_cache["ecc_rule"] = {
            "node1": {
                "time_found": time_one_days_ago.strftime(rule_config['date_time_format']),
                "instance": "192.168.0.1"
            }
        }

        # node rebooted *after* initial ecc error detection
        node_boot_times = {
            "192.168.0.1": str(now.replace(tzinfo=timezone.utc).timestamp())
        }
        mock_request_get.return_value.json.return_value = _mock_prometheus_node_boot_time_response(node_boot_times)


        ecc_reboot_node_rule_instance = ecc_reboot_node_rule.ECCRebootNodeRule(rule_alert_handler_instance, rule_config)
        response = ecc_reboot_node_rule_instance.check_status()


        self.assertFalse(response)
        self.assertEqual(0, len(ecc_reboot_node_rule_instance.nodes_ready_for_action))
        self.assertTrue("node1" not in rule_alert_handler_instance.rule_cache["ecc_rule"])


    @mock.patch('rules.ecc_detect_error_rule.requests.get')
    @mock.patch('rules.ecc_reboot_node_rule.ECCRebootNodeRule.load_ecc_config')
    @mock.patch('utils.email_util.EmailHandler')
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler.load_config')
    def test_check_status_no_action_needed(self,
        mock_load_rule_config,
        mock_email_handler, 
        mock_ecc_config,
        mock_request_get):

        rule_config = _mock_rule_config()
        mock_load_rule_config.return_value = rule_config

        mock_ecc_config.return_value = _mock_ecc_config()
        mock_ecc_config.return_value["days_until_node_reboot"] = 5

        time_two_days_ago = datetime.utcnow() - timedelta(days=2)
        time_three_days_ago = datetime.utcnow() - timedelta(days=3)

        #  ecc error detection occured in previous iteration
        rule_alert_handler_instance = rule_alert_handler.RuleAlertHandler()
        rule_alert_handler_instance.rule_cache["ecc_rule"] = {
            "node1": {
                "time_found": time_two_days_ago.strftime(rule_config['date_time_format']),
                "instance": "192.168.0.1"
            }
        }

        # node rebooted *before* initial ecc error detection
        node_boot_times = {
            "192.168.0.1": str(time_three_days_ago.replace(tzinfo=timezone.utc).timestamp())
        }
        mock_request_get.return_value.json.return_value = _mock_prometheus_node_boot_time_response(node_boot_times)


        ecc_reboot_node_rule_instance = ecc_reboot_node_rule.ECCRebootNodeRule(rule_alert_handler_instance, rule_config)
        response = ecc_reboot_node_rule_instance.check_status()


        self.assertFalse(response)
        self.assertEqual(0, len(ecc_reboot_node_rule_instance.nodes_ready_for_action))


    @mock.patch('utils.k8s_util.list_namespaced_pod')
    @mock.patch('rules.ecc_reboot_node_rule.ECCRebootNodeRule.load_ecc_config')
    @mock.patch('utils.email_util.EmailHandler')
    @mock.patch('requests.get')
    @mock.patch('rules.ecc_reboot_node_rule._create_email_for_pause_resume_job')
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler.load_config')
    def test_take_action(self, 
        mock_load_rule_config,
        mock_create_email_for_pause_resume_job,
        mock_get_requests,
        mock_email_handler,
        mock_load_ecc_config,
        mock_list_pods):

        rule_config = _mock_rule_config()
        mock_load_rule_config.return_value = rule_config

        mock_load_ecc_config.return_value = _mock_ecc_config()
        mock_load_ecc_config.return_value["alert_job_owners"] = True

        mock_get_requests.return_value.json.side_effect = [
            # job 1
            {"result": "Success, job paused."},
            {"errorMsg": None,
            "jobStatus": "paused",
            "jobTime": "Thu, 30 Jan 2020 23:43:00 GMT"},
            {"result": "Success, job resumed."},
            # job 2
            {"result": "Success, job paused."},
            {"errorMsg": None,
            "jobStatus": "paused",
            "jobTime": "Thu, 30 Jan 2020 23:43:00 GMT"},
            {"result": "Success, job resumed."},
            # job 3
            {"result": "Success, job paused."},
            {"errorMsg": None,
            "jobStatus": "paused",
            "jobTime": "Thu, 30 Jan 2020 23:43:00 GMT"},
            {"result": "Success, job resumed."}
        ]

        rule_alert_handler_instance = rule_alert_handler.RuleAlertHandler()
        rule_alert_handler_instance.rule_cache["ecc_rule"] = {
            "node1": {"instance": "192.168.0.1:9090"},
            "node2": {"instance": "192.168.0.2:9090"},
            "node3": {"instance": "192.168.0.3:9090"}
        }

        pod_one = _mock_v1_pod("87654321-wxyz", "user1", "vc1", "node1")
        pod_two = _mock_v1_pod("12345678-abcd", "user2", "vc2", "node1")
        pod_three = _mock_v1_pod("99999999-efgh", "user3", "vc3", "node3")
        mock_pod_list = V1PodList(items=[pod_one, pod_two, pod_three])
        mock_list_pods.return_value = mock_pod_list

        ecc_reboot_node_rule_instance = ecc_reboot_node_rule.ECCRebootNodeRule(rule_alert_handler_instance, rule_config)
        ecc_reboot_node_rule_instance.nodes_ready_for_action = ["node1", "node3"]

        ecc_reboot_node_rule_instance.take_action()

        self.assertEqual(3, mock_create_email_for_pause_resume_job.call_count)

    @mock.patch('rules.ecc_reboot_node_rule._create_email_for_issue_with_pause_resume_job')
    @mock.patch('rules.ecc_detect_error_rule.k8s_util.list_namespaced_pod')
    @mock.patch('rules.ecc_reboot_node_rule.ECCRebootNodeRule.load_ecc_config')
    @mock.patch('utils.email_util.EmailHandler')
    @mock.patch('rules.ecc_detect_error_rule.requests.get')
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler.load_config')
    def test_take_action_pause_failed(self, 
        mock_load_rule_config,
        mock_get_requests,
        mock_email_load_config,
        mock_load_ecc_config,
        mock_list_pods,
        mock_create_email_for_issue_with_pause_resume_job):

        rule_config = _mock_rule_config()
        mock_load_rule_config.return_value = rule_config

        mock_load_ecc_config.return_value = _mock_ecc_config()
        mock_load_ecc_config.return_value["alert_job_owners"] = True

        mock_get_requests.return_value.json.return_value = {"result": "Sorry, something went wrong."}

        rule_alert_handler_instance = rule_alert_handler.RuleAlertHandler()
        rule_alert_handler_instance.rule_cache["ecc_rule"] = {
            "node1": {"instance": "192.168.0.1:9090"}
        }

        pod_one = _mock_v1_pod("87654321-wxyz", "user1", "vc1", "node1")
        mock_pod_list = V1PodList(items=[pod_one])
        mock_list_pods.return_value = mock_pod_list

        ecc_reboot_node_rule_instance = ecc_reboot_node_rule.ECCRebootNodeRule(rule_alert_handler_instance, rule_config)
        ecc_reboot_node_rule_instance.nodes_ready_for_action = ["node1"]

        ecc_reboot_node_rule_instance.take_action()

        self.assertEqual(1, mock_create_email_for_issue_with_pause_resume_job.call_count)


if __name__ == '__main__':
    unittest.main()
