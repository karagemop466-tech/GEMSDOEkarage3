"""Regression checks for the audit-only 2026-10-29 review and fail-closed status."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_current_repository_review_card_is_negative_and_has_no_candidate():
    card = json.loads((ROOT / "docs/data/review-run-20261029.json").read_text())
    assert card["review_only"] is True
    assert card["verdict"] == "negative"
    assert card["experiments_run"] == card["weekly_slots_used"] == 0
    assert card["ok_to_submit"] is False
    assert card["selector_approval"] is False
    assert card["submission_name"] is None
    assert card["raster_sha256"] is None
    assert card["holdout_dti"]["value"] is None
    assert card["holdout_dti"]["ci_95"] is None
    assert card["correlation_overlap_vs_registry"]["candidate_surface_spearman"] is None
    assert card["correlation_overlap_vs_registry"]["candidate_final_dot_overlap"] is None
    validator = card["validator_output"]
    assert validator["status"].startswith("NOT RUN")
    assert validator["organizer_acceptance"] == "unknown"
    assert all(validator[key] is None for key in (
        "no_nan_inside_footprint", "values_in_0_1", "crs_matches",
        "shape_matches", "transform_matches", "outside_null_or_nan"))
    assert len(card["note"]) <= 140


def test_review_is_current_starting_point_and_dashboard_links_resolve():
    agents = (ROOT / "AGENTS.md").read_text()
    readme = (ROOT / "README.md").read_text()
    html = (ROOT / "docs/index.html").read_text()
    assert "docs/review-2026-10-29-session.md" in agents
    assert "docs/data/review-run-20261029.json" in agents
    assert "Latest repository review (2026-10-29)" in readme
    assert "review-2026-10-29-session.md" in html
    assert (ROOT / "docs/review-2026-10-29-session.md").is_file()
    assert (ROOT / "docs/data/review-run-20261029.json").is_file()


def test_review_reports_source_conflicts_and_no_projected_score():
    review = (ROOT / "docs/review-2026-10-29-session.md").read_text()
    assert "0.3195" in review and "0.4413" in review and "0.4544" in review
    assert "not estimable" in review.lower()
    assert "not causally proven" in review
    assert "NOT RUN" in review
    assert "DO NOT SUBMIT" in review
    assert "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/" in review
    assert "https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and" in review
