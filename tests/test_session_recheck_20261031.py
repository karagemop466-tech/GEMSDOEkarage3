"""Regression guards for the 2026-10-31 session evidence (no data files needed).

These tests pin the verified facts in evidence/session-recheck-20261031.json and
evidence/run-card-20261031.json, so a later edit cannot silently clear a file or
change a verified count.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RECHECK = ROOT / "evidence" / "session-recheck-20261031.json"
CARD = ROOT / "evidence" / "run-card-20261031.json"

NINE = {"GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
        "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"}
FORMAT_PASS = {"GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE31"}


@pytest.fixture(scope="module")
def recheck() -> dict:
    return json.loads(RECHECK.read_text())


@pytest.fixture(scope="module")
def card() -> dict:
    return json.loads(CARD.read_text())


def test_nine_sites_are_all_present_and_bound_to_pinned_hashes(recheck):
    rows = recheck["rows"]
    assert {r["site"] for r in rows} == NINE
    registry = json.loads((ROOT / "data" / "focus_registry.json").read_text())["sites"]
    pinned = {s["site"]: s["sha256"] for s in registry}
    for r in rows:
        assert r["file_sha256"] == pinned[r["site"]], r["site"]


def test_format_gate_results_match_the_validator(recheck):
    passed = {r["site"] for r in recheck["rows"] if r["format_gate_pass"]}
    assert passed == FORMAT_PASS


def test_no_nine_site_file_is_unique_under_the_literal_rule(recheck):
    for r in recheck["rows"]:
        assert r["literal_protocol_gate"] == "DUPLICATE-STOP", r["site"]
        assert r["ok_to_submit"] is False, r["site"]
        assert r["overlap_vs_lattice_within3px"] > 0.70, r["site"]


def test_zeros_files_are_outside_the_null_or_nan_rule(recheck):
    for r in recheck["rows"]:
        if r["nan_cells"] == 0:
            assert r["outside_null_or_nan"] is False, r["site"]
            assert r["format_gate_pass"] is False, r["site"]


def test_lattice_bound_is_recorded(recheck):
    assert recheck["lattice"]["footprint_cells"] == 5167373
    assert abs(recheck["lattice"]["footprint_coverage_within_3px"] - 0.998713) < 1e-6


def test_session_declares_no_clearance_and_no_slot(recheck, card):
    assert recheck["ok_to_submit_any"] is False
    assert recheck["weekly_slots_used"] == 0
    assert recheck["new_candidates_generated"] == 0
    assert card["ok_to_submit"] is False
    assert card["verdict"] == "negative"
    assert card["organizer_confirmed_scores"] == 0
    assert card["submission_name"] is None


def test_run_card_irregularities_are_listed(card):
    assert card["irregularities"] == [f"IR-S8-0{i}" for i in range(1, 9)]


def test_public_pages_carry_the_session_decision():
    readme = (ROOT / "README.md").read_text()
    assert "2026-10-31 (session 8)" in readme
    assert "OK TO DOWNLOAD AND SUBMIT? NO" in readme
    for page in ("index.html", "site/index.template.html"):
        text = (ROOT / page).read_text()
        assert "Session 8 (2026-10-31)" in text, page
        assert "DO NOT SUBMIT" in text, page
