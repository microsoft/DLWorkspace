import unittest
from unittest.mock import Mock
from utils import prometheus_util


def _mock_empty_prometheus_metric_data():
    empty_prometheus_error_data = {"status": "success", "data": {"result": []}}
    return empty_prometheus_error_data


def _mock_prometheus_metric_data():
    mock_prometheus_metric_data = {
        "status": "success",
        "data": {
            "result": [{
                "metric": {
                    "__name__": "nvidiasmi_smi_metric",
                    "exporter_name": "job-exporter",
                    "instance": "192.168.0.1:9102",
                    "job": "serivce_exporter",
                    "minor_number": "1",
                    "scraped_from": "job-exporter-abcd",
                    "type": "volatile_double"
                },
                "values": [[1578453042, "2"], [1578453042, "2"]]
            }, {
                "metric": {
                    "__name__": "nvidiasmi_smi_metric",
                    "exporter_name": "job-exporter",
                    "instance": "192.168.0.2:9102",
                    "job": "serivce_exporter",
                    "minor_number": "1",
                    "scraped_from": "job-exporter-jmgn4",
                    "type": "volatile_double"
                },
                "values": [[1578453042, "2"], [1578453042, "2"],
                           [1578453042, "2"]]
            }]
        }
    }
    return mock_prometheus_metric_data


class TestPrometheusUtil(unittest.TestCase):
    def test_extract_ips_from_response(self):
        mock_response = Mock()
        mock_response.json.return_value = _mock_prometheus_metric_data()

        node_ips = prometheus_util.extract_ips_from_response(mock_response)

        self.assertEqual(len(node_ips), 2)
        self.assertTrue('192.168.0.1' in node_ips)
        self.assertTrue('192.168.0.2' in node_ips)

    def test_extract_ips_from_response_empty(self):
        mock_response = Mock()
        mock_response.json.return_value = _mock_empty_prometheus_metric_data()

        node_ips = prometheus_util.extract_ips_from_response(mock_response)

        self.assertTrue(len(node_ips) == 0)
