import unittest
import hmac
import hashlib
import json
from unittest.mock import patch, MagicMock
from app import create_app


class TestCoordinatorAuth(unittest.TestCase):
    def setUp(self):
        self.coordinator_key = "dev-coordinator-secret-key"
        self.app = create_app("testing")
        self.app.config["COORDINATOR_KEY"] = self.coordinator_key
        self.client = self.app.test_client()

    def test_request_without_header_returns_401(self):
        # Protected route call without coordinator auth headers
        response = self.client.get("/api/scan/list")
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Unauthorized", data["message"])

    def test_request_with_invalid_key_header_returns_401(self):
        headers = {"X-Coordinator-Key": "wrong-secret-key"}
        response = self.client.get("/api/scan/list", headers=headers)
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Unauthorized", data["message"])

    def test_request_with_invalid_hmac_signature_returns_401(self):
        headers = {"X-Coordinator-Signature": "sha256=0000000000000000000000000000000000000000000000000000000000000000"}
        response = self.client.get("/api/scan/list", headers=headers)
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Unauthorized", data["message"])

    @patch("services.extraction_service.ExtractionService.list_scans")
    def test_request_with_valid_coordinator_key_succeeds(self, mock_list_scans):
        mock_list_scans.return_value = []
        headers = {"X-Coordinator-Key": self.coordinator_key}
        response = self.client.get("/api/scan/list", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])

    @patch("services.extraction_service.ExtractionService.list_scans")
    def test_request_with_valid_hmac_signature_succeeds(self, mock_list_scans):
        mock_list_scans.return_value = []
        # GET with empty body
        body = b""
        expected_sig = hmac.new(
            self.coordinator_key.encode("utf-8"),
            body,
            hashlib.sha256
        ).hexdigest()

        headers = {"X-Coordinator-Signature": f"sha256={expected_sig}"}
        response = self.client.get("/api/scan/list", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])

    @patch("services.extraction_service.ExtractionService.list_scans")
    def test_request_with_valid_hmac_signature_post_payload_succeeds(self, mock_list_scans):
        payload = json.dumps({"organizationId": "org-test-1"}).encode("utf-8")
        expected_sig = hmac.new(
            self.coordinator_key.encode("utf-8"),
            payload,
            hashlib.sha256
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-Coordinator-Signature": expected_sig  # without sha256= prefix
        }
        # Call protected endpoint
        response = self.client.post("/api/scan/list", data=payload, headers=headers)
        # 405 Method Not Allowed is expected for POST /api/scan/list because list is GET-only, but auth passed (not 401)!
        self.assertNotEqual(response.status_code, 401)

    @patch("services.extraction_service.ExtractionService.get_pipeline_info")
    def test_health_endpoints_remain_publicly_accessible(self, mock_pipeline):
        mock_pipeline.return_value = {"name": "test_pipeline"}
        
        # /health without headers
        r1 = self.client.get("/health")
        self.assertEqual(r1.status_code, 200)

        # /api/health without headers
        r2 = self.client.get("/api/health")
        self.assertEqual(r2.status_code, 200)

        # Root / index without headers
        r3 = self.client.get("/")
        self.assertEqual(r3.status_code, 200)


if __name__ == "__main__":
    unittest.main()
