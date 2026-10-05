import unittest
from unittest.mock import patch, MagicMock
from app import create_app
from config import get_config
from models.models import Job, JobStatus
from services.job_service import JobService
from services.extraction_service import ExtractionService


class TestPauseResumeSecurity(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        self.job_service = JobService()
        self.config = get_config("testing")
        self.extraction_service = ExtractionService(self.config.get_extraction_config())

    def test_job_to_dict_excludes_auth_by_default(self):
        job = Job(
            id="test-sec-001",
            organizationId="test-org",
            type="deal",
            status=JobStatus.PENDING.value,
            config={
                "auth": {"accessToken": "pat-na1-secret-token"},
                "filters": {"includeArchived": False},
                "type": ["deal"]
            }
        )
        job_dict = job.to_dict(include_auth=False)
        self.assertNotIn("auth", job_dict["config"])
        self.assertIn("filters", job_dict["config"])

        job_dict_with_auth = job.to_dict(include_auth=True)
        self.assertIn("auth", job_dict_with_auth["config"])

    @patch("models.database.check_database_health")
    @patch("services.job_service.get_db_session_scope")
    def test_get_job_status_response_excludes_auth(self, mock_db_scope, mock_health):
        mock_health.return_value = True
        mock_job = Job(
            id="test-sec-002",
            organizationId="test-org",
            type="deal",
            status=JobStatus.RUNNING.value,
            config={
                "auth": "encrypted_auth_string",
                "filters": {"includeArchived": False},
                "type": ["deal"]
            }
        )
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_job
        mock_db_scope.return_value.__enter__.return_value = mock_session

        job_retrieved = self.job_service.get_job("test-sec-002", decrypt=False)
        self.assertNotIn("auth", job_retrieved["config"])

    @patch("services.hubspot_api_service.HubSpotAPIService.validate_credentials")
    @patch("services.extraction_service.ExtractionService._create_performance_indexes")
    @patch("dlt.pipeline")
    @patch("services.job_service.JobService.get_job")
    @patch("services.job_service.JobService.get_latest_checkpoint")
    @patch("services.job_service.JobService.complete_job")
    def test_paused_job_remains_paused_after_pipeline_run(
        self, mock_complete, mock_get_cp, mock_get_job, mock_dlt_pipeline, mock_indexes, mock_validate
    ):
        mock_validate.return_value = {"valid": True}
        mock_pipeline = MagicMock()
        mock_dlt_pipeline.return_value = mock_pipeline
        mock_get_cp.return_value = {
            "cursor": "cursor_next_page_123",
            "pageNumber": 1,
            "recordsProcessed": 5,
            "batchSize": 1,
            "phase": "main_data_paused"
        }
        mock_get_job.side_effect = [
            {
                "scanId": "deals-pause-001",
                "organizationId": "test-org",
                "status": JobStatus.RUNNING.value,
                "config": {"auth": {"accessToken": "pat-test"}, "filters": {}}
            },
            {
                "scanId": "deals-pause-001",
                "organizationId": "test-org",
                "status": JobStatus.PAUSED.value,
                "config": {"auth": {"accessToken": "pat-test"}, "filters": {}}
            }
        ]

        import asyncio
        asyncio.run(self.extraction_service._execute_scan("deals-pause-001"))

        mock_pipeline.run.assert_called_once()
        mock_complete.assert_not_called()

    @patch("services.hubspot_api_service.HubSpotAPIService.validate_credentials")
    def test_resume_from_checkpoint_cursor_and_real_page_size(self, mock_validate):
        mock_validate.return_value = {"valid": True}
        with patch.object(self.job_service, "get_latest_checkpoint") as mock_cp:
            mock_cp.return_value = {
                "cursor": "cursor_page_3",
                "pageNumber": 2,
                "recordsProcessed": 20,
                "batchSize": 1
            }
            source_functions = self.extraction_service.create_source_with_checkpoints(
                auth_config={"accessToken": "pat-test"},
                job_config={"scanId": "job-001", "organizationId": "org-001"},
                filters={},
                job_id="job-001"
            )
            self.assertTrue(len(source_functions) > 0)


if __name__ == "__main__":
    unittest.main()
