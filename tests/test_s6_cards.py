"""Session-6 candidate cards, duplicate check, random null and desk freshness.

Every candidate must be recorded as NOT ok to submit. The desk must be the
rendering of the current evidence. No proxy number may be presented as a score.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import build_submission_desk as desk

ROOT = Path(__file__).resolve().parents[1]
S6E1 = ROOT / "evidence" / "exp-s6-e1-offconsensus.json"
S6E2 = ROOT / "evidence" / "exp-s6-e2-lidar-lineament.json"
NULL = ROOT / "evidence" / "control-random-null-sgmc.json"
DUP = ROOT / "evidence" / "dup-check-s6.json"
IRR = ROOT / "registry" / "irregularities.json"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture(scope="module", params=[S6E1, S6E2], ids=["S6-E1", "S6-E2"])
def card(request) -> dict:
    return json.loads(request.param.read_text())


def test_candidate_not_ok_to_submit(card):
    assert card["ok_to_submit"] is False


def test_raster_exists_and_hash_matches(card):
    f = ROOT / card["raster"]["file"]
    assert f.exists(), f
    assert _sha(f) == card["raster"]["sha256"]
    assert f.stat().st_size == card["raster"]["bytes"]


def test_validator_and_budget(card):
    assert card["validator"]["validator_pass"] is True
    assert card["validator"]["dots"] == card["n_dots"] == 37654
    assert card["validator"]["nan_inside_footprint"] == 0


def test_zero_overlap_with_nine_focus_files(card):
    assert card["uniqueness_vs_focus_nine_literal_3px_max"] == 0.0


def test_lattice_overlap_above_rule(card):
    assert card["uniqueness_vs_r13_lattice_literal_3px"] > 0.70
    assert card["lattice_rule_pass_70pct"] is False


def test_card_records_duplicate_stop(card):
    assert "DUPLICATE_STOP" in card["verdict"]


def test_holdout_is_labelled_and_ci_ordered(card):
    sg = card["holdout_sgmc_offcatalogue_raw"]
    assert sg["evidence_class"] == "HOLDOUT-DTI"
    lo, hi = sg["ci95"]
    assert lo <= sg["dti"] <= hi


def test_leakage_canary_passes(card):
    assert card["feature_auc_canary"]["max_oriented_auc"] <= 0.90
    assert card["feature_auc_canary"]["pass"] is True


def test_s6e2_novelty_is_disclosed():
    card = json.loads(S6E2.read_text())
    assert "NOT NOVEL" in card["novelty"]


def test_random_null_is_below_focus_band():
    nul = json.loads(NULL.read_text())
    assert nul["not_a_candidate"] is True
    assert len(nul["draws"]) == 5
    assert nul["max"] < 0.0943  # focus band lower edge (audit JSON)


def test_s6e1_below_null():
    e1 = json.loads(S6E1.read_text())
    nul = json.loads(NULL.read_text())
    assert e1["holdout_sgmc_offcatalogue_raw"]["dti"] < nul["min"]


def test_duplicate_check_covers_every_restored_scored_raster():
    dup = json.loads(DUP.read_text())
    for name, v in dup["candidates"].items():
        assert v["verdict"] == "DUPLICATE_STOP", name
        assert len(v["references"]) == dup["n_reference_rasters"] == 14


def test_desk_is_fresh_render_of_evidence():
    text = desk.render()
    assert (ROOT / "submission-desk.html").read_text() == text


def test_desk_verdict_and_downloads_are_honest():
    text = (ROOT / "submission-desk.html").read_text()
    assert "NOT CLEARED" in text
    assert "no file on this page is cleared for upload" in text.lower()
    assert "research only — do NOT upload" in text
    for c in (S6E1, S6E2):
        assert json.loads(c.read_text())["raster"]["file"] in text


def test_no_user_reported_number_labelled_as_organizer_score():
    text = (ROOT / "submission-desk.html").read_text()
    assert "USER-REPORTED" in text
    assert "ORGANIZER-CONFIRMED" not in text.replace("no organizer receipt", "").replace("ORGANIZER-CONFIRMED receipt", "")


def test_irregularity_register_has_ir_s6_entries():
    ids = {x["id"] for x in json.loads(IRR.read_text())["irregularities"]}
    for n in range(1, 13):
        assert f"IR-S6-{n:02d}" in ids, n


def _committed(name: str) -> str:
    """Committed bytes of a root page. Other suites regenerate the working-tree copy."""
    import subprocess
    try:
        return subprocess.run(["git", "show", f"HEAD:{name}"], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return (ROOT / name).read_text()


def test_index_links_to_desk_at_top():
    text = _committed("index.html")
    assert 'href="submission-desk.html"' in text
    assert text.index("submission-desk.html") < text.index('<main id="main"')
