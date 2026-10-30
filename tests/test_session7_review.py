"""Regression checks for the 2026-10-30 review receipts and the DTI break-even rule.

These tests read committed receipts (no restored data needed) and re-check the
break-even identity against the shared metric. They make no score claim.
"""
import json
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

from src.gems32 import metric as M

ROOT = Path(__file__).resolve().parents[1]


def test_break_even_rule_matches_shared_metric():
    # Removing a dot whose exclusive TP credit is t changes DTI as: improves iff t < alpha*DTI.
    rng = np.random.default_rng(7)
    H, W = 40, 40
    checked = violations = 0
    for _ in range(60):
        truth = np.zeros((H, W), bool)
        for _ in range(int(rng.integers(3, 10))):
            y, x = rng.integers(0, H), rng.integers(0, W)
            truth[y:min(H, y + int(rng.integers(5, 20))), x] = True
        pred = (rng.random((H, W)) < 0.02).astype(float)
        pred[truth & (rng.random((H, W)) < 0.5)] = 1.0
        if pred.sum() < 3 or not truth.any():
            continue
        base = M.dti_exact(pred, truth)
        if base["dti"] <= 0:
            continue
        for y, x in list(zip(*np.nonzero(pred > 0)))[:10]:
            p2 = pred.copy()
            p2[y, x] = 0.0
            after = M.dti_exact(p2, truth)
            t = base["tp"] - after["tp"]
            improves = after["dti"] > base["dti"]
            checked += 1
            if improves != (t < 0.2 * base["dti"]):
                violations += 1
    assert checked > 100
    assert violations == 0


def test_isolated_dot_removal_drops_denominator_by_alpha():
    truth = np.zeros((20, 20), bool)
    truth[10, 10] = True
    pred = np.zeros((20, 20))
    pred[10, 11] = 1.0
    b = M.dti_exact(pred, truth)
    a = M.dti_exact(np.zeros((20, 20)), truth)
    d0 = b["tp"] + 0.2 * b["fp"] + 0.8 * b["fn"]
    d1 = a["tp"] + 0.2 * a["fp"] + 0.8 * a["fn"]
    assert abs((d0 - d1) - 0.2) < 1e-9


def test_focus9_structure_receipt_invariants():
    r = json.loads((ROOT / "evidence/focus9-structure-20261030.json").read_text())
    assert r["ok_to_submit"] is False and r["verdict"] == "negative"
    assert r["experiments_run"] == 0 and r["weekly_slots_used"] == 0
    files = {f["site"]: f for f in r["files"]}
    assert set(files) == {"GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
                          "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"}
    # No positive pixel of any focus file lies on a catalogue trace (distance 0).
    assert all(f["positive_on_catalogue_d0_masked_by_organizer_rule"] == 0 for f in files.values())
    # GEMSDOE32 has no positive within 2 px of a catalogue trace.
    g32 = files["GEMSDOE32"]
    assert g32["positive_0px_to_1px_from_catalogue_unmasked"] == 0
    assert g32["positive_1px_to_2px_from_catalogue"] == 0
    assert g32["positive_pixels_in_footprint"] == 37654
    # Exact pixel inheritance: all GEMSDOE32 dots are also GEMSDOE36 dots.
    assert "GEMSDOE36" in r["is_subset_of"]["GEMSDOE32"]
    assert r["pairwise_jaccard_positive_pixels"]["GEMSDOE32"]["GEMSDOE36"] > 0.9
    # The exploratory ring-vs-reported association is recorded with its label.
    rv = r["ring_vs_reported"]
    assert rv["label"].startswith("USER-REPORTED")
    rings = [rv["ring_0_to_2px_dots"][s] for s in sorted(files)]
    scores = [rv["user_reported_score"][s] for s in sorted(files)]
    rho = spearmanr(rings, [-s for s in scores]).statistic
    assert rho > 0.9
    assert abs(rho - rv["spearman_ring_vs_reported_score"]) < 1e-3


def test_holdout_reproduction_receipt_labels():
    p = ROOT / "evidence/holdout-reproduction-20261030-geoconduit-zeros.json"
    d = json.loads(p.read_text())
    h = d["hide_and_recover"]
    assert h["evaluator_version"] == "GEMSDOE32-HIDE-RECOVER-v3.0"
    assert h["score_label"] == "HOLDOUT-DTI"
    assert h["n_withheld_positives"] == 22232
    assert abs(h["pooled_dti"] - 0.30473355287974024) < 1e-9
    lo, hi = h["ci95_cluster_bootstrap"]
    assert abs(lo - 0.2881210935821653) < 1e-9 and abs(hi - 0.3188882103680109) < 1e-9
    assert d["promotion_eligible"] is False
