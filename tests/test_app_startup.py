import unittest
from unittest.mock import patch, MagicMock
from app import create_app


class TestAppStartup(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()

    @patch("services.extraction_service.ExtractionService.get_pipeline_info")
    def test_health_endpoint(self, mock_get_pipeline_info):
        mock_get_pipeline_info.return_value = {"name": "hubspot_deals_extraction"}
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get("status"), "healthy")

    @patch("services.extraction_service.ExtractionService.get_pipeline_info")
    def test_api_health_endpoint(self, mock_get_pipeline_info):
        mock_get_pipeline_info.return_value = {"name": "hubspot_deals_extraction"}
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get("status"), "healthy")
