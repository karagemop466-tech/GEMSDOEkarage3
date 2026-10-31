"""Guards for the 2026-10-31 K8-D session: candidate generated, gated, duplicate-stopped.

Nothing here may authorize a submission; the card's own gates are fail-closed.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "docs" / "quarantine" / "k8d-scarponly" / "karage3-k8d-scarponly-n44k-card.json"
SCAN = ROOT / "evidence" / "k8d-registry-uniqueness-scan.json"
PROOF = ROOT / "evidence" / "k8d-lattice-covering-proof.json"
ESTIMATE = ROOT / "evidence" / "k8d-estimate-projection.json"
FOCUS_OVERLAP = ROOT / "evidence" / "k8d-focus9-overlap.json"


def _load(rel):
    return json.loads((ROOT / rel).read_text())


def test_k8d_card_is_negative_and_quarantined():
    c = json.loads(CARD.read_text())
    assert c["verdict"] == "negative"
    assert c["file_published"] is False
    assert c["gates"]["download_ok"] is False
    assert c["weekly_slots_used"] == 0
    assert c["organizer_confirmed_score"] is None
    # The file must NOT sit in the public downloads folder.
    assert not (ROOT / "docs" / "downloads" / "gemsdoe32-karage3-k8d-scarponly-n44k-20261031T010414Z-857c3fc6-zeros.tif").exists()
    assert CARD.exists()


def test_k8d_holdout_numbers_are_labelled_and_ci_bounded():
    c = json.loads(CARD.read_text())
    h = c["holdout"]
    for key in ("hide_and_recover", "sgmc_off_catalogue"):
        assert h[key]["label"] == "HOLDOUT-DTI"
        assert h[key]["n_withheld_positives"] > 0
        lo, hi = (h[key]["ci95"] if key == "hide_and_recover" else h[key]["calibrated_ci95"])
        dti = h[key]["pooled_dti" if key == "hide_and_recover" else "prevalence_calibrated_dti"]
        assert lo <= dti <= hi
    # The SGMC-CAL value beats the focus-9 best on the same evaluator.
    assert h["sgmc_off_catalogue"]["prevalence_calibrated_dti"] > h["best_focus9_same_evaluator"]["prevalence_calibrated_dti"]
    assert h["leakage_canary"]["auc_vs_sgmc_offcatalogue"] <= 0.90


def test_k8d_full_registry_screen_supports_the_duplicate_stop():
    s = json.loads(SCAN.read_text())
    assert s["checked_same_grid"] > 1900
    assert s["fail_count"] > 0
    assert s["pass"] is False
    rows = [json.loads(line) for line in (SCAN.with_suffix(".partial.jsonl")).read_text().splitlines() if line.strip()]
    checked = [r for r in rows if r["status"] == "checked"]
    # No surface-correlation lane collision anywhere.
    assert max(abs(r["rho_final_dots"]) for r in checked) <= 0.90
    # The decisive collision is the registered scarp-lane research raster.
    h3 = [r for r in checked if "h3-lidar-scarp-unique-50k" in r["name"]]
    assert h3 and max(r["overlap3px_final"] for r in h3) > 0.70


def test_k8d_is_unique_against_the_nine_scored_focus_submissions():
    o = json.loads(FOCUS_OVERLAP.read_text())
    assert len(o["rows"]) == 9
    assert o["max"] <= 0.70
    assert o["pass"] is True


def test_lattice_covering_proof_is_loaded_and_decisive():
    p = json.loads(PROOF.read_text())
    assert p["footprint_share_within_3px_sampled"] > 0.99
    assert all(v > 0.99 for v in p["random_44k_share_within_3px"])


def test_projection_is_labelled_and_never_a_score():
    e = json.loads(ESTIMATE.read_text())
    assert e["label"].startswith("PROJECTION")
    c = json.loads(CARD.read_text())
    assert c["score_projection"]["label"].startswith("PROJECTION")
    assert c["estimated_leaderboard_score"] is None


def test_site_pages_carry_the_decision_first_and_no_authorization():
    for page in ("index.html", "executive-summary.html"):
        txt = (ROOT / page).read_text()
        assert "DO NOT SUBMIT" in txt
        assert "HOLDOUT-DTI" in txt
        assert "PROJECTION" in txt or "not an organizer" in txt.lower() or "NOT ESTABLISHED" in txt
    howto = (ROOT / "docs" / "how-to-submit.html").read_text()
    assert "DO NOT SUBMIT YET" in howto
    assert "-zeros.tif" in howto and "-nan.tif" in howto
    assert "Predicted values must be in range [0, 1]" in howto
