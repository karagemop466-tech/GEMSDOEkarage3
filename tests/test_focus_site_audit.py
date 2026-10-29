"""Consistency tests for evidence/focus-site-audit-20261029.json.

These read the committed evidence JSON only, so they run without the 4 GB core
data. They pin the exact-set relations and the lattice pigeonhole arithmetic that
the submission desk quotes.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "evidence" / "focus-site-audit-20261029.json"
NINE = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
        "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]


@pytest.fixture(scope="module")
def audit() -> dict:
    return json.loads(AUDIT.read_text())


def test_nine_files_present_and_hash_checked(audit):
    assert sorted(audit["files"]) == sorted(NINE)
    for site in NINE:
        f = audit["files"][site]
        assert f["registry_sha256_match"] is True
        assert len(f["sha256"]) == 64


def test_format_checks_pass_for_all_nine(audit):
    for site in NINE:
        fc = audit["files"][site]["format_checks"]
        assert fc["crs_is_EPSG32611"] and fc["shape_matches_template"] and fc["transform_matches_template"]
        assert fc["single_band"] and fc["float32"] and fc["values_in_0_1_where_finite"]
        assert fc["nan_inside_footprint"] == 0 and fc["nonzero_outside_footprint"] == 0


def test_exact_set_relations_hold(audit):
    ex = audit["exact_set_relations"]
    assert ex["GEMSDOE32_subset_of_GEMSDOE31"] is True
    assert ex["GEMSDOE31_subset_of_GEMSDOE25"] is True
    assert ex["GEMSDOE32_subset_of_GEMSDOE36"] is True
    assert ex["GEMSDOE25_dot_mask_identical_to_GEMSDOE30"] is True


def test_removed_dots_lie_on_visible_faults(audit):
    ex = audit["exact_set_relations"]
    assert ex["GEMSDOE31_minus_GEMSDOE32_dots"] == 2545
    assert ex["GEMSDOE31_minus_GEMSDOE32_max_distance_to_visible_fault_px"] == pytest.approx(2.0)


def test_dot_counts_match_32_is_smallest(audit):
    counts = {s: audit["files"][s]["dot_count_gt0"] for s in NINE}
    assert counts["GEMSDOE32"] == 37654
    assert min(counts, key=counts.get) == "GEMSDOE32"
    assert sorted(counts.values())[1] == counts["GEMSDOE28"] == 37660


def test_lattice_pigeonhole_arithmetic(audit):
    lat = audit["lattice"]
    H = lat["footprint_px_uncovered_within_3px"]
    assert H == 6649
    # overlap >= 1 - H/N must exceed 0.70 once N >= ceil(H / 0.30)
    assert lat["min_N_forcing_overlap_above_70pct"] == math.ceil(H / 0.30) == 22164
    n = lat["min_N_forcing_overlap_above_70pct"]
    assert 1 - H / n > 0.70
    assert 1 - H / (n - 1) <= 0.70 + 1e-12 or n - 1 < H / 0.30  # boundary sanity


def test_lattice_hash_matches_registry_expectation(audit):
    lat = audit["lattice"]
    assert lat["sha256"] == lat["sha256_expected"]
    assert lat["dots"] == 206895


def test_pairwise_overlaps_are_fractions(audit):
    pw = audit["pairwise_literal_overlap_3px_row_is_A_col_is_B"]
    for a, row in pw.items():
        for b, v in row.items():
            assert 0.0 <= v <= 1.0, (a, b, v)


def test_no_exemption_flag_for_uniqueness(audit):
    # the audit must not carry any "waived" or "exempt" switch
    text = AUDIT.read_text().lower()
    assert "exempt" not in text and "waive" not in text


def test_sgmc_proxy_present_and_labelled(audit):
    sg = audit["offcatalogue_sgmc_raw_dti_same_evaluator"]
    for site in NINE:
        assert sg[site]["evidence_class"] == "HOLDOUT-DTI"
        lo, hi = sg[site]["ci95"]
        assert lo <= sg[site]["dti"] <= hi
        assert "calibrated" in sg[site]["note"]  # the calibrated variant is named and not reported
