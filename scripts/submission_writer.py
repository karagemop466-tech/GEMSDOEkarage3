#!/usr/bin/env python3
"""Canonical Protocol Rule 2 submission writer & automated 13-check GeoTIFF validator (`submission_writer.py`).

Delegates strictly to `gems32.submission` (zero private fork):
  - Enforces exact CRS (`EPSG:32611`), shape (`3730 x 3292`), and affine geotransform matching
    `sample_submission.tif`.
  - Accepts explicit binary emissions only; rejects implicit probability thresholding.
    Verifies all saved predictions strictly inside `[0.0, 1.0]` with `0` NaNs anywhere in the
    12,279,160-cell raster (`-zeros.tif`, `nodata=None`), preventing DrivenData's portal error
    `Predicted values must be in range [0, 1]` (`IR-34-NODATA-01`).
  - Masks known USGS/INGENIOUS catalogue traces (`labels.tif`) to `0.0` and builds a single-GeoTIFF `.zip`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems32 import submission  # noqa: E402
from gems32.paths import data_dir  # noqa: E402


def write_validated_submission(
    mask_or_probs: np.ndarray,
    slug: str,
    candidate_meta: dict,
    ddir: Path | None = None,
    out_dir: Path | None = None,
    timestamp_tag: str | None = None,
) -> dict:
    # Legacy argument name retained for callers; probabilities must be emitted explicitly.
    ddir = ddir or data_dir()
    out_dir = out_dir or (ROOT / "docs" / "downloads")
    sample_tif = ddir / "sample_submission.tif"
    labels_tif = ddir / "labels.tif"
    with rasterio.open(sample_tif) as ds:
        foot = np.isfinite(ds.read(1)) & (ds.read_masks(1) > 0)
        template_grid = (ds.crs, ds.shape, ds.transform)
    arr_in = submission.require_binary_mask(mask_or_probs, foot)
    if arr_in.shape != foot.shape:
        raise ValueError(f"Expected grid shape {foot.shape}, got {arr_in.shape}")
    for nk in ("submission_note_zeros", "submission_note_nan"):
        if nk in candidate_meta and len(str(candidate_meta[nk])) > 140:
            raise ValueError(f"{nk} exceeds 140 characters ({len(str(candidate_meta[nk]))} chars)")
    with rasterio.open(labels_tif) as ds:
        if (ds.crs, ds.shape, ds.transform) != template_grid or ds.count != 1:
            raise ValueError("Catalogue grid does not match the template")
        raw_labels = ds.read(1)
        if not np.isfinite(raw_labels[foot]).all():
            raise ValueError("Catalogue contains nonfinite values inside footprint")
        labels = (raw_labels > 0) & foot
    ts = timestamp_tag or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    meta_full = {
        "catalogue_hidden_mean": None,
        "catalogue_hidden_per_quadrant": {},
        "sgmc_prevalence_calibrated_dti": None,
        "drift_corrected_holdout_mean": None,
        "drift_corrected_per_quadrant": {},
        "predicted_leaderboard_dti": None,
        "ei_drift_corrected": None,
        "slot_decision": "HOLD-DO-NOT-SUBMIT",
    }
    meta_full.update(candidate_meta)

    bundle = submission.write_submission_pair(
        mask=arr_in & ~labels,
        foot=foot,
        labels=labels,
        template_tif=sample_tif,
        out_dir=out_dir,
        slug=slug,
        timestamp_tag=ts,
        candidate_meta=meta_full,
    )
    zeros_path = out_dir / bundle["zeros_tif"]["filename"]
    zip_path = zeros_path.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.write(zeros_path, arcname=zeros_path.name)
    bundle["zeros_zip"] = {
        "filename": zip_path.name,
        "path": str(zip_path),
        "size_bytes": zip_path.stat().st_size,
        "sha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
    }
    return bundle


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mask_npy", type=Path, help="Boolean or exact {0,1} .npy emission mask on the 3730x3292 grid")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--candidate-id", required=True)
    ap.add_argument("--note", required=True, help="Short DrivenData portal note (<= 140 chars)")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "docs" / "downloads")
    ap.add_argument("--data-dir", type=Path, default=None)
    args = ap.parse_args()

    if len(args.note) > 140:
        raise SystemExit(f"Submission note exceeds 140 characters ({len(args.note)} chars)")

    arr = np.load(args.mask_npy)
    meta = {
        "candidate_id": args.candidate_id,
        "description": f"Generated via scripts/submission_writer.py for {args.candidate_id}",
        "submission_note_zeros": args.note,
        "submission_note_nan": args.note,
    }
    bundle = write_validated_submission(
        arr, slug=args.slug, candidate_meta=meta, ddir=args.data_dir or data_dir(), out_dir=args.out_dir
    )
    print(json.dumps(bundle, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
