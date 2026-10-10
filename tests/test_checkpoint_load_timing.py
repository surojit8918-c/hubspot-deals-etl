import unittest
from unittest.mock import patch, MagicMock
import asyncio

from app import create_app
from config import get_config
from models.models import JobStatus
from services.job_service import JobService
from services.extraction_service import ExtractionService


class TestCheckpointLoadTiming(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.config = get_config("testing")
        self.extraction_service = ExtractionService(self.config.get_extraction_config())
        self.job_service = self.extraction_service.job_service

        # In-memory checkpoint storage for fast, reliable unit testing without DB timeouts
        self.checkpoints = {}

        def mock_save_checkpoint(job_id, data):
            cp = {
                "job_id": job_id,
                "cursor": data.get("cursor"),
                "recordsProcessed": data.get("records_processed", 0),
                "pageNumber": data.get("page_number", 0),
                "phase": data.get("phase")
            }
            self.checkpoints[job_id] = cp
            return cp

        def mock_get_latest_checkpoint(job_id):
            return self.checkpoints.get(job_id)

        self.job_service.save_checkpoint = MagicMock(side_effect=mock_save_checkpoint)
        self.job_service.get_latest_checkpoint = MagicMock(side_effect=mock_get_latest_checkpoint)
        self.job_service.complete_job = MagicMock(return_value=True)
        self.job_service.fail_job = MagicMock(return_value=True)
        self.job_service.update_job_heartbeat = MagicMock(return_value=True)

    @patch("services.hubspot_api_service.HubSpotAPIService.get_deals")
    @patch("services.hubspot_api_service.HubSpotAPIService.validate_credentials")
    @patch("services.extraction_service.ExtractionService._create_performance_indexes")
    @patch("dlt.pipeline")
    @patch("services.job_service.JobService.get_job")
    def test_mid_scan_crash_does_not_advance_checkpoint(
        self, mock_get_job, mock_dlt_pipeline, mock_indexes, mock_validate, mock_get_deals
    ):
        """
        Test 1: Simulate mid-scan crash (exception raised after page fetch but during DLT load).
        Verify that saved checkpoint cursor was NOT prematurely advanced to uncommitted page cursor.
        """
        mock_validate.return_value = {"valid": True}
        mock_get_deals.side_effect = [
            {
                "results": [{"id": "deal-1", "properties": {"dealname": "Deal 1"}}],
                "paging": {"next": {"after": "cursor_page_2"}}
            },
            {
                "results": [],
                "paging": {}
            }
        ]
        job_id = "test-crash-scan-001"
        mock_get_job.return_value = {
            "scanId": job_id,
            "organizationId": "test-org-1",
            "status": JobStatus.RUNNING.value,
            "config": {
                "auth": {"accessToken": "pat-test-token"},
                "filters": {}
            }
        }

        # Mock DLT pipeline to consume resource generator (fetch page) then crash during load
        def run_crash_side_effect(source_functions):
            for fn in source_functions:
                for res in fn():
                    list(res)
            raise RuntimeError("Postgres destination crash during load")

        mock_pipeline = MagicMock()
        mock_dlt_pipeline.return_value = mock_pipeline
        mock_pipeline.run.side_effect = run_crash_side_effect

        # Execute scan which will crash during DLT load
        asyncio.run(self.extraction_service._execute_scan(job_id))

        # Verify no premature checkpoint was saved to DB/storage despite page being fetched
        latest_checkpoint = self.job_service.get_latest_checkpoint(job_id)
        self.assertIsNone(latest_checkpoint)

    @patch("services.hubspot_api_service.HubSpotAPIService.get_deals")
    @patch("services.hubspot_api_service.HubSpotAPIService.validate_credentials")
    @patch("services.extraction_service.ExtractionService._create_performance_indexes")
    @patch("dlt.pipeline")
    @patch("services.job_service.JobService.get_job")
    def test_resume_after_crash_refetches_uncommitted_page(
        self, mock_get_job, mock_dlt_pipeline, mock_indexes, mock_validate, mock_get_deals
    ):
        """
        Test 2: Resume after crash: verify next execution starts from last successfully
        committed cursor (None/initial), successfully re-fetching records without data loss.
        """
        mock_validate.return_value = {"valid": True}
        mock_get_deals.side_effect = [
            {
                "results": [{"id": "deal-1", "properties": {"dealname": "Deal 1"}}],
                "paging": {"next": {"after": "cursor_page_2"}}
            },
            {
                "results": [],
                "paging": {}
            },
            {
                "results": [{"id": "deal-1", "properties": {"dealname": "Deal 1"}}],
                "paging": {"next": {"after": "cursor_page_2"}}
            },
            {
                "results": [],
                "paging": {}
            }
        ]
        job_id = "test-resume-scan-002"
        mock_get_job.return_value = {
            "scanId": job_id,
            "organizationId": "test-org-1",
            "status": JobStatus.RUNNING.value,
            "config": {
                "auth": {"accessToken": "pat-test-token"},
                "filters": {}
            }
        }

        # Step A: First run crashes during DLT load after fetching page 1
        def run_crash_side_effect(source_functions):
            for fn in source_functions:
                for res in fn():
                    list(res)
            raise RuntimeError("Postgres destination error")

        mock_pipeline = MagicMock()
        mock_dlt_pipeline.return_value = mock_pipeline
        mock_pipeline.run.side_effect = run_crash_side_effect

        asyncio.run(self.extraction_service._execute_scan(job_id))
        self.assertIsNone(self.job_service.get_latest_checkpoint(job_id))

        # Step B: Second run (retry/resume) succeeds
        def run_success_side_effect(source_functions):
            for fn in source_functions:
                for res in fn():
                    list(res)

        mock_pipeline.run.side_effect = run_success_side_effect

        with patch.object(self.extraction_service.db_service, "get_scan_data") as mock_get_scan_data:
            mock_get_scan_data.return_value = {"success": True}
            asyncio.run(self.extraction_service._execute_scan(job_id))

        # Verify that pipeline.run was called twice total
        self.assertEqual(mock_pipeline.run.call_count, 2)
        # Verify checkpoint is saved post-load after successful execution
        latest_checkpoint = self.job_service.get_latest_checkpoint(job_id)
        self.assertIsNotNone(latest_checkpoint)
        self.assertEqual(latest_checkpoint["cursor"], "cursor_page_2")

    @patch("services.hubspot_api_service.HubSpotAPIService.get_deals")
    @patch("services.hubspot_api_service.HubSpotAPIService.validate_credentials")
    @patch("services.extraction_service.ExtractionService._create_performance_indexes")
    @patch("dlt.pipeline")
    @patch("services.job_service.JobService.get_job")
    def test_standard_successful_extraction_commits_checkpoint_post_load(
        self, mock_get_job, mock_dlt_pipeline, mock_indexes, mock_validate, mock_get_deals
    ):
        """
        Test 3: Standard successful extraction: verify checkpoint commits properly
        AFTER successful DLT pipeline load execution.
        """
        mock_validate.return_value = {"valid": True}
        job_id = "test-success-scan-003"
        mock_get_job.return_value = {
            "scanId": job_id,
            "organizationId": "test-org-1",
            "status": JobStatus.RUNNING.value,
            "config": {
                "auth": {"accessToken": "pat-test-token"},
                "filters": {}
            }
        }

        mock_get_deals.side_effect = [
            {
                "results": [{"id": "deal-101", "properties": {"dealname": "Big Deal"}}],
                "paging": {"next": {"after": "cursor_page_2"}}
            },
            {
                "results": [],
                "paging": {}
            }
        ]

        def run_success_side_effect(source_functions):
            for fn in source_functions:
                for res in fn():
                    list(res)

        mock_pipeline = MagicMock()
        mock_dlt_pipeline.return_value = mock_pipeline
        mock_pipeline.run.side_effect = run_success_side_effect

        # Run scan
        asyncio.run(self.extraction_service._execute_scan(job_id))

        # Verify pipeline.run was called
        mock_pipeline.run.assert_called_once()

        # Verify post-load checkpoint was committed to DB / memory store
        latest_checkpoint = self.job_service.get_latest_checkpoint(job_id)
        self.assertIsNotNone(latest_checkpoint)
        self.assertEqual(latest_checkpoint["cursor"], "cursor_page_2")
        self.assertEqual(latest_checkpoint["recordsProcessed"], 1)
        self.assertEqual(latest_checkpoint["phase"], "main_data_completed")


if __name__ == "__main__":
    unittest.main()
