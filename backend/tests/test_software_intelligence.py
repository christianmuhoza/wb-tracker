import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.software_intelligence import _notice_context, _clean_text


class TestSoftwareIntelligenceHelpers(unittest.TestCase):
    def test_context_uses_full_notice_not_only_title(self):
        context = _notice_context({
            "title": "SDID development",
            "description": "Build a pre-enrolment and identity proofing solution.",
            "project_name": "Digital identity project",
            "procurement_method": "RFP",
            "borrower_bid_reference": "ID-001",
        })
        self.assertIn("SDID development", context)
        self.assertIn("identity proofing solution", context)
        self.assertIn("Digital identity project", context)

    def test_clean_text_is_null_safe_and_bounded(self):
        self.assertIsNone(_clean_text(None))
        self.assertIsNone(_clean_text("  "))
        self.assertEqual(len(_clean_text("x" * 600)), 500)


if __name__ == "__main__":
    unittest.main()
