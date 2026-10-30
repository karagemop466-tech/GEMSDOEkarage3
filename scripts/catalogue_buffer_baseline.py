#!/usr/bin/env python3
"""Diagnostic baselines (no learned model): (a) dense bands within r px of VISIBLE faults; (b) sparse 3-px lattice dots inside a distance ring of visible faults.

Purpose: separate two effects in the shared hide-and-recover holdout:
  (a) how much of the holdout score a trivial catalogue-proximity mask already earns, and
  (b) whether the learned H-QDTI emission (scripts/qdti_holdout.py) adds anything over it.
This is NOT a submission candidate. It uses only the per-cell visible catalogue (fold-local) and
the shared evaluator gems32.holdout.evaluate_hide_and_recover, exactly like the other entries.

Usage: python scripts/catalogue_buffer_baseline.py --data-dir .cache/gems_data --out evidence/catalogue-buffer-baseline-20261030.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems32 import holdout  # noqa: E402  (shared evaluator, unmodified)

RADII_PX = (0, 1, 3, 6, 10)
# Sparse lattice variants (experiment 3): dots on a 3-px lattice inside a distance ring of visible traces.
# These keep the emitted count near the ~37k-dot scale of the dotted-ridge family, unlike the dense bands above.
LATTICE_RINGS = ((1, 2), (1, 3))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=ROOT / ".cache" / "gems_data")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--n-boot", type=int, default=1000)
    a = ap.parse_args()
    t0 = time.time()
    ctx = holdout.load_holdout_context(a.data_dir)
    res = {}
    for r in RADII_PX:
        cells = {}
        area = 0
        for cell in ctx.cells:
            vis = ctx.visible_by_cell[cell.key]
            dom = np.zeros(ctx.foot.shape, bool)
            dom[cell.bbox] = cell.active_sub
            if r == 0:
                m = vis & dom
            else:
                m = (distance_transform_edt(~vis) <= r) & dom
            cells[cell.key] = m
            area += int(m.sum())
        ev = holdout.evaluate_hide_and_recover(cells, ctx, n_boot=a.n_boot, name=f"visible-buffer-{r}px")
        res[f"buffer_{r}px"] = {
            "pooled_dti": ev["pooled_dti"],
            "ci95_cluster_bootstrap": ev["ci95_cluster_bootstrap"],
            "n_withheld_positives": ev["n_withheld_positives"],
            "evaluator_version": ev["evaluator_version"],
            "emitted_cells_all_cells_total": area,
        }
        print(f"visible buffer {r:>2} px: DTI={ev['pooled_dti']:.4f} CI={ev['ci95_cluster_bootstrap']} emitted={area}", flush=True)
    lat = {}
    for lo, hi in LATTICE_RINGS:
        cells = {}
        area = 0
        for cell in ctx.cells:
            vis = ctx.visible_by_cell[cell.key]
            dom = np.zeros(ctx.foot.shape, bool)
            dom[cell.bbox] = cell.active_sub
            d = distance_transform_edt(~vis)
            ring = (d >= lo) & (d <= hi)
            rr, cc = np.indices(ctx.foot.shape)
            lattice = (rr % 3 == 0) & (cc % 3 == 0)
            m = ring & lattice & dom
            cells[cell.key] = m
            area += int(m.sum())
        ev = holdout.evaluate_hide_and_recover(cells, ctx, n_boot=a.n_boot, name=f"lattice-ring-{lo}-{hi}px")
        lat[f"lattice_ring_{lo}_{hi}px"] = {
            "pooled_dti": ev["pooled_dti"],
            "ci95_cluster_bootstrap": ev["ci95_cluster_bootstrap"],
            "n_withheld_positives": ev["n_withheld_positives"],
            "evaluator_version": ev["evaluator_version"],
            "emitted_cells_all_cells_total": area,
        }
        print(f"lattice ring {lo}-{hi} px: DTI={ev['pooled_dti']:.4f} CI={ev['ci95_cluster_bootstrap']} emitted={area}", flush=True)
    out = {
        "experiment": "catalogue-proximity baselines (diagnostic, NOT submissions)",
        "score_label": "HOLDOUT-DTI",
        "results": res,
        "sparse_lattice_results": lat,
        "elapsed_s": round(time.time() - t0, 1),
        "not_organizer_confirmed": True,
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=2, default=float) + "\n")
    print("wrote", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
