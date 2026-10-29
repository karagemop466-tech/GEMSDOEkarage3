#!/usr/bin/env python3
"""Control: random-placement null for the off-catalogue SGMC proxy.

Places the same budget (37,654 binary dots) uniformly at random inside the
footprint, excluding known-fault pixels, and scores each draw with the same
evaluator used for every candidate. Gives the chance-level DTI that candidate
scores must beat to be informative. Not a candidate; never a submission.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems32.paths import data_dir  # noqa: E402
from karage3.holdout import evaluate_sgmc_with_ci, load_holdout_context  # noqa: E402

N_DOTS = 37654
SEEDS = [1, 2, 3, 4, 5]
OUT = ROOT / "evidence" / "control-random-null-sgmc.json"


def main() -> int:
    ddir = data_dir()
    with rasterio.open(ddir / "sample_submission.tif") as s:
        fp = np.isfinite(s.read(1))
    with rasterio.open(ddir / "labels.tif") as s:
        known = s.read(1) > 0
    pool = np.flatnonzero((fp & ~known).ravel())
    ctx = load_holdout_context(ddir)
    rows = []
    for seed in SEEDS:
        rng = np.random.default_rng(seed)
        pick = rng.choice(pool, size=N_DOTS, replace=False)
        dots = np.zeros(fp.shape, bool)
        dots.ravel()[pick] = True
        sg = evaluate_sgmc_with_ci(dots & fp, ctx, name=f"null-{seed}")
        rows.append({"seed": seed, "sgmc_raw_dti": round(float(sg["sgmc_raw_pooled_dti"]), 6),
                     "ci95": [round(float(x), 6) for x in sg["sgmc_raw_ci95"]]})
        print(rows[-1], flush=True)
    vals = np.array([r["sgmc_raw_dti"] for r in rows])
    card = {"control": "random placement, same budget, same SGMC evaluator", "evaluator_version": sg["evaluator_version"],
            "n_dots": N_DOTS, "draws": rows, "mean": round(float(vals.mean()), 6),
            "min": round(float(vals.min()), 6), "max": round(float(vals.max()), 6),
            "evidence_class": "HOLDOUT-DTI", "not_a_candidate": True}
    OUT.write_text(json.dumps(card, indent=2) + "\n")
    print("wrote", OUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
