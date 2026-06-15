import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.bidder_extraction import (
    _clean_name, _dedupe, extract_bidders_list,
    extract_awarded_bidders, extract_bidders_from_description,
    parse_notice_bidder_details, _infer_notice_category,
    _merge_categories,
)


class TestCleanName(unittest.TestCase):

    def test_clean_basic_name(self):
        self.assertEqual(_clean_name("  Acme Corp  "), "Acme Corp")

    def test_remove_leading_numbers(self):
        self.assertEqual(_clean_name("1. Acme Corp"), "Acme Corp")

    def test_remove_trailing_punctuation(self):
        self.assertEqual(_clean_name("Acme Corp,"), "Acme Corp")

    def test_empty_input(self):
        self.assertEqual(_clean_name(""), '')

    def test_noise_words(self):
        self.assertEqual(_clean_name("n/a"), '')
        self.assertEqual(_clean_name("N/A"), '')
        self.assertEqual(_clean_name("none"), '')

    def test_short_name(self):
        self.assertEqual(_clean_name("AB"), '')


class TestDedupe(unittest.TestCase):

    def test_dedupe_case_insensitive(self):
        result = _dedupe(["Acme Corp", "acme corp", "Global Ltd"])
        self.assertEqual(result, ["Acme Corp", "Global Ltd"])

    def test_preserves_order(self):
        result = _dedupe(["C", "A", "B", "A", "C"])
        self.assertEqual(result, ["C", "A", "B"])

    def test_empty_list(self):
        self.assertEqual(_dedupe([]), [])


class TestExtractBiddersList(unittest.TestCase):

    def test_format_a_numbered_list(self):
        text = "Bidder 1: Acme Corp\nBidder 2: Global Supplies Ltd"
        result = extract_bidders_list(text)
        self.assertIn("Acme Corp", result)
        self.assertIn("Global Supplies Ltd", result)

    def test_format_b_labeled_fields(self):
        text = "Awarded Firm: Acme Corp\nEvaluated Bidder(s): Global Supplies Ltd"
        result = extract_bidders_list(text)
        self.assertIn("Acme Corp", result)
        self.assertIn("Global Supplies Ltd", result)

    def test_format_c_table_rows(self):
        text = "1 | Acme Corp | USD 1,200,000\n2 | Global Ltd | USD 800,000"
        result = extract_bidders_list(text)
        self.assertIn("Acme Corp", result)

    def test_format_d_freeform_contract_awarded(self):
        text = "The contract was awarded to Acme Corp for the supply of goods."
        result = extract_bidders_list(text)
        self.assertIn("Acme Corp", result)

    def test_empty_text(self):
        self.assertEqual(extract_bidders_list(""), [])

    def test_no_bidders_found(self):
        self.assertEqual(extract_bidders_list("This is a notice about road construction."), [])


class TestExtractAwardedBidders(unittest.TestCase):

    def test_awarded_section(self):
        text = "Awarded Firm: Acme Corp\nEvaluated Bidder(s): Global Supplies Ltd"
        result = extract_awarded_bidders(text)
        self.assertIn("Acme Corp", result)
        self.assertNotIn("Global Supplies Ltd", result)

    def test_freeform_awarded(self):
        text = "The contract was awarded to Acme Corp for the supply."
        result = extract_awarded_bidders(text)
        self.assertIn("Acme Corp", result)

    def test_empty_text(self):
        self.assertEqual(extract_awarded_bidders(""), [])


class TestExtractBiddersFromDescription(unittest.TestCase):

    def test_returns_semicolon_separated(self):
        text = "Bidder 1: Acme Corp\nBidder 2: Global Ltd"
        result = extract_bidders_from_description(text)
        self.assertIn("Acme Corp", result)
        self.assertIn("Global Ltd", result)

    def test_none_on_empty(self):
        self.assertIsNone(extract_bidders_from_description(""))


class TestParseNoticeBidderDetails(unittest.TestCase):

    def test_parse_awarded_section_with_amounts(self):
        text = """Awarded Firm(s): ACME CORP (1234)
Country: Zambia
Bid Price at Opening: USD 1,200,000
Evaluated Bid Price: USD 1,180,000

Awarded Firm(s): GLOBAL LTD (5678)
Country: Kenya
Bid Price at Opening: USD 900,000"""
        result = parse_notice_bidder_details(text)
        self.assertTrue(len(result) >= 2)
        names = [r["name"] for r in result]
        self.assertIn("ACME CORP (1234)", names)
        self.assertIn("GLOBAL LTD (5678)", names)

    def test_empty_text(self):
        self.assertEqual(parse_notice_bidder_details(""), [])


class TestInferNoticeCategory(unittest.TestCase):

    def test_works_category(self):
        result = _infer_notice_category(
            {"borrower_bid_reference": "ZW-CW-123", "title": "", "procurement_method": ""},
            ""
        )
        self.assertEqual(result, "Works")

    def test_goods_category(self):
        result = _infer_notice_category(
            {"borrower_bid_reference": "ZW-GO-456", "title": "", "procurement_method": ""},
            ""
        )
        self.assertEqual(result, "Goods")

    def test_consulting_category(self):
        result = _infer_notice_category(
            {"borrower_bid_reference": "ZW-CS-789", "title": "", "procurement_method": ""},
            ""
        )
        self.assertEqual(result, "Consulting Services")

    def test_unknown_category(self):
        result = _infer_notice_category(
            {"borrower_bid_reference": "", "title": "Some notice", "procurement_method": ""},
            ""
        )
        self.assertIsNone(result)


class TestMergeCategories(unittest.TestCase):

    def test_merge_two_categories(self):
        result = _merge_categories("Works", "Goods")
        self.assertIn("Works", result)
        self.assertIn("Goods", result)

    def test_merge_with_none(self):
        self.assertEqual(_merge_categories("Works", None), "Works")
        self.assertEqual(_merge_categories(None, "Goods"), "Goods")

    def test_merge_duplicates(self):
        result = _merge_categories("Works, Goods", "Goods, Consulting Services")
        categories = result.split(", ")
        self.assertEqual(categories, ["Works", "Goods", "Consulting Services"])


if __name__ == '__main__':
    unittest.main()
