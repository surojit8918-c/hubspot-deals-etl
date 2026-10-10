import unittest
from unittest.mock import patch, MagicMock
from app import create_app
from services.database_service import DatabaseService
from models.models import JobStatus


class TestTableNameSecurity(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        self.db_service = DatabaseService("hubspot_deals_extraction", "postgres")

    @patch("dlt.pipeline")
    def test_database_service_valid_table(self, mock_dlt_pipeline):
        mock_pipeline = MagicMock()
        mock_sql_client = MagicMock()
        mock_dlt_pipeline.return_value = mock_pipeline
        mock_pipeline.sql_client.return_value.__enter__.return_value = mock_sql_client

        # Mock get_available_tables return value
        mock_tables_result = MagicMock()
        mock_tables_result.fetchall.return_value = [("hubspot_deals",), ("other_table",)]
        
        # Mock total_count, column structure, data query
        mock_count_result = MagicMock()
        mock_count_result.fetchone.return_value = (5,)
        mock_schema_result = MagicMock()
        mock_schema_result.fetchall.return_value = [("id",), ("name",)]
        mock_data_result = MagicMock()
        mock_data_result.fetchall.return_value = [(1, "Deal A"), (2, "Deal B")]

        mock_sql_client.execute_sql.side_effect = [
            mock_tables_result,  # tables_list query
            mock_count_result,   # count query
            mock_schema_result,  # columns query
            mock_data_result     # data query
        ]

        result = self.db_service.get_scan_data("dataset_123", "hubspot_deals")
        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["tableName"], "hubspot_deals")

    @patch("dlt.pipeline")
    def test_database_service_non_existent_table(self, mock_dlt_pipeline):
        mock_pipeline = MagicMock()
        mock_sql_client = MagicMock()
        mock_dlt_pipeline.return_value = mock_pipeline
        mock_pipeline.sql_client.return_value.__enter__.return_value = mock_sql_client

        mock_tables_result = MagicMock()
        mock_tables_result.fetchall.return_value = [("hubspot_deals",)]
        mock_sql_client.execute_sql.return_value = mock_tables_result

        result = self.db_service.get_scan_data("dataset_123", "unknown_table")
        self.assertFalse(result["success"])
        self.assertIn("Table 'unknown_table' does not exist in schema 'dataset_123'", result["message"])

    @patch("dlt.pipeline")
    @patch("services.database_service.build_sql_queries")
    def test_database_service_sql_injection_payload_rejected(self, mock_build_queries, mock_dlt_pipeline):
        mock_pipeline = MagicMock()
        mock_sql_client = MagicMock()
        mock_dlt_pipeline.return_value = mock_pipeline
        mock_pipeline.sql_client.return_value.__enter__.return_value = mock_sql_client

        mock_tables_result = MagicMock()
        mock_tables_result.fetchall.return_value = [("hubspot_deals",)]
        mock_sql_client.execute_sql.return_value = mock_tables_result

        malicious_payload = 'hubspot_deals";DROP TABLE jobs;--'
        result = self.db_service.get_scan_data("dataset_123", malicious_payload)

        self.assertFalse(result["success"])
        self.assertIn(f"Table '{malicious_payload}' does not exist in schema 'dataset_123'", result["message"])
        # Verify build_sql_queries was never called with the malicious table name
        for call_args in mock_build_queries.call_args_list:
            if len(call_args[0]) > 1:
                self.assertNotEqual(call_args[0][1], malicious_payload)

    @patch("services.extraction_service.ExtractionService.get_scan_results")
    def test_api_route_get_scan_results_valid_table(self, mock_get_results):
        mock_get_results.return_value = {
            "success": True,
            "data": {
                "scanId": "scan-123",
                "tableName": "hubspot_deals",
                "results": [{"id": 1, "dealname": "Test Deal"}]
            }
        }
        headers = {"X-Coordinator-Key": "dev-coordinator-secret-key"}
        response = self.client.get("/api/results/scan-123/result?tableName=hubspot_deals", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])

    @patch("services.extraction_service.ExtractionService.get_scan_results")
    def test_api_route_get_scan_results_non_existent_table(self, mock_get_results):
        mock_get_results.return_value = {
            "success": False,
            "message": "Table 'non_existent' does not exist in schema 'dataset_123'"
        }
        headers = {"X-Coordinator-Key": "dev-coordinator-secret-key"}
        response = self.client.get("/api/results/scan-123/result?tableName=non_existent", headers=headers)
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data["success"])
        self.assertIn("does not exist", data["message"])

    @patch("services.extraction_service.ExtractionService.get_scan_results")
    def test_api_route_get_scan_results_sql_injection_payload(self, mock_get_results):
        malicious_payload = 'hubspot_deals";DROP TABLE jobs;--'
        mock_get_results.return_value = {
            "success": False,
            "message": f"Table '{malicious_payload}' does not exist in schema 'dataset_123'"
        }
        headers = {"X-Coordinator-Key": "dev-coordinator-secret-key"}
        response = self.client.get(f"/api/results/scan-123/result?tableName={malicious_payload}", headers=headers)
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data["success"])
        self.assertIn("does not exist", data["message"])


if __name__ == "__main__":
    unittest.main()
