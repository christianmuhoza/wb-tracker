import unittest
from unittest.mock import patch
from fastapi import HTTPException
from api import enrich_bidder_gemini
from services.gemini_service import classify_and_enrich_with_gemini


class TestGeminiService(unittest.TestCase):
    @patch("services.gemini_service.GEMINI_API_KEY", "")
    def test_missing_key_service(self):
        with self.assertRaises(ValueError) as ctx:
            classify_and_enrich_with_gemini("Test Company", "Test Country")
        self.assertIn("GEMINI_API_KEY environment variable is not configured", str(ctx.exception))

    @patch("services.gemini_service.GEMINI_API_KEY", "")
    def test_missing_key_endpoint(self):
        with self.assertRaises(HTTPException) as ctx:
            enrich_bidder_gemini(51)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("GEMINI_API_KEY environment variable is not configured", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
