#!/usr/bin/env python3
"""Verification (not an experiment): re-score the quarantined H-GEO-CONDUIT historical files.

Claims under test (from README / docs/review-2026-10-29.md):
  * run card HOLDOUT-DTI 0.4239 [0.4053, 0.4427] under evaluator GEMSDOE32-HOLDOUT-v3-visible-gated
  * committed CLI hide-and-recover evaluator gives 0.3047 [0.2881, 0.3189]

Both files are read from docs/quarantine/geoconduit-hybrid/ (NOT submission files; never copied to downloads).
Scoring uses src/gems32/holdout.py unmodified. Output: evidence/h-geo-claim-verification-20261030.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems32 import holdout  # noqa: E402

DDIR = ROOT / ".cache" / "gems_data"
QDIR = ROOT / "docs" / "quarantine" / "geoconduit-hybrid"
OUT = ROOT / "evidence" / "h-geo-claim-verification-20261030.json"
FILES = [
    "gemsdoe32-karage3-h-geoconduit-hybrid-20261029T181452Z-0a6974d8-nan.tif",
    "gemsdoe32-karage3-h-geoconduit-hybrid-20261029T181452Z-0a6974d8-zeros.tif",
]


def dots_full(path: Path, foot: np.ndarray) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1, masked=False)
    return (np.nan_to_num(a, nan=0.0) > 0) & foot


def main() -> int:
    with rasterio.open(DDIR / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    ctx = holdout.load_holdout_context(DDIR)
    assert np.array_equal(ctx.foot, foot)
    res = {"claims": {"visible_gated_run_card": {"pooled_dti": 0.4239, "ci95": [0.4053, 0.4427]},
                      "hide_recover_cli": {"pooled_dti": 0.3047, "ci95": [0.2881, 0.3189]}},
           "label": "HOLDOUT-DTI (historical verification; file quarantined, not a submission)",
           "files": []}
    for name in FILES:
        p = QDIR / name
        m = dots_full(p, foot)
        row = {"file": name, "sha256_file": None, "emitted_cells": int(m.sum())}
        import hashlib
        row["sha256_file"] = hashlib.sha256(p.read_bytes()).hexdigest()
        try:
            hr = holdout.evaluate_hide_and_recover(m, ctx, name="H-GEO-verify")
            row["hide_recover"] = {"evaluator_version": hr["evaluator_version"], "pooled_dti": hr["pooled_dti"],
                                   "ci95": hr["ci95_cluster_bootstrap"], "n_withheld_positives": hr["n_withheld_positives"]}
        except Exception as e:  # record, do not hide
            row["hide_recover"] = {"error": repr(e)}
        try:
            vg = holdout.evaluate_visible_gated_holdout(m, ctx, b_gate_px=2.0, n_boot=2000)
            row["visible_gated_b2"] = {k: vg.get(k) for k in ("evaluator_version", "pooled_dti", "ci95_cluster_bootstrap", "n_withheld_positives")}
        except Exception as e:
            row["visible_gated_b2"] = {"error": repr(e)}
        print(json.dumps(row, default=str), flush=True)
        res["files"].append(row)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2, default=str, allow_nan=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
