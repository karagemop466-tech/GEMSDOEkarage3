#!/usr/bin/env python3
"""Measure the literal uniqueness constraint imposed by the registered calibration lattice.

Registry raster: 13GEMSDOE `20261001_r13-lattice-s5_v2_nan-outside` (listed on the user's GEMSDOE list
with 0.0904). We measure from the restored bytes:
  * lattice dots, and footprint cells NOT within 3 px of any lattice dot (the "gap");
  * the largest dot budget a literal <=70% rule allows if every gap cell is used
    (N <= gap / 0.30, pigeonhole bound);
  * the recall ceiling a gap-only file could reach: the share of off-catalogue SGMC truth cells
    (evaluator's SGMC-CAL truth, >3 px from labels.tif) that lie within 3 px of a gap cell;
  * the share of the same off-catalogue truth within 3 px of ANY lattice dot.

Output: docs/data/lattice-gap-analysis.json. Measured; no score is projected.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
DDIR = ROOT / ".cache" / "gems_data"
LATTICE = DDIR / "scored" / "13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
SGMC = DDIR / "external" / "derived_sgmc_faults_100m_u8.tif"
OUT = ROOT / "docs" / "data" / "lattice-gap-analysis.json"
RADIUS = 3.0


def main() -> int:
    with rasterio.open(DDIR / "labels.tif") as ds:
        lab = ds.read(1)
    foot = lab != -1
    with rasterio.open(LATTICE) as ds:
        a = ds.read(1)
    lat = np.argwhere(np.isfinite(a) & (a > 0))
    fp = np.argwhere(foot)
    dist, _ = cKDTree(lat).query(fp, k=1)
    gap = np.zeros(foot.shape, bool)
    gap[fp[dist > RADIUS, 0], fp[dist > RADIUS, 1]] = True
    n_gap = int(gap.sum())
    with rasterio.open(SGMC) as ds:
        sg = ds.read(1) > 0
    cat = (lab == 1) & foot
    d_cat = distance_transform_edt(~cat)
    sg_off = sg & foot & (d_cat > RADIUS)
    d_gap = distance_transform_edt(~gap)
    lm = np.zeros(foot.shape, bool)
    lm[lat[:, 0], lat[:, 1]] = True
    d_lat = distance_transform_edt(~lm)
    rec = dict(
        schema_version=1,
        registry_raster=str(LATTICE.relative_to(ROOT)),
        lattice_dots=int(lat.shape[0]),
        footprint_cells=int(foot.sum()),
        gap_cells_not_within_3px=n_gap,
        max_budget_for_literal_70pct_if_all_gap_used=int(np.floor(n_gap / 0.30)),
        sgmc_offcatalogue_truth_cells=int(sg_off.sum()),
        recall_ceiling_gap_only_share=round(float((d_gap[sg_off] <= RADIUS).mean()), 6),
        share_offcatalogue_truth_within_3px_of_any_lattice_dot=round(float((d_lat[sg_off] <= RADIUS).mean()), 6),
        interpretation=("A literal-compliant file must put >=30% of its dots in the gap cells, and gap cells "
                        "cover almost none of the off-catalogue truth. Matches IR-K3-02 in knowledge/irregularities.md."),
    )
    OUT.write_text(json.dumps(rec, indent=2, allow_nan=False) + "\n")
    print(json.dumps(rec, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
