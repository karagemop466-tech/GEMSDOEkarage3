#!/usr/bin/env python3
"""Measurement (not an experiment): score the nine focus files under the committed visible-gated variant.

Purpose: check whether the holdout-vs-owner-reported inversion in evidence/focus9-audit-20261030.json
depends on the evaluator variant. Uses src/gems32/holdout.py::evaluate_visible_gated_holdout unmodified
(b_gate_px = 2.0, as used for the 0.4239 H-GEO headline). Writes evidence/focus9-visible-gated-20261030.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems32 import holdout  # noqa: E402

DDIR = ROOT / ".cache" / "gems_data"
OUT = ROOT / "evidence" / "focus9-visible-gated-20261030.json"
AUDIT = ROOT / "evidence" / "focus9-audit-20261030.json"


def main() -> int:
    with rasterio.open(DDIR / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    ctx = holdout.load_holdout_context(DDIR)
    assert np.array_equal(ctx.foot, foot)
    audit = json.loads(AUDIT.read_text())
    out_rows = []
    for r in audit["rows"]:
        if not r.get("holdout_eligible"):
            continue
        path = ROOT / ".cache" / "focus9" / r["file"]
        with rasterio.open(path) as ds:
            a = ds.read(1, masked=False)
        m = (np.nan_to_num(a, nan=0.0) > 0) & foot
        vg = holdout.evaluate_visible_gated_holdout(m, ctx, b_gate_px=2.0, n_boot=2000)
        out_rows.append({
            "site": r["site"], "file": r["file"], "sha256": r["sha256"],
            "owner_reported_score": r["owner_reported_score"],
            "holdout_hide_recover": r["holdout_dti"]["pooled_dti"],
            "visible_gated_b2": vg["pooled_dti"],
            "visible_gated_ci95": vg.get("ci95_cluster_bootstrap"),
            "n_withheld_positives": vg.get("n_withheld_positives"),
            "evaluator_version": vg["evaluator_version"],
        })
        print(out_rows[-1]["site"], round(vg["pooled_dti"], 4), flush=True)
    own = [x["owner_reported_score"] for x in out_rows]
    vgv = [x["visible_gated_b2"] for x in out_rows]
    rho, p = spearmanr(vgv, own)
    res = {
        "label": "HOLDOUT-DTI (measurement under the committed visible-gated variant; not an experiment)",
        "rows": out_rows,
        "spearman_visible_gated_vs_owner_reported": {"rho": float(rho), "p": float(p), "n": len(out_rows),
                                                     "note": "owner-reported values are USER-REPORTED, unverified"},
        "limitations": ["visible-gated CI not returned under the key read here for every row; see ci field",
                        "no organizer receipt; not ORGANIZER-CONFIRMED"],
    }
    OUT.write_text(json.dumps(res, indent=2, default=str, allow_nan=False) + "\n")
    print(f"spearman visible-gated vs owner-reported rho={rho:.3f} p={p:.3f} n={len(out_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
