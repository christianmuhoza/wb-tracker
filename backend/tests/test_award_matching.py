import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fetcher import transform
from routers.awards import score_award_match


def notice(**overrides):
    base = {
        "project_id": "P174385",
        "project_name": "Second Ethiopia Resilient Landscapes and Livelihoods Project",
        "borrower_bid_reference": "",
        "borrower": "Sidama Bureau of Agriculture",
        "title": "",
    }
    base.update(overrides)
    return base


def test_exact_procurement_reference_is_auto_match_strength():
    source = notice(title="Supply of improved potato seed", borrower_bid_reference="ET-MOA-123/2026")
    award = notice(title="Potato seed supply contract award", borrower_bid_reference="et moa 123 2026")

    assert score_award_match(source, award) == (100, "exact procurement reference")


def test_shared_project_does_not_match_unrelated_tenders():
    source = notice(title="Procurement of agricultural lime for Bursa Woreda")
    award = notice(title="Procurement of improved potato seed for Bursa Woreda")

    score, reason = score_award_match(source, award)

    assert score == 0
    assert "same project only" in reason


def test_title_match_without_reference_is_review_strength_not_identity():
    source = notice(title="Supply and installation of solar water pumps in Gonder")
    award = notice(title="Supply and installation of solar water pumps in Gonder")

    score, reason = score_award_match(source, award)

    assert score >= 40
    assert "strong title similarity" in reason


def test_project_name_alone_never_matches():
    source = notice(project_id="", title="Independent procurement audit")
    award = notice(project_id="", title="Independent procurement audit")

    assert score_award_match(source, award)[0] == 0


def test_best_candidate_is_the_exact_title_over_a_related_project_notice():
    award = notice(title="Supply and installation of solar water pumps in Gonder")
    related = notice(title="Supply of solar water tanks in Gonder")
    exact = notice(title="Supply and installation of solar water pumps in Gonder")

    assert score_award_match(exact, award)[0] > score_award_match(related, award)[0]


def test_transform_reads_api_and_embedded_procurement_references():
    api_reference = transform({"id": "1", "notice_type": "IFB", "bid_reference_no": "ET-MOA-321"})
    embedded_reference = transform(
        {
            "id": "2",
            "notice_type": "IFB",
            "bid_description": "Tender reference number: ET/MOA/654.",
        }
    )

    assert api_reference["borrower_bid_reference"] == "ET-MOA-321"
    assert embedded_reference["borrower_bid_reference"] == "ET/MOA/654"
