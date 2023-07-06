try:
    import common
except:
    pass

from pawnlib.utils.http import CallHttp
import unittest
from unittest.mock import patch, Mock, PropertyMock


class TestCallHttp(unittest.TestCase):
    def setUp(self):
        self.sample_url = "http://example.com"
        self.sample_payload = {"key": "value"}

    def test_url_initialization(self):
        http_call = CallHttp(url=self.sample_url)
        self.assertEqual(http_call.url, self.sample_url)

    @patch('requests.get')
    def test_get_request(self, mock_get):
        mock_resp = Mock()
        type(mock_resp).status_code = PropertyMock(return_value=200)
        mock_resp.json.return_value = {"success": True}
        type(mock_resp.elapsed.total_seconds).return_value = 0.1  # Updated this line
        mock_resp.as_dict.return_value = {"status_code": 200, "result": {"success": True}}  # Added this line
        mock_get.return_value = mock_resp

        http_call = CallHttp(url=self.sample_url, method="get")
        http_call.run()

        self.assertEqual(http_call.response.status_code, 200)
        self.assertEqual(http_call.response.result, {"success": True})

    @patch('requests.post')
    def test_post_request(self, mock_post):
        mock_resp = Mock()
        type(mock_resp).status_code = PropertyMock(return_value=200)
        mock_resp.json.return_value = {"success": True}
        type(mock_resp.elapsed.total_seconds).return_value = 0.1  # Updated this line
        mock_resp.as_dict.return_value = {"status_code": 200, "result": {"success": True}}  # Added this line
        mock_post.return_value = mock_resp

        http_call = CallHttp(url=self.sample_url, method="post", payload=self.sample_payload)
        http_call.run()

        self.assertEqual(http_call.response.status_code, 200)
        self.assertEqual(http_call.response.result, {"success": True})


if __name__ == "__main__":
    unittest.main()
