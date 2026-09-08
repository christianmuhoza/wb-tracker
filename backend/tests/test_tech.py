import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.tech import (
    build_tech_bidder_condition,
    build_tech_notice_condition,
    classify_notice_tech,
    looks_like_tech_bidder,
)


class TestClassifyNoticeTech(unittest.TestCase):
    def test_software_keyword_detected(self):
        result = classify_notice_tech(
            {
                "title": "Development of a new software platform",
                "description": "",
                "project_name": "",
                "procurement_method": "",
                "borrower_bid_reference": "",
            }
        )
        self.assertTrue(result["is_tech"])
        self.assertIn("Software / Platforms", result["tech_category"])

    def test_ict_equipment_detected(self):
        result = classify_notice_tech(
            {
                "title": "Supply of computers and laptops",
                "description": "",
                "project_name": "",
                "procurement_method": "",
                "borrower_bid_reference": "",
            }
        )
        self.assertTrue(result["is_tech"])
        self.assertIn("ICT Equipment", result["tech_category"])

    def test_connectivity_detected(self):
        result = classify_notice_tech(
            {
                "title": "Fiber optic network installation",
                "description": "",
                "project_name": "",
                "procurement_method": "",
                "borrower_bid_reference": "",
            }
        )
        self.assertTrue(result["is_tech"])
        self.assertIn("Connectivity / Telecom", result["tech_category"])

    def test_non_tech_notice(self):
        result = classify_notice_tech(
            {
                "title": "Construction of rural roads",
                "description": "Road rehabilitation project",
                "project_name": "",
                "procurement_method": "",
                "borrower_bid_reference": "",
            }
        )
        self.assertFalse(result["is_tech"])
        self.assertIsNone(result["tech_category"])

    def test_empty_notice(self):
        result = classify_notice_tech({})
        self.assertFalse(result["is_tech"])
        self.assertIsNone(result["tech_category"])

    def test_multiple_categories(self):
        result = classify_notice_tech(
            {
                "title": "Cloud-based cybersecurity platform",
                "description": "Software for data protection",
                "project_name": "",
                "procurement_method": "",
                "borrower_bid_reference": "",
            }
        )
        self.assertTrue(result["is_tech"])
        categories = result["tech_category"].split(", ")
        self.assertIn("Software / Platforms", categories)
        self.assertIn("Cybersecurity / Data", categories)

    def test_search_across_multiple_fields(self):
        result = classify_notice_tech(
            {
                "title": "IT Advisory Services",
                "description": "Digital transformation for the ministry",
                "project_name": "",
                "procurement_method": "",
                "borrower_bid_reference": "",
            }
        )
        self.assertTrue(result["is_tech"])
        self.assertIn("Digital Services", result["tech_category"])

    def test_ai_emerging_tech_detected(self):
        result = classify_notice_tech(
            {
                "title": "AI-powered predictive analytics platform",
                "description": "Machine learning model for data science",
                "project_name": "",
                "procurement_method": "",
                "borrower_bid_reference": "",
            }
        )
        self.assertTrue(result["is_tech"])
        categories = result["tech_category"].split(", ")
        self.assertIn("AI & Emerging Tech", categories)

    def test_system_integration_detected(self):
        result = classify_notice_tech(
            {
                "title": "ERP system integration for public finance",
                "description": "",
                "project_name": "",
                "procurement_method": "",
                "borrower_bid_reference": "",
            }
        )
        self.assertTrue(result["is_tech"])
        self.assertIn("Software / Platforms", result["tech_category"])

    def test_cybersecurity_expanded_detected(self):
        result = classify_notice_tech(
            {
                "title": "Penetration testing and vulnerability assessment",
                "description": "Network security and endpoint protection",
                "project_name": "",
                "procurement_method": "",
                "borrower_bid_reference": "",
            }
        )
        self.assertTrue(result["is_tech"])
        self.assertIn("Cybersecurity / Data", result["tech_category"])

    def test_medical_equipment_is_not_ict_equipment(self):
        result = classify_notice_tech(
            {
                "title": "Procurement of medical equipments for six Veterinary clinics",
                "description": "Veterinary medicines and equipment wholesale",
                "project_name": "Lowlands Livelihood Resilience Project",
                "procurement_method": "Request for Quotations",
                "borrower_bid_reference": "ET-AFAR, LLRP-503414-GO-RFQ",
            }
        )
        self.assertFalse(result["is_tech"])

    def test_epidemiology_training_program_is_not_tech(self):
        result = classify_notice_tech(
            {
                "title": "Hire an international firm to guide and lead the process of establishing the Advanced Field Epidemiology Training Programs (FELTP).",
                "description": "",
                "project_name": "",
                "procurement_method": "",
                "borrower_bid_reference": "",
            }
        )
        self.assertFalse(result["is_tech"])

    def test_concrete_platform_is_not_software_platform(self):
        result = classify_notice_tech(
            {
                "title": "Construction of Concrete platform for incinerator Bansang RHD",
                "description": "Scope of Contract Construction of Concrete Platform for Incinerator Bansang Central River Region",
                "project_name": "The Gambia COVID-19 Preparedness and Response Project",
                "procurement_method": "Request for Quotations",
                "borrower_bid_reference": "GM-MOH-270567-CW-RFQ",
            }
        )
        self.assertFalse(result["is_tech"])

    def test_project_unit_does_not_match_bare_it(self):
        condition, params = build_tech_notice_condition()
        self.assertEqual(len(params), 1)
        self.assertNotIn("|it|", params[0])
        self.assertIn("~*", condition)


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

    def test_cloud_company(self):
        row = {"name": "Cloud Infrastructure Ltd", "contact_org": "", "category": ""}
        self.assertTrue(looks_like_tech_bidder(row))

    def test_analytics_company(self):
        row = {"name": "Data Analytics Solutions", "contact_org": "", "category": ""}
        self.assertTrue(looks_like_tech_bidder(row))

    def test_managed_services_company(self):
        row = {"name": "Managed Services Provider Inc", "contact_org": "", "category": ""}
        self.assertTrue(looks_like_tech_bidder(row))

    def test_bidder_sql_filter_uses_alias(self):
        condition, params = build_tech_bidder_condition("b")
        self.assertIn("b.name", condition)
        self.assertIn("b.core_products", condition)
        self.assertIn("~*", condition)
        self.assertEqual(len(params), 1)
        self.assertIn("software", params[0])


class TestBuildTechNoticeCondition(unittest.TestCase):
    def test_returns_tuple(self):
        condition, params = build_tech_notice_condition()
        self.assertIsInstance(condition, str)
        self.assertIsInstance(params, list)
        self.assertTrue(len(params) > 0)

    def test_contains_keywords_in_params(self):
        _, params = build_tech_notice_condition()
        self.assertIn("software", params[0])
        self.assertIn("ict", params[0])

    def test_with_alias(self):
        condition, _ = build_tech_notice_condition("n")
        self.assertIn("n.title", condition)
        self.assertIn("n.description", condition)


if __name__ == "__main__":
    unittest.main()
