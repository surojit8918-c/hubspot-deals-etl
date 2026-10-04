import unittest
from decimal import Decimal
from datetime import datetime, timezone
import logging

from services.data_source import transform_deal, parse_iso_datetime

class TestTransformDeal(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger("test_transform")

    def test_parse_iso_datetime(self):
        dt = parse_iso_datetime("2026-10-04T09:30:00.000Z")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.tzinfo, timezone.utc)

        self.assertIsNone(parse_iso_datetime(""))
        self.assertIsNone(parse_iso_datetime(None))

    def test_transform_deal_numeric_conversions(self):
        raw = {
            "id": "12345",
            "createdAt": "2026-10-04T09:30:00Z",
            "updatedAt": "2026-10-04T10:00:00Z",
            "archived": False,
            "properties": {
                "amount": "25000.50",
                "dealname": "   Globex Project  \t",
                "dealstage": "presentationscheduled",
                "hs_is_closed": "true",
                "hs_is_closed_won": "false",
                "closedate": "2026-11-15T00:00:00Z"
            }
        }
        props = ["amount", "dealname", "dealstage", "hs_is_closed", "hs_is_closed_won", "closedate"]
        res = transform_deal(raw, props, self.logger)

        self.assertEqual(res["id"], "12345")
        self.assertEqual(res["amount"], Decimal("25000.50"))
        self.assertEqual(res["dealname"], "Globex Project")
        self.assertTrue(res["hs_is_closed"])
        self.assertFalse(res["hs_is_closed_won"])
        self.assertIsInstance(res["closedate"], datetime)

    def test_transform_deal_bad_numeric_fallback(self):
        raw = {
            "id": "67890",
            "properties": {
                "amount": "invalid_number_string"
            }
        }
        res = transform_deal(raw, ["amount"], self.logger)
        self.assertIsNone(res["amount"])


if __name__ == "__main__":
    unittest.main()
