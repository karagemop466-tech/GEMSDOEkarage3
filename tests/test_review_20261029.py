"""Regression checks for the audit-only 2026-10-29 review and fail-closed status."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "evidence/rejected-lattice-hole-candidate"
ARTIFACT_NAME = "karage3-unique-offcat-20261029T180337Z-6a8c2368-zeros.tif"


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
    assert card["inherited_artifact_review"]["status"].startswith("REJECTED — DO NOT SUBMIT")
    assert len(card["note"]) <= 140


def test_review_is_current_starting_point_and_dashboard_links_resolve():
    agents = (ROOT / "AGENTS.md").read_text()
    readme = (ROOT / "README.md").read_text()
    html = (ROOT / "docs/index.html").read_text()
    home = (ROOT / "index.html").read_text()
    assert "docs/review-2026-10-29-session.md" in agents
    assert "docs/data/review-run-20261029.json" in agents
    assert "Latest repository review (2026-10-29)" in readme
    assert "review-2026-10-29-session.md" in html
    assert "docs/focus9/index.html" in home
    assert (ROOT / "docs/focus9/index.html").is_file()
    assert (ROOT / "docs/review-2026-10-29-session.md").is_file()
    assert (ROOT / "docs/data/review-run-20261029.json").is_file()


def test_review_reports_source_conflicts_and_no_projected_score():
    review = (ROOT / "docs/review-2026-10-29-session.md").read_text()
    assert "0.3195" in review and "0.4413" in review and "0.4544" in review
    assert "not estimable" in review.lower()
    assert "not causally proven" in review
    assert "not run" in review.lower()
    assert "DO NOT SUBMIT" in review
    assert "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/" in review
    assert "https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and" in review


def test_inherited_lattice_hole_artifact_is_hash_bound_and_not_offered_as_download():
    metadata_path = ARTIFACT_DIR / "karage3-unique-offcat-20261029T180337Z-6a8c2368-metadata.json"
    meta = json.loads(metadata_path.read_text())
    zeros = ARTIFACT_DIR / ARTIFACT_NAME
    assert meta["artifact_status"] == "REJECTED — DO NOT SUBMIT"
    assert meta["submission_authorized"] is False
    assert "forbids selecting lattice holes" in meta["construction_warning"]
    assert meta["lattice_overlap_bound"]["classification"].startswith("arithmetic lower bound")
    assert hashlib.sha256(zeros.read_bytes()).hexdigest() == meta["zeros_sha256"]
    assert hashlib.sha256((ARTIFACT_DIR / "karage3-unique-offcat-20261029T180337Z-6a8c2368-nan.tif").read_bytes()).hexdigest() == meta["nan_sha256"]
    assert "format observations only" in (ARTIFACT_DIR / "README.md").read_text()
    for page in ("index.html", "executive-summary.html", "docs/how-to-submit.html", "docs/index.html"):
        text = (ROOT / page).read_text()
        assert ARTIFACT_NAME not in text
        assert "READY TO DOWNLOAD" not in text
        assert "OK TO SUBMIT? YES" not in text
    assert "NO FILE IS CURRENTLY OK TO DOWNLOAD AND SUBMIT" in (ROOT / "docs/how-to-submit.html").read_text()
