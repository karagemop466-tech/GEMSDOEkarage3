#!/usr/bin/env python3
"""Measure how many dots of a candidate lie inside the scored footprint, and their lattice overlap.

Why this exists: check_candidate_uniqueness.py counts every dot. A file can therefore look
"unique" by placing dots where the template is null (no lattice dots there). This script
reports the in-footprint overlap, which is the part a scorer can use.

Usage: check_inside_footprint_overlap.py CANDIDATE.tif OUT.json
Classification: DIAGNOSTIC, NOT A SCORE. ok_to_submit is always false here.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / ".cache/gems_data/sample_submission.tif"
LATTICE = ROOT / ".cache/gems_data/scored/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    cand, out = Path(argv[0]), Path(argv[1])
    with rasterio.open(TEMPLATE) as t:
        foot = np.isfinite(t.read(1)) & (t.read_masks(1) != 0)
    with rasterio.open(LATTICE) as l:
        lat = np.nan_to_num(l.read(1)) > 0
    with rasterio.open(cand) as c:
        a = c.read(1)
        same_grid = (c.shape == foot.shape) and (c.transform == rasterio.open(TEMPLATE).transform)
    dots = np.isfinite(a) & (a > 0)
    near = distance_transform_edt(~lat) <= 3
    inside = dots & foot
    n_in = int(inside.sum())
    rec = dict(
        schema_version=1,
        checked_utc=datetime.now(timezone.utc).isoformat(),
        classification="DIAGNOSTIC, NOT A SCORE",
        candidate=str(cand.relative_to(ROOT)) if cand.is_absolute() else str(cand),
        same_grid_as_template=bool(same_grid),
        total_dots=int(dots.sum()),
        dots_inside_template_footprint=n_in,
        dots_outside_template_footprint=int((dots & ~foot).sum()),
        inside_within3px_of_lattice_share=(float((inside & near).sum()) / n_in) if n_in else None,
        all_dots_within3px_of_lattice_share=float((dots & near).sum() / dots.sum()) if dots.sum() else None,
        literal_70pct_rule_on_inside_dots_triggered=bool(n_in and (inside & near).sum() / n_in > 0.70),
        ok_to_submit=False,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=2, allow_nan=False) + "\n")
    print(json.dumps(rec, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
