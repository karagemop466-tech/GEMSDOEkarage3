#!/usr/bin/env python3
"""Measure the nine focus-site files with the SHARED holdout evaluator and write one labelled table.

Calls scripts/evaluate_holdout.py's evaluate_path (no private fork). Every number is labelled HOLDOUT-DTI
with its evaluator version, number of withheld positives and 95% CI. Leaderboard values are copied from
the user's submission-page reports and are labelled USER-REPORTED (not organizer receipts).
Output: docs/data/nine-site-holdout-20261031.json (read by the executive summary page).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import evaluate_holdout as ev  # noqa: E402  (shared evaluator, unmodified)
from gems32.paths import data_dir  # noqa: E402

# (site, file in docs/downloads, USER-REPORTED leaderboard value copied from the user's list)
SITES = [
    ("GEMSDOE24", "GEMSDOE24-gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif", 0.2477),
    ("GEMSDOE25", "GEMSDOE25-gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif", 0.2600),
    ("GEMSDOE27", "GEMSDOE27-gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif", 0.2449),
    ("GEMSDOE28", "GEMSDOE28-gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif", 0.2710),
    ("GEMSDOE30", "GEMSDOE30-gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif", 0.2600),
    ("GEMSDOE31", "GEMSDOE31-gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif", 0.2708),
    ("GEMSDOE32", "GEMSDOE32-gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif", 0.2778),
    ("GEMSDOE33", "GEMSDOE33-GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif", 0.2632),
    ("GEMSDOE36", "GEMSDOE36-gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif", 0.2750),
]


def main() -> int:
    ddir = data_dir()
    rows = []
    for site, fname, reported in SITES:
        path = ROOT / "docs" / "downloads" / fname
        res = ev.evaluate_path(path, ddir=ddir, name=site)
        hr = res["hide_and_recover"]
        sg = res["sgmc_off_catalogue"]
        rows.append({
            "site": site,
            "file": f"docs/downloads/{fname}",
            "sha256": __import__("hashlib").sha256(path.read_bytes()).hexdigest(),
            "emitted_dots": res["emitted_pixels"],
            "user_reported_leaderboard": {"value": reported, "label": "USER-REPORTED (not an organizer receipt)"},
            "holdout_hide_recover": {
                "label": "HOLDOUT-DTI", "evaluator_version": hr["evaluator_version"],
                "pooled_dti": hr["pooled_dti"], "ci95": hr["ci95_cluster_bootstrap"],
                "n_withheld_positives": hr["n_withheld_positives"]},
            "holdout_sgmc_calibrated": {
                "label": "HOLDOUT-DTI", "evaluator_version": sg["evaluator_version"],
                "calibrated_dti": sg["sgmc_prevalence_calibrated_dti"],
                "ci95": sg["sgmc_calibrated_ci95"], "raw_pooled_dti": sg["sgmc_raw_pooled_dti"],
                "n_withheld_positives": sg["n_withheld_positives"]},
        })
        print(site, round(sg["sgmc_prevalence_calibrated_dti"], 5), round(hr["pooled_dti"], 5), flush=True)
    rows.sort(key=lambda r: -r["holdout_sgmc_calibrated"]["calibrated_dti"])
    out = {
        "generated_for": "2026-10-31",
        "evaluator": "scripts/evaluate_holdout.py -> src/gems32/holdout.py (shared, unmodified)",
        "rank_basis": "holdout_sgmc_calibrated.calibrated_dti (HOLDOUT-DTI, off-catalogue SGMC)",
        "caveat": ("Holdout values are a same-protocol proxy. They are NOT the leaderboard score. "
                   "No organizer receipt exists in this repository for any value listed."),
        "rows": rows,
    }
    dest = ROOT / "docs" / "data" / "nine-site-holdout-20261031.json"
    dest.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    print("wrote", dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
