#!/usr/bin/env python3
"""Evaluate candidate masks on the spatial hide-and-recover holdout (HOLDOUT-DTI)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems32 import holdout  # noqa: E402
from gems32.paths import data_dir  # noqa: E402


def main() -> None:
    ddir = data_dir()
    ctx = holdout.load_holdout_context(ddir)
    print("context loaded: n_withheld per cell sum =",
          sum(c.n_truth for c in ctx.cells), "n_cells =", len(ctx.cells))

    results = {}
    for name in ["zone3_8", "zone3_6", "zone1_6", "dir_all"]:
        p = Path(f".cache/mask_{name}.npy")
        if not p.exists():
            # try alternate naming
            alt = list(Path(".cache").glob(f"mask_{name}*.npy"))
            p = alt[0] if alt else None
        if p is None:
            print("skip", name, "not found"); continue
        mask = np.load(p).astype(bool)
        print(f"\n=== {name} ({p.name}) emitted={int(mask.sum())} ===")
        res = holdout.evaluate_hide_and_recover(mask, ctx, b_visible_px=0.0, name=name)
        pooled = res["pooled_dti"]
        ci = res["ci95_cluster_bootstrap"]
        sg = res.get("sgmc_off_catalogue", {})
        print(f"  HOLDOUT-DTI pooled={pooled:.6f}  CI95=[{ci[0]:.6f}, {ci[1]:.6f}]  n_withheld={res['n_withheld_positives']}")
        print(f"  SGMC raw={sg.get('sgmc_raw_pooled_dti'):.4f} cal={sg.get('sgmc_prevalence_calibrated_dti'):.4f}")
        print(f"  emitted={res['emitted_pixels']} on_cat={res['on_catalogue_pixels']} hug={res['hug_share']:.3f}")
        results[name] = {
            "pooled_dti": pooled,
            "ci95": ci,
            "n_withheld": res["n_withheld_positives"],
            "emitted": res["emitted_pixels"],
            "sgmc_cal": sg.get("sgmc_prevalence_calibrated_dti"),
        }

    Path(".cache/eval_novel_results.json").write_text(json.dumps(results, indent=1))
    print("\nSaved .cache/eval_novel_results.json")


if __name__ == "__main__":
    main()
