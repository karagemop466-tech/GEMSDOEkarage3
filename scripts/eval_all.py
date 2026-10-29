#!/usr/bin/env python3
"""Evaluate all candidate masks on hide-and-recover holdout."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems32 import holdout  # noqa: E402
from gems32.paths import data_dir  # noqa: E402

CANDIDATES = [
    ("zone3_8", ".cache/mask_zone3_8.npy"),
    ("zone3_6", ".cache/mask_zone3_6.npy"),
    ("zone1_6", ".cache/mask_zone1_6.npy"),
    ("zone0_3", ".cache/mask_dir_0_3_tight.npy"),
    ("zone1_3", ".cache/mask_dir_1_3_tight.npy"),
    ("zone0_1", ".cache/mask_dir_0_1_tight.npy"),
]


def main() -> None:
    ddir = data_dir()
    ctx = holdout.load_holdout_context(ddir)
    results = {}
    for name, p in CANDIDATES:
        path = Path(p)
        if not path.exists():
            print("skip", name, "missing"); continue
        mask = np.load(path).astype(bool)
        res = holdout.evaluate_hide_and_recover(mask, ctx, b_visible_px=0.0, name=name)
        pooled = res["pooled_dti"]; ci = res["ci95_cluster_bootstrap"]
        sg = res.get("sgmc_off_catalogue", {})
        print(f"{name:10s} emitted={int(mask.sum()):6d} pooled={pooled:.6f} "
              f"CI=[{ci[0]:.6f},{ci[1]:.6f}] sgmc_cal={sg.get('sgmc_prevalence_calibrated_dti',-1):.4f}")
        results[name] = {
            "pooled_dti": pooled, "ci95": ci, "n_withheld": res["n_withheld_positives"],
            "emitted": int(mask.sum()), "sgmc_cal": sg.get("sgmc_prevalence_calibrated_dti"),
            "file": str(path),
        }
    Path(".cache/eval_all_results.json").write_text(json.dumps(results, indent=1))
    print("\nSaved .cache/eval_all_results.json")


if __name__ == "__main__":
    main()
