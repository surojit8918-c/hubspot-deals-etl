import unittest
from unittest.mock import patch, MagicMock
import requests

from services.hubspot_api_service import (
    HubSpotAPIService,
    HubSpotAuthError,
    HubSpotRateLimitError,
    HubSpotAPIError,
    mask_token,
)


class TestHubSpotAPIService(unittest.TestCase):
    def setUp(self):
        self.api_service = HubSpotAPIService(
            base_url="https://api.hubapi.com",
            timeout=5,
            rate_limit=100,
            window_seconds=10,
            max_retries=2,
            backoff_seconds=0.01,
            test_delay_seconds=0,
        )
        self.dummy_token = "pat-na1-12345678-abcd-1234"

    def test_mask_token(self):
        self.assertEqual(mask_token("pat-na1-12345678-abcd-1234"), "pat-****")
        self.assertEqual(mask_token(""), "<empty>")

    @patch.object(requests.Session, "request")
    def test_get_deals_pagination(self, mock_request):
        mock_response_1 = MagicMock()
        mock_response_1.status_code = 200
        mock_response_1.json.return_value = {
            "results": [{"id": "1", "properties": {"dealname": "Deal 1"}}],
            "paging": {"next": {"after": "cursor_page2"}},
        }

        mock_response_2 = MagicMock()
        mock_response_2.status_code = 200
        mock_response_2.json.return_value = {
            "results": [{"id": "2", "properties": {"dealname": "Deal 2"}}],
        }

        mock_request.side_effect = [mock_response_1, mock_response_2]

        pages = list(self.api_service.iter_deals(self.dummy_token, limit=1))
        self.assertEqual(len(pages), 2)
        self.assertEqual(pages[0]["results"][0]["id"], "1")
        self.assertEqual(pages[1]["results"][0]["id"], "2")
        self.assertEqual(mock_request.call_count, 2)

    @patch.object(requests.Session, "request")
    def test_401_unauthorized_error(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Invalid token"}
        mock_request.return_value = mock_response

        with self.assertRaises(HubSpotAuthError) as ctx:
            self.api_service.get_deals(self.dummy_token)

        self.assertEqual(ctx.exception.status_code, 401)
        self.assertFalse(ctx.exception.retryable)

    @patch("time.sleep")
    @patch.object(requests.Session, "request")
    def test_429_rate_limit_retry(self, mock_request, mock_sleep):
        mock_429 = MagicMock()
        mock_429.status_code = 429
        mock_429.headers = {"Retry-After": "2"}

        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_200.json.return_value = {"results": [{"id": "100"}]}

        mock_request.side_effect = [mock_429, mock_200]

        data = self.api_service.get_deals(self.dummy_token)
        self.assertEqual(data["results"][0]["id"], "100")
        mock_sleep.assert_called_with(2.0)

    @patch("time.sleep")
    @patch.object(requests.Session, "request")
    def test_5xx_server_error_retry(self, mock_request, mock_sleep):
        mock_500 = MagicMock()
        mock_500.status_code = 500

        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_200.json.return_value = {"results": [{"id": "200"}]}

        mock_request.side_effect = [mock_500, mock_200]

        data = self.api_service.get_deals(self.dummy_token)
        self.assertEqual(data["results"][0]["id"], "200")
        self.assertEqual(mock_request.call_count, 2)


if __name__ == "__main__":
    unittest.main()
