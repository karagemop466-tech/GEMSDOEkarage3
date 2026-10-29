#!/usr/bin/env python3
"""Build a lattice-compliant binary dot submission (candidate generator).

Policy (lane: "lattice-gap dots, scarp-ranked"):
  1. Footprint F        = cells where the organizer template sample_submission.tif is finite.
  2. Catalogue C        = existing_faults.tif == 1 (identical to labels.tif in this checkout).
  3. Lattice R          = r13 calibration-lattice dots inside F (registry raster, 206,895 dots).
  4. Uncovered U        = F cells > 3 px from every R dot. A dot here is never within 3 px of
                          the lattice, so ALL of U is placed (6,649 cells).
  5. Covered candidates = F cells <= 3 px from R and > 3 px from C (off-catalogue).
  6. k covered dots are added, ranked by the prior, with k chosen so that
     covered / (|U| + k) <= OVERLAP_CAP (default 0.65, margin under the literal 0.70 stop).
  7. Output: float32 GeoTIFF, template CRS/transform/shape, NaN outside F (template
     convention), 1.0 at dots, 0.0 elsewhere inside F. Binary by design (the shared writer
     rejects non-binary inputs).

Priors (ranking of covered candidates; larger score = placed first):
  * lidar_step_max (DEFAULT, pre-declared): external/lidar_scarp_features_u8.tif band
    'step_max' where 'valid' > 0. Mechanism: a vertical step offset is the scarp signature of
    a normal fault. Independent of the catalogue and of the SGMC evaluator truth.
  * sgmc_distance (RETIRED, leakage): nearest USGS SGMC fault trace. The SGMC evaluator scores
    against that same trace, so it is circular. Kept only so the retired candidate reproduces.

This script does NOT authorize a submission. Gates run separately.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

OVERLAP_CAP = 0.65
LATTICE_RADIUS_PX = 3.0
CATALOGUE_RADIUS_PX = 3.0  # 300 m at the 100 m grid
PRIORS = ("lidar_step_max", "sgmc_distance")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def prior_scores(prior: str, data_dir: Path, sgmc: Path, F: np.ndarray, d_sgmc_unused=None) -> np.ndarray:
    """Return a float array; larger = placed earlier."""
    if prior == "lidar_step_max":
        with rasterio.open(data_dir / "external" / "lidar_scarp_features_u8.tif") as d:
            names = list(d.descriptions)
            step = d.read(names.index("step_max") + 1).astype(np.float64)
            valid = d.read(names.index("valid") + 1).astype(np.float64)
        score = np.where(valid > 0, step, -1.0)
        return score
    if prior == "sgmc_distance":
        with rasterio.open(sgmc) as d:
            S = d.read(1) == 1
        return -distance_transform_edt(~S)  # closer to SGMC trace = larger
    raise ValueError(f"unknown prior {prior}")


def build(data_dir: Path, lattice: Path, sgmc: Path, out_tif: Path, cap: float, prior: str) -> dict:
    with rasterio.open(data_dir / "sample_submission.tif") as t:
        tmpl = t.read(1)
        profile = dict(crs=t.crs, transform=t.transform, height=t.height, width=t.width)
    F = np.isfinite(tmpl)
    with rasterio.open(data_dir / "existing_faults.tif") as d:
        C = d.read(1) == 1
    with rasterio.open(lattice) as d:
        R = (d.read(1) > 0) & F

    d_lat = distance_transform_edt(~R)
    d_cat = distance_transform_edt(~C)

    U = F & (d_lat > LATTICE_RADIUS_PX)
    covered = F & (d_lat <= LATTICE_RADIUS_PX) & (d_cat > CATALOGUE_RADIUS_PX)

    n_u = int(U.sum())
    k_max = int(np.floor(cap * n_u / (1.0 - cap)))
    score = prior_scores(prior, data_dir, sgmc, F).ravel()
    cov_idx = np.flatnonzero(covered.ravel())
    # Descending prior score; deterministic tie-break by flat index.
    order = np.lexsort((cov_idx, -score[cov_idx]))
    k = min(k_max, cov_idx.size)
    chosen_cov = cov_idx[order[:k]]

    dots = U.ravel().copy()
    dots[chosen_cov] = True
    dots = dots.reshape(F.shape) & F

    out = np.full(F.shape, np.nan, dtype=np.float32)
    out[F] = 0.0
    out[dots] = 1.0

    out_tif.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out_tif, "w", driver="GTiff", dtype="float32", count=1, nodata=np.nan,
                       compress="deflate", **profile) as dst:
        dst.write(out, 1)

    n_dots = int(dots.sum())
    dots_within_lattice = int((dots & (d_lat <= LATTICE_RADIUS_PX)).sum())
    return {
        "prior": prior,
        "footprint_cells": int(F.sum()),
        "catalogue_cells_in_footprint": int((C & F).sum()),
        "lattice_dots_in_footprint": int(R.sum()),
        "uncovered_cells_all_placed": n_u,
        "covered_offcatalogue_candidates": int(covered.sum()),
        "overlap_cap": cap,
        "covered_dots_added": k,
        "covered_dots_max_allowed": k_max,
        "candidate_dots": n_dots,
        "dots_within_3px_of_lattice": dots_within_lattice,
        "expected_lattice_overlap_fraction": (dots_within_lattice / n_dots) if n_dots else None,
        "raster_sha256": sha256_file(out_tif),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument("--lattice", type=Path, required=True)
    ap.add_argument("--sgmc", type=Path, required=True)
    ap.add_argument("--prior", choices=PRIORS, default="lidar_step_max")
    ap.add_argument("--out", type=Path, required=True, help="output .tif path (staging)")
    ap.add_argument("--cap", type=float, default=OVERLAP_CAP)
    ap.add_argument("--sidecar", type=Path, required=True)
    args = ap.parse_args()
    if not (0.0 < args.cap < 0.70):
        raise SystemExit("cap must be in (0, 0.70)")
    info = build(args.data_dir, args.lattice, args.sgmc, args.out, args.cap, args.prior)
    info["created_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    args.sidecar.parent.mkdir(parents=True, exist_ok=True)
    args.sidecar.write_text(json.dumps(info, indent=2, allow_nan=False) + "\n")
    print(json.dumps(info, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
