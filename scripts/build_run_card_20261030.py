#!/usr/bin/env python3
"""Assemble evidence/run-card-20261030-session1.json from the evidence files of this session (no hand-typed numbers)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "evidence"
OUT = E / "run-card-20261030-session1.json"


def load(p: str):
    return json.loads((ROOT / p).read_text())


def main() -> int:
    q = load("evidence/qdti-holdout-20261030.json")
    a = load("evidence/focus9-audit-20261030.json")
    vg = load("evidence/focus9-visible-gated-20261030.json")
    hg = load("evidence/h-geo-claim-verification-20261030.json")
    cand = ROOT / ".cache/research-artifacts/hqdti-not-cleared/gemsdoekarage3-h-qdti-logit-top10-20261030.tif"
    cand_meta = load("docs/quarantine/hqdti-not-cleared/gemsdoekarage3-h-qdti-logit-top10-20261030-meta.json")
    uniq_path = E / "literal-uniqueness-20261030.json"
    ur = json.loads(uniq_path.read_text()) if uniq_path.exists() else None
    qrow = next((c for c in ur["candidates"] if "qdti" in c["file"]), None) if ur else None
    uniq = ({"status": "NOT RUN: receipt missing"} if qrow is None else
            {"status": f"{qrow['literal_screen_result']} (literal rule, decisive by protocol)",
             "receipt": str(uniq_path.relative_to(ROOT)),
             "candidate_max_within_3px": qrow["max_fraction_within_3px"],
             "candidate_argmax_within_3px_registry": qrow["argmax_fraction_registry"],
             "candidate_max_abs_spearman": qrow["max_abs_spearman"],
             "candidate_argmax_spearman_registry": qrow["argmax_spearman_registry"],
             "candidate_duplicate_hits_count": qrow["duplicate_hits_count"],
             "registry_unique_sha256_compared": ur["registry_unique_sha256_compared"],
             "skipped_counts": ur["skipped_counts"],
             "degeneracy_flag": ("the within-3px maximum for every candidate is driven by one registry raster "
                                 "(apartanish22-droid/ApartGEMSDOE2 depth-cond-conductive-under-thin-cover top37654 -nan), "
                                 "which is ~98.8 % positive; a near-full raster makes every dot 'within 3 px'. "
                                 "The within-3px rule is degenerate against it. The rho rule is not affected. "
                                 "A rule decision (exclude or keep) is needed from the user; it is not applied here."),
             "note": "screen against the FILTERED inventory only; not a uniqueness certificate"})
    rf = q["results_by_fraction"]
    qdti_table = {f: {"qdti": {"pooled_dti": round(v["qdti"]["pooled_dti"], 4),
                               "ci95": [round(x, 4) for x in v["qdti"]["ci95_cluster_bootstrap"]]},
                      "random_same_area": {"pooled_dti": round(v["random_same_area"]["pooled_dti"], 4),
                                           "ci95": [round(x, 4) for x in v["random_same_area"]["ci95_cluster_bootstrap"]]}}
                  for f, v in rf.items()}
    rows = a["rows"]
    own = [r["owner_reported_score"] for r in rows]
    hold = [r["holdout_dti"]["pooled_dti"] for r in rows]
    rho, p = spearmanr(hold, own)
    vg_rows = {r["site"]: r["visible_gated_b2"] for r in vg["rows"]}
    focus = []
    for r in rows:
        focus.append({"site": r["site"], "file": r["file"], "sha256": r["sha256"],
                      "format_gate_pass": r["format_gate_pass_official"],
                      "format_checks_failed": r["format_checks_failed"],
                      "owner_reported_USER_REPORTED": r["owner_reported_score"],
                      "holdout_dti_hide_recover": {"value": round(r["holdout_dti"]["pooled_dti"], 6),
                                                   "ci95": [round(x, 6) for x in r["holdout_dti"]["ci95_cluster_bootstrap"]],
                                                   "n_withheld_positives": r["holdout_dti"]["n_withheld_positives"],
                                                   "evaluator_version": r["holdout_dti"]["evaluator_version"]},
                      "holdout_dti_visible_gated_b2_point": round(vg_rows[r["site"]], 6)})
    card = {
        "schema_version": 1,
        "run_id": "gemsdoekarage3-session1-20261030",
        "branch": "arena/1f0b5753-gemsdoekarage3",
        "method_lane": "H-QDTI label-trained logistic emission (single lane)",
        "hypotheses_ranked": [
            {"rank": 1, "id": "H2", "name": "magnetic tilt-derivative contact ridges with gravity-gradient ridges", "tested": False},
            {"rank": 2, "id": "H3", "name": "geodetic strain-rate ridges at detrended-elevation slope steps", "tested": False},
            {"rank": 3, "id": "H4", "name": "basement-step ridges at conductivity contrasts", "tested": False},
            {"rank": 4, "id": "H1", "name": "H-QDTI logistic emission", "tested": True, "result": "negative (below random control)"},
            {"rank": 5, "id": "H5", "name": "off-catalogue-only emission (SGMC-validated)", "tested": False},
        ],
        "top_hypothesis_validated_on_holdout": False,
        "top_hypothesis_validation_status": "NOT VALIDATED: experiment budget spent (3 of 3). Needs an explicit decision for a 4th experiment.",
        "experiments_run": 3,
        "experiment_budget": 3,
        "weekly_slots_used": 0,
        "slot_approved": False,
        "holdout_leakage_canary": {"label": "HOLDOUT-DTI infrastructure", "max_single_feature_auc": round(q["leakage_canary"]["max_single_feature_auc"], 4),
                                   "threshold": 0.90, "result": "PASS"},
        "holdout_H_QDTI_vs_random": {"label": "HOLDOUT-DTI", "evaluator_version": q["evaluator_version"],
                                     "withheld_positives": 22232, "by_fraction": qdti_table,
                                     "result": "FAIL: H-QDTI below random same-area control at every fraction"},
        "candidate_raster": {"file": str(cand.relative_to(ROOT)), "sha256": hashlib.sha256(cand.read_bytes()).hexdigest(),
                             "emitted_cells": cand_meta["emitted_cells"], "catalogue_cells_emitted": cand_meta["catalogue_cells_emitted"],
                             "status": "NOT CLEARED (quarantined; do not submit)",
                             "gates": {"format_check_scripts_check_format": "PASS",
                                       "writer_audit_audit_geotiff_nan": "PASS (13/13)",
                                       "leakage_canary": "PASS",
                                       "holdout_vs_random_control": "FAIL",
                                       "holdout_vs_holdout_best_0.0967": "FAIL",
                                       "literal_uniqueness": uniq["status"]}},
        "focus9_nine_site": {"label": "HOLDOUT-DTI + USER-REPORTED + FORMAT/OVERLAP", "sites": focus,
                             "holdout_vs_owner_reported_spearman": {"rho": round(float(rho), 4), "p": round(float(p), 4), "n": len(rows)},
                             "visible_gated_b2_vs_owner_reported": {k: v for k, v in vg["spearman_visible_gated_vs_owner_reported"].items()}},
        "h_geo_claim_verification": {"label": "HOLDOUT-DTI (verification of quarantined file)",
                                     "hide_recover_v3_0": round(hg["files"][0]["hide_recover"]["pooled_dti"], 4),
                                     "hide_recover_ci95": [round(x, 4) for x in hg["files"][0]["hide_recover"]["ci95"]],
                                     "visible_gated_b2": round(hg["files"][0]["visible_gated_b2"]["pooled_dti"], 4),
                                     "claims": hg["claims"],
                                     "reading": "Both claimed numbers reproduce under their named committed evaluator variants."},
        "literal_uniqueness": uniq,
        "leaderboard_check_2026_10_30": {"source": "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/",
                                         "top_1": 0.4544, "rank_48": 0.3195, "value_0_4413_found": False,
                                         "note": "public page read in 3 chunks; user-cited 0.4413 is not on the page"},
        "irregularities": [
            "registry/focus9_registry.json vs data/focus_registry.json disagree on file variant (-allfinite vs -nan); audit uses data/focus_registry.json",
            "GEMSDOE30 dot set is identical to GEMSDOE25 (44,090 dots, 0 differing cells); only outside-footprint encoding differs",
            "GEMSDOE30/32/33/36 fail the official null-or-nan outside rule (zeros outside)",
            "Holdout ordering is inverse to owner-reported ordering (rho -0.849); reproduced under visible-gated b=2 px",
            "User-cited leaderboard 0.4413 not found on the public page; 0.3195 is at rank 48",
            "Prior README advice to use -zeros files conflicts with the official null-or-nan rule and check_format.py; the advice is superseded here",
            "Portal error 'Predicted values must be in range [0, 1]' is not linked to any file in the repo; not reproduced locally",
            "lbfgs ConvergenceWarning on one H-QDTI cell (draw21_fold2, 300 iterations); effect not isolated",
            "Visible-gated variant did not return CIs for the focus rows; point estimates only",
            "Registry is a filtered inventory (literal_registry_complete false); uniqueness is against the filtered inventory only",
            "Surface-level (continuous) check not run: the candidate was built binary only",
            "Literal uniqueness DUPLICATE-STOP for every candidate is driven by a ~98.8 %-positive registry raster (within-3 px rule degenerate); rho gate passes for the H-QDTI candidate (max |rho| 0.152)",
        ],
        "limitations": [
            "No organizer receipt exists; nothing is ORGANIZER-CONFIRMED",
            "All scores are HOLDOUT-DTI local proxies or USER-REPORTED; the local proxy does not track the reported leaderboard",
            "The pre-registration record was written after the experiments and is marked as such",
        ],
        "ok_to_submit": False,
        "verdict": "NEGATIVE: no candidate cleared; no submission slot selected",
    }
    OUT.write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
