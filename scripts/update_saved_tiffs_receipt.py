#!/usr/bin/env python3
"""Keep evidence/saved-tiffs-literal-20261030.json covering every TIFF under docs/.

For each docs/**/*.tif missing from the receipt, measure the share of its dots
within 3 px of the pinned lattice witness (the decisive duplicate witness used by
this receipt since 2026-10-30) and append the row with duplicate_stop set by the
70% literal rule. Existing rows are preserved byte-for-value; guard fields stay
negative. This is a coverage refresh, not a clearance of anything.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems32.paths import data_dir  # noqa: E402

RECEIPT = ROOT / "evidence" / "saved-tiffs-literal-20261030.json"
LATTICE_CANDIDATES = (
    "scored/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif",
    "13gems_20261001_r13-lattice-s5_v2_nan-outside.tif",
)
RADIUS = 3.0
LIMIT = 0.70


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    d = data_dir()
    lattice_path = next((d / c for c in LATTICE_CANDIDATES if (d / c).exists()), None)
    if lattice_path is None:
        raise SystemExit("lattice witness not found; restore data first")
    with rasterio.open(lattice_path) as ds:
        lat = ds.read(1)
    lat_pts = np.argwhere(np.isfinite(lat) & (lat > 0))
    tree = cKDTree(lat_pts)

    receipt = json.loads(RECEIPT.read_text())
    known = {r["file"] for r in receipt["rasters"]}
    added = []
    for p in sorted((ROOT / "docs").rglob("*.tif")):
        rel = str(p.relative_to(ROOT))
        if rel in known:
            continue
        with rasterio.open(p) as ds:
            a = ds.read(1)
        with rasterio.open(d / "sample_submission.tif") as t:
            foot = np.isfinite(t.read(1)) & (t.read_masks(1) > 0)
        dots = np.argwhere(np.isfinite(a) & (a > 0) & foot)
        if dots.shape[0] == 0:
            frac = 0.0
        else:
            dist, _ = tree.query(dots, k=1)
            frac = float(np.mean(dist <= RADIUS))
        row = {
            "file": rel,
            "sha256": sha256_file(p),
            "within_3px_fraction_vs_lattice_witness": frac,
            "within_3px_fraction": frac,
            "duplicate_stop": bool(frac > LIMIT),
            "measured_utc": datetime.now(timezone.utc).isoformat(),
            "note": "lattice witness share; receipt guard fields unchanged; not a clearance",
        }
        receipt["rasters"].append(row)
        added.append((rel, round(frac, 6), row["duplicate_stop"]))
    receipt["generated_utc"] = datetime.now(timezone.utc).isoformat()
    receipt["guard_note"] = "ok_to_submit stays False; this refresh only extends raster coverage"
    if not args.dry_run:
        RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"added": added, "total_rows": len(receipt["rasters"])}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
