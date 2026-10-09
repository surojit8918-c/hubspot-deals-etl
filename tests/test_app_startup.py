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

    @patch("services.job_service.get_db_session_scope")
    def test_startup_crash_detection_transitions_orphaned_jobs(self, mock_db_scope):
        from datetime import datetime, timezone, timedelta
        from models.models import JobStatus
        old_heartbeat = datetime.now(timezone.utc) - timedelta(minutes=30)

        mock_job = MagicMock()
        mock_job.id = "orphaned-scan-99"
        mock_job.status = JobStatus.RUNNING.value
        mock_job.lastHeartbeat = old_heartbeat
        mock_job.to_dict.return_value = {"id": "orphaned-scan-99", "status": "crashed"}

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [mock_job]
        mock_db_scope.return_value.__enter__.return_value = mock_session

        app = create_app("testing")
        self.assertEqual(mock_job.status, JobStatus.CRASHED.value)
