#!/usr/bin/env python3
"""Budget-matched random control: uniform random dots inside the footprint, labels excluded.

Used as the null for a candidate with the same dot count. Fixed seed, recorded in the output.
Scored with the shared evaluator (scripts/evaluate_holdout.py), so numbers are HOLDOUT-DTI.
Run: python scripts/random_budget_control.py --n 12177 --seed 1 --out evidence/controls/x.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from evaluate_holdout import evaluate_path  # noqa: E402
from gems32.paths import data_dir  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    ddir = data_dir()
    with rasterio.open(ddir / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    with rasterio.open(ddir / "labels.tif") as ds:
        labels = (ds.read(1) > 0) & foot
    pool = np.flatnonzero((foot & ~labels).ravel())
    rng = np.random.default_rng(a.seed)
    pick = rng.choice(pool, size=a.n, replace=False)
    mask = np.zeros(foot.shape, dtype=np.float32)
    mask.ravel()[pick] = 1.0
    tmp = ROOT / ".cache" / "controls" / f"random-n{a.n}-s{a.seed}.npy"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    np.save(tmp, mask)
    res = evaluate_path(tmp, ddir=ddir, name=f"random-n{a.n}-s{a.seed}")
    res["control"] = {"kind": "uniform random inside footprint minus labels", "n": a.n, "seed": a.seed}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, indent=2) + "\n")
    hr = res["hide_and_recover"]
    sg = res["sgmc_off_catalogue"]
    print(f"n={a.n} seed={a.seed} HR={hr['pooled_dti']:.4f} CI={hr['ci95_cluster_bootstrap']} "
          f"SGMCcal={sg['sgmc_prevalence_calibrated_dti']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
