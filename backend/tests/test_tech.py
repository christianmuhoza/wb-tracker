import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.tech import (
    classify_notice_tech, looks_like_tech_bidder,
    build_tech_notice_condition, TECH_NOTICE_KEYWORDS,
)


class TestClassifyNoticeTech(unittest.TestCase):

    def test_software_keyword_detected(self):
        result = classify_notice_tech({
            "title": "Development of a new software platform",
            "description": "",
            "project_name": "",
            "procurement_method": "",
            "borrower_bid_reference": "",
        })
        self.assertTrue(result["is_tech"])
        self.assertIn("Software / Platforms", result["tech_category"])

    def test_ict_equipment_detected(self):
        result = classify_notice_tech({
            "title": "Supply of computers and laptops",
            "description": "",
            "project_name": "",
            "procurement_method": "",
            "borrower_bid_reference": "",
        })
        self.assertTrue(result["is_tech"])
        self.assertIn("ICT Equipment", result["tech_category"])

    def test_connectivity_detected(self):
        result = classify_notice_tech({
            "title": "Fiber optic network installation",
            "description": "",
            "project_name": "",
            "procurement_method": "",
            "borrower_bid_reference": "",
        })
        self.assertTrue(result["is_tech"])
        self.assertIn("Connectivity / Telecom", result["tech_category"])

    def test_non_tech_notice(self):
        result = classify_notice_tech({
            "title": "Construction of rural roads",
            "description": "Road rehabilitation project",
            "project_name": "",
            "procurement_method": "",
            "borrower_bid_reference": "",
        })
        self.assertFalse(result["is_tech"])
        self.assertIsNone(result["tech_category"])

    def test_empty_notice(self):
        result = classify_notice_tech({})
        self.assertFalse(result["is_tech"])
        self.assertIsNone(result["tech_category"])

    def test_multiple_categories(self):
        result = classify_notice_tech({
            "title": "Cloud-based cybersecurity platform",
            "description": "Software for data protection",
            "project_name": "",
            "procurement_method": "",
            "borrower_bid_reference": "",
        })
        self.assertTrue(result["is_tech"])
        categories = result["tech_category"].split(", ")
        self.assertIn("Software / Platforms", categories)
        self.assertIn("Cybersecurity / Data", categories)

    def test_search_across_multiple_fields(self):
        result = classify_notice_tech({
            "title": "IT Advisory Services",
            "description": "Digital transformation for the ministry",
            "project_name": "",
            "procurement_method": "",
            "borrower_bid_reference": "",
        })
        self.assertTrue(result["is_tech"])
        self.assertIn("Digital Services", result["tech_category"])


class TestLooksLikeTechBidder(unittest.TestCase):

    def test_tech_company_detected(self):
        row = {"name": "Global Technologies Ltd", "contact_org": "", "category": ""}
        self.assertTrue(looks_like_tech_bidder(row))

    def test_non_tech_company(self):
        row = {"name": "Zambia Road Construction Co", "contact_org": "", "category": ""}
        self.assertFalse(looks_like_tech_bidder(row))

    def test_systems_company(self):
        row = {"name": "Integrated Systems Corp", "contact_org": "", "category": ""}
        self.assertTrue(looks_like_tech_bidder(row))


class TestBuildTechNoticeCondition(unittest.TestCase):

    def test_returns_tuple(self):
        condition, params = build_tech_notice_condition()
        self.assertIsInstance(condition, str)
        self.assertIsInstance(params, list)
        self.assertTrue(len(params) > 0)

    def test_contains_keywords_in_params(self):
        _, params = build_tech_notice_condition()
        self.assertIn("%software%", params)
        self.assertIn("%ict%", params)

    def test_with_alias(self):
        condition, _ = build_tech_notice_condition("n")
        self.assertIn("n.title", condition)
        self.assertIn("n.description", condition)


if __name__ == '__main__':
    unittest.main()
