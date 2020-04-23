import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import mock
from datetime import datetime, timedelta, timezone
from rules import ecc_reboot_node_rule
from utils import rule_alert_handler, test_util

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

class TestEccRebootNodeRule(unittest.TestCase):

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


    @mock.patch('utils.k8s_util.list_namespaced_pod')
    @mock.patch('requests.get')
    @mock.patch('rules.ecc_reboot_node_rule.EccRebootNodeRule.load_etcd_config')
    @mock.patch('rules.ecc_reboot_node_rule.EccRebootNodeRule.load_ecc_config')
    @mock.patch('utils.email_util.EmailHandler')
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler.load_config')
    def test_check_status_node_due_for_reboot(self,
            mock_load_rule_config,
            mock_email_handler,
            mock_load_ecc_config,
            mock_load_etcd_config,
            mock_request_get,
            mock_pod_list):

        rule_config = test_util.mock_rule_config()
        mock_load_rule_config.return_value = rule_config

        etcd_config = test_util.mock_etcd_config()
        mock_load_etcd_config.return_value = etcd_config

        mock_load_ecc_config.return_value = test_util.mock_ecc_config()
        mock_load_ecc_config.return_value["days_until_node_reboot"] = 5

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

        # reboot is due to be rebooted (exceeded configured deadline), should trigger take action
        node_boot_times = {
            "192.168.0.1": str(time_six_days_ago.replace(tzinfo=timezone.utc).timestamp())
        }
        mock_request_get.return_value.json.return_value = _mock_prometheus_node_boot_time_response(node_boot_times)
        
        # at least one job running on the node
        mock_pod_list.return_value = test_util.mock_v1_pod_list([
            {
                "job_name": "87654321-wxyz",
                "user_name": "user1",
                "vc_name": "vc1",
                "node_name": "node1"
            }
        ])

        ecc_reboot_node_rule_instance = ecc_reboot_node_rule.EccRebootNodeRule(rule_alert_handler_instance, rule_config)
        response = ecc_reboot_node_rule_instance.check_status()

        self.assertTrue(response)
        self.assertEqual(1, len(ecc_reboot_node_rule_instance.nodes_ready_for_action))
        self.assertTrue("node1" in ecc_reboot_node_rule_instance.nodes_ready_for_action)
        self.assertEqual(1, len(ecc_reboot_node_rule_instance.jobs_ready_for_migration))
        self.assertTrue("87654321-wxyz" in ecc_reboot_node_rule_instance.jobs_ready_for_migration)

    
    @mock.patch('utils.k8s_util.list_namespaced_pod')
    @mock.patch('requests.get')
    @mock.patch('rules.ecc_reboot_node_rule.EccRebootNodeRule.load_etcd_config')
    @mock.patch('rules.ecc_reboot_node_rule.EccRebootNodeRule.load_ecc_config')
    @mock.patch('utils.email_util.EmailHandler')
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler.load_config')
    def test_check_status_no_jobs_running(self,
            mock_load_rule_config,
            mock_email_handler,
            mock_load_ecc_config,
            mock_load_etcd_config,
            mock_request_get,
            mock_pod_list):

        rule_config = test_util.mock_rule_config()
        mock_load_rule_config.return_value = rule_config

        etcd_config = test_util.mock_etcd_config()
        mock_load_etcd_config.return_value = etcd_config

        mock_load_ecc_config.return_value = test_util.mock_ecc_config()
        mock_load_ecc_config.return_value["days_until_node_reboot"] = 5

        time_two_days_ago = datetime.utcnow() - timedelta(days=2)

        rule_alert_handler_instance = rule_alert_handler.RuleAlertHandler()
        rule_alert_handler_instance.rule_cache["ecc_rule"] = {
            "node1": {
                "time_found": time_two_days_ago.strftime(rule_config['date_time_format']),
                "instance": "192.168.0.1"
            }
        }

        # node not due to be rebooted
        node_boot_times = {
            "192.168.0.1": str(time_two_days_ago.replace(tzinfo=timezone.utc).timestamp())
        }
        mock_request_get.return_value.json.return_value = _mock_prometheus_node_boot_time_response(node_boot_times)

        # no pods running on node, should trigger take action
        mock_pod_list.return_value = test_util.mock_v1_pod_list([])

        ecc_reboot_node_rule_instance = ecc_reboot_node_rule.EccRebootNodeRule(rule_alert_handler_instance, rule_config)
        response = ecc_reboot_node_rule_instance.check_status()


        self.assertTrue(response)
        self.assertEqual(1, len(ecc_reboot_node_rule_instance.nodes_ready_for_action))
        self.assertTrue("node1" in ecc_reboot_node_rule_instance.nodes_ready_for_action)
        self.assertEqual(0, len(ecc_reboot_node_rule_instance.jobs_ready_for_migration))

    @mock.patch('rules.ecc_detect_error_rule.k8s_util.uncordon_node')
    @mock.patch('utils.k8s_util.list_namespaced_pod')
    @mock.patch('requests.get')
    @mock.patch('rules.ecc_reboot_node_rule.EccRebootNodeRule.load_etcd_config')
    @mock.patch('rules.ecc_reboot_node_rule.EccRebootNodeRule.load_ecc_config')
    @mock.patch('utils.email_util.EmailHandler')
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler.load_config')
    def test_check_status_node_rebooted_after_detection(self,
            mock_load_rule_config,
            mock_email_handler,
            mock_load_ecc_config,
            mock_load_etcd_config,
            mock_request_get,
            mock_pod_list,
            mock_uncordon_node):

        rule_config = test_util.mock_rule_config()
        mock_load_rule_config.return_value = rule_config

        etcd_config = test_util.mock_etcd_config()
        mock_load_etcd_config.return_value = etcd_config

        mock_load_ecc_config.return_value = test_util.mock_ecc_config()
        mock_load_ecc_config.return_value["days_until_node_reboot"] = 5

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

        mock_pod_list.return_value = test_util.mock_v1_pod_list([])

        ecc_reboot_node_rule_instance = ecc_reboot_node_rule.EccRebootNodeRule(rule_alert_handler_instance, rule_config)
        response = ecc_reboot_node_rule_instance.check_status()


        self.assertFalse(response)
        self.assertEqual(0, len(ecc_reboot_node_rule_instance.nodes_ready_for_action))
        self.assertTrue("node1" not in rule_alert_handler_instance.rule_cache["ecc_rule"])


    @mock.patch('utils.k8s_util.list_namespaced_pod')
    @mock.patch('requests.get')
    @mock.patch('rules.ecc_reboot_node_rule.EccRebootNodeRule.load_ecc_config')
    @mock.patch('rules.ecc_reboot_node_rule.EccRebootNodeRule.load_etcd_config')
    @mock.patch('utils.email_util.EmailHandler')
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler.load_config')
    def test_check_status_no_action_needed(self,
        mock_load_rule_config,
        mock_email_handler,
        mock_load_etcd_config,
        mock_load_ecc_config,
        mock_request_get,
        mock_pod_list):

        rule_config = test_util.mock_rule_config()
        mock_load_rule_config.return_value = rule_config

        etcd_config = test_util.mock_etcd_config()
        mock_load_etcd_config.return_value = etcd_config

        mock_load_ecc_config.return_value = test_util.mock_ecc_config()
        mock_load_ecc_config.return_value["days_until_node_reboot"] = 5

        time_two_days_ago = datetime.utcnow() - timedelta(days=2)
        time_three_days_ago = datetime.utcnow() - timedelta(days=3)
        time_six_days_ago = datetime.utcnow() - timedelta(days=6)

        #  ecc error detection occured in previous iteration
        rule_alert_handler_instance = rule_alert_handler.RuleAlertHandler()
        rule_alert_handler_instance.rule_cache["ecc_rule"] = {
            "node1": {
                "time_found": time_two_days_ago.strftime(rule_config['date_time_format']),
                "instance": "192.168.0.1"
            },
            # this node already has a reboot attempt, so should not trigger take action
            "node2": {
                "time_found": time_three_days_ago.strftime(rule_config['date_time_format']),
                "instance": "192.168.0.2",
                "reboot_requested": time_two_days_ago.strftime(rule_config['date_time_format'])
            }
        }

        # both nodes have not been rebooted after initial detection
        node_boot_times = {
            "192.168.0.1": str(time_three_days_ago.replace(tzinfo=timezone.utc).timestamp()),
            "192.168.0.2": str(time_six_days_ago.replace(tzinfo=timezone.utc).timestamp())
        }
        mock_request_get.return_value.json.return_value = _mock_prometheus_node_boot_time_response(node_boot_times)

        # at least one job running on the node
        mock_pod_list.return_value = test_util.mock_v1_pod_list([
            {
                "job_name": "87654321-wxyz",
                "user_name": "user1",
                "vc_name": "vc1",
                "node_name": "node1"
            }
        ])

        ecc_reboot_node_rule_instance = ecc_reboot_node_rule.EccRebootNodeRule(rule_alert_handler_instance, rule_config)
        response = ecc_reboot_node_rule_instance.check_status()


        self.assertFalse(response)
        self.assertEqual(0, len(ecc_reboot_node_rule_instance.nodes_ready_for_action))


    @mock.patch('rules.ecc_reboot_node_rule.EccRebootNodeRule.load_ecc_config')
    @mock.patch('rules.ecc_reboot_node_rule.EccRebootNodeRule.load_etcd_config')
    @mock.patch('utils.email_util.EmailHandler')
    @mock.patch('requests.get')
    @mock.patch('requests.put')
    @mock.patch('rules.ecc_reboot_node_rule._create_email_for_pause_resume_job')
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler.load_config')
    def test_take_action(self, 
        mock_load_rule_config,
        mock_create_email_for_pause_resume_job,
        mock_put_requests,
        mock_get_requests,
        mock_email_handler,
        mock_load_etcd_config,
        mock_load_ecc_config):

        rule_config = test_util.mock_rule_config()
        mock_load_rule_config.return_value = rule_config

        etcd_config = test_util.mock_etcd_config()
        mock_load_etcd_config.return_value = etcd_config

        mock_load_ecc_config.return_value = test_util.mock_ecc_config()
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

        mock_put_requests.return_value.json.side_effect = [
            {
                "action": "set",
                "node": {
                    "key": "/mock-worker-one/reboot",
                    "value": "True",
                    "modifiedIndex": 39,
                    "createdIndex": 39
                }
            },
            {
                "action": "set",
                "node": {
                    "key": "/mock-worker-three/reboot",
                    "value": "True",
                    "modifiedIndex": 39,
                    "createdIndex": 39
                }
            }]

        rule_alert_handler_instance = rule_alert_handler.RuleAlertHandler()
        rule_alert_handler_instance.rule_cache["ecc_rule"] = {
            "mock-worker-one": {"instance": "192.168.0.1:9090"},
            "mock-worker-two": {"instance": "192.168.0.2:9090"},
            "mock-worker-three": {"instance": "192.168.0.3:9090"}
        }

        ecc_reboot_node_rule_instance = ecc_reboot_node_rule.EccRebootNodeRule(
            rule_alert_handler_instance, rule_config)
        ecc_reboot_node_rule_instance.nodes_ready_for_action = [
            "mock-worker-one", "mock-worker-three"]
        ecc_reboot_node_rule_instance.jobs_ready_for_migration = {
            "87654321-wxyz":
                {
                    "user_name": "user1",
                    "vc_name": "vc1",
                    "node_names": ["mock-worker-one"],
                    "job_link": "/job-link-1"
                },
            "12345678-abcd": {
                    "user_name": "user2",
                    "vc_name": "vc2",
                    "node_names": ["mock-worker-one"],
                    "job_link": "/job-link-2"
                },
            "99999999-efgh": {
                    "user_name": "user3",
                    "vc_name": "vc3",
                    "node_names": ["mock-worker-three"],
                    "job_link": "/job-link-3"
                }
        }

        ecc_reboot_node_rule_instance.take_action()

        self.assertEqual(3, mock_create_email_for_pause_resume_job.call_count)
        self.assertEqual(3, len(rule_alert_handler_instance.rule_cache["ecc_rule"]))
        # node should have successfully rebooted
        self.assertTrue("mock-worker-one" in rule_alert_handler_instance.rule_cache["ecc_rule"])
        self.assertTrue("reboot_requested" in rule_alert_handler_instance.rule_cache["ecc_rule"]["mock-worker-one"])
        # no action was taken on this node (not in ready for action list)
        self.assertTrue("mock-worker-two" in rule_alert_handler_instance.rule_cache["ecc_rule"])
        self.assertFalse("reboot_requested" in rule_alert_handler_instance.rule_cache["ecc_rule"]["mock-worker-two"])
        # node should have successfully rebooted
        self.assertTrue("mock-worker-three" in rule_alert_handler_instance.rule_cache["ecc_rule"])
        self.assertTrue("reboot_requested" in rule_alert_handler_instance.rule_cache["ecc_rule"]["mock-worker-three"])
    

    @mock.patch('rules.ecc_reboot_node_rule.EccRebootNodeRule.load_etcd_config')
    @mock.patch('rules.ecc_reboot_node_rule.EccRebootNodeRule.load_ecc_config')
    @mock.patch('utils.email_util.EmailHandler')
    @mock.patch('requests.get')
    @mock.patch('requests.put')
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler.load_config')
    def test_take_action_pause_failed(self, 
        mock_load_rule_config,
        mock_put_requests,
        mock_get_requests,
        mock_email_load_config,
        mock_load_ecc_config,
        mock_load_etcd_config):

        rule_config = test_util.mock_rule_config()
        mock_load_rule_config.return_value = rule_config

        etcd_config = test_util.mock_etcd_config()
        mock_load_etcd_config.return_value = etcd_config

        mock_load_ecc_config.return_value = test_util.mock_ecc_config()
        mock_load_ecc_config.return_value["alert_job_owners"] = True

        mock_get_requests.return_value.json.return_value = {"result": "Sorry, something went wrong."}

        rule_alert_handler_instance = rule_alert_handler.RuleAlertHandler()
        rule_alert_handler_instance.rule_cache["ecc_rule"] = {
            "mock-worker-one": {"instance": "192.168.0.1:9090"},
            "mock-worker-two": {"instance": "192.168.0.2:9090"},
            "mock-worker-three": {"instance": "192.168.0.3:9090"},
            "mock-worker-four": {"instance": "192.168.0.4:9090"}
        }

        ecc_reboot_node_rule_instance = ecc_reboot_node_rule.EccRebootNodeRule(rule_alert_handler_instance, rule_config)
        ecc_reboot_node_rule_instance.nodes_ready_for_action = [
            "mock-worker-one", 
            "mock-worker-two",
            "mock-worker-three",
            "mock-worker-four"
        ]
        ecc_reboot_node_rule_instance.jobs_ready_for_migration = {
            "87654321-wxyz":
                {
                    "user_name": "user1",
                    "vc_name": "vc1",
                    "node_names": ["mock-worker-one"],
                    "job_link": "/job-link-1"
                },
                # distributed job
                "12345678-abcd": {
                    "user_name": "user2",
                    "vc_name": "vc1",
                    "node_names": ["mock-worker-two", "mock-worker-three"],
                    "job_link": "/job-link-2"
                }
        }

        mock_put_requests.return_value.json.return_value = {
            "action": "set",
            "node": {
                "key": "/mock-worker-four/reboot",
                "value": "True",
                "modifiedIndex": 39,
                "createdIndex": 39
            }
        }

        ecc_reboot_node_rule_instance.take_action()
        # node should be skipped since job migration failed
        self.assertTrue("mock-worker-one" in rule_alert_handler_instance.rule_cache["ecc_rule"])
        self.assertFalse("reboot_requested" in rule_alert_handler_instance.rule_cache["ecc_rule"]["mock-worker-one"])
        self.assertFalse("mock-worker-one" in ecc_reboot_node_rule_instance.nodes_ready_for_action)
        # node should be skipped since job migration failed (distributed job)
        self.assertTrue("mock-worker-two" in rule_alert_handler_instance.rule_cache["ecc_rule"])
        self.assertFalse("reboot_requested" in rule_alert_handler_instance.rule_cache["ecc_rule"]["mock-worker-two"])
        self.assertFalse("mock-worker-two" in ecc_reboot_node_rule_instance.nodes_ready_for_action)
        # node should be skipped since job migration failed (distributed job)
        self.assertTrue("mock-worker-three" in rule_alert_handler_instance.rule_cache["ecc_rule"])
        self.assertFalse("reboot_requested" in rule_alert_handler_instance.rule_cache["ecc_rule"]["mock-worker-three"])
        self.assertFalse("mock-worker-three" in ecc_reboot_node_rule_instance.nodes_ready_for_action)
        # node should be successfully rebooted (had no jobs to migrate)
        self.assertTrue("mock-worker-four" in rule_alert_handler_instance.rule_cache["ecc_rule"])
        self.assertTrue("reboot_requested" in rule_alert_handler_instance.rule_cache["ecc_rule"]["mock-worker-four"])
        self.assertTrue("mock-worker-four" in ecc_reboot_node_rule_instance.nodes_ready_for_action)

    @mock.patch('rules.ecc_reboot_node_rule.EccRebootNodeRule.load_ecc_config')
    @mock.patch('rules.ecc_reboot_node_rule.EccRebootNodeRule.load_etcd_config')
    @mock.patch('utils.email_util.EmailHandler')
    @mock.patch('requests.get')
    @mock.patch('requests.put')
    @mock.patch('rules.ecc_reboot_node_rule._create_email_for_pause_resume_job')
    @mock.patch('utils.rule_alert_handler.RuleAlertHandler.load_config')
    def test_take_action_reboot_failed(self, 
        mock_load_rule_config,
        mock_create_email_for_pause_resume_job,
        mock_put_requests,
        mock_get_requests,
        mock_email_handler,
        mock_load_etcd_config,
        mock_load_ecc_config):

        rule_config = test_util.mock_rule_config()
        mock_load_rule_config.return_value = rule_config

        etcd_config = test_util.mock_etcd_config()
        mock_load_etcd_config.return_value = etcd_config

        mock_load_ecc_config.return_value = test_util.mock_ecc_config()
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

        mock_put_requests.return_value.json.side_effect = [
            {
                "action": "set",
                "node": {
                    "key": "/mock-worker-one/reboot",
                    "value": "True",
                    "modifiedIndex": 39,
                    "createdIndex": 39
                }
            },
            # reboot failed for one of the nodes
            {
                "error_code": 100,
                "message": "Something went wrong",
                "cause": "Unable to open connection"
            }]

        rule_alert_handler_instance = rule_alert_handler.RuleAlertHandler()
        rule_alert_handler_instance.rule_cache["ecc_rule"] = {
            "mock-worker-one": {"instance": "192.168.0.1:9090"},
            "mock-worker-three": {"instance": "192.168.0.3:9090"}
        }

        ecc_reboot_node_rule_instance = ecc_reboot_node_rule.EccRebootNodeRule(
            rule_alert_handler_instance, rule_config)
        ecc_reboot_node_rule_instance.nodes_ready_for_action = [
            "mock-worker-one", "mock-worker-three"]
        ecc_reboot_node_rule_instance.jobs_ready_for_migration = {
            "87654321-wxyz":
                {
                    "user_name": "user1",
                    "vc_name": "vc1",
                    "node_names": ["mock-worker-one"],
                    "job_link": "/job-link-1"
                },
            "12345678-abcd": {
                    "user_name": "user2",
                    "vc_name": "vc2",
                    "node_names": ["mock-worker-one"],
                    "job_link": "/job-link-2"
                },
            "99999999-efgh": {
                    "user_name": "user3",
                    "vc_name": "vc3",
                    "node_names": ["mock-worker-three"],
                    "job_link": "/job-link-3"
                }
        }

        ecc_reboot_node_rule_instance.take_action()

        self.assertEqual(3, mock_create_email_for_pause_resume_job.call_count)
        self.assertEqual(2, len(rule_alert_handler_instance.rule_cache["ecc_rule"]))
        # reboot successful for this node
        self.assertTrue("mock-worker-one" in rule_alert_handler_instance.rule_cache["ecc_rule"])
        self.assertTrue("reboot_requested" in rule_alert_handler_instance.rule_cache["ecc_rule"]["mock-worker-one"])
        # reboot failed for this node
        self.assertTrue("mock-worker-three" in rule_alert_handler_instance.rule_cache["ecc_rule"])
        self.assertFalse("reboot_requested" in rule_alert_handler_instance.rule_cache["ecc_rule"]["mock-worker-three"])

if __name__ == '__main__':
    unittest.main()
