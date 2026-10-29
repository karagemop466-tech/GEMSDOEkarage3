#!/usr/bin/env python3
"""Candidate generator: CONSENSUS-HGRAD (non-fitted, two-field agreement).

Method (one sentence): keep the K footprint pixels where BOTH the magnetic
total-field horizontal gradient (band `tmi_hg`, band 3) AND the isostatic
gravity horizontal gradient (band `iso_grav_anom_hg`, band 18) are high,
scored as the min of their within-footprint percentile ranks.

Why this is a different lane from the registry: the score is a min-of-two
percentile ranks on two independent potential-field gradients, not a single
gradient magnitude, a DEM/curvature ridge, a model fit, or a catalogue-derived
feature. No model is trained, so no fold-local feature leakage can enter.

Nothing here is written as a score. Output is only a candidate raster plus
its metadata; the gates live in scripts/validate_submission.py.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems32.paths import data_dir, work_dir  # noqa: E402
from submission_writer import write_validated_submission  # noqa: E402

BAND_TMI_HG = 3   # tmi_hg, verified by description in training_features.tif
BAND_GRAV_HG = 18  # iso_grav_anom_hg, verified by description
SENTINEL = -1e30
EXPECTED_FOOTPRINT = 5_167_373


def rank01(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(values.size, dtype=np.float64)
    ranks[order] = np.arange(1, values.size + 1)
    return (ranks - 0.5) / values.size


def build(k: int, slug: str, ddir: Path, out_dir: Path) -> dict:
    with rasterio.open(ddir / "sample_submission.tif") as tpl:
        foot = np.isfinite(tpl.read(1)) & (tpl.read_masks(1) > 0)
    if int(foot.sum()) != EXPECTED_FOOTPRINT:
        raise ValueError(f"unexpected footprint size {int(foot.sum())}")
    with rasterio.open(ddir / "training_features.tif") as ds:
        tmi_hg = ds.read(BAND_TMI_HG).astype(np.float64)
        grav_hg = ds.read(BAND_GRAV_HG).astype(np.float64)
    # Pixels whose feature is a nodata sentinel are NOT eligible (never ranked, never emitted).
    valid = foot & np.isfinite(tmi_hg) & np.isfinite(grav_hg) & (tmi_hg > SENTINEL) & (grav_hg > SENTINEL)
    n_excluded = int(foot.sum() - valid.sum())
    if valid.sum() < k:
        raise ValueError("fewer eligible pixels than requested dots")

    r_mag = np.zeros(foot.shape, np.float64)
    r_grv = np.zeros(foot.shape, np.float64)
    r_mag[valid] = rank01(tmi_hg[valid])
    r_grv[valid] = rank01(grav_hg[valid])
    consensus = np.where(valid, np.minimum(r_mag, r_grv), 0.0).astype(np.float32)

    flat = consensus[valid]
    thresh_idx = np.argpartition(flat, -k)[-k:]
    mask = np.zeros(foot.shape, bool)
    mask_vals = np.zeros(int(valid.sum()), bool)
    mask_vals[thresh_idx] = True
    mask[valid] = mask_vals

    with rasterio.open(ddir / "labels.tif") as ds:
        labels_raw = ds.read(1)
    labels = (labels_raw > 0) & foot

    work = work_dir() / "surfaces"
    work.mkdir(parents=True, exist_ok=True)
    np.save(work / f"{slug}-consensus.npy", consensus)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    note = ("karage3 consensus-hgrad: top-%d px where magnetic TMI and isostatic gravity "
            "horizontal gradients both rank high; no model fit" % k)
    meta = {
        "candidate_id": slug,
        "description": "CONSENSUS-HGRAD: min(percentile rank tmi_hg, rank iso_grav_anom_hg), top-K in footprint, catalogue pixels removed",
        "submission_note_zeros": note,
        "submission_note_nan": note,
        "k_requested": k,
        "bands": {"tmi_hg": BAND_TMI_HG, "iso_grav_anom_hg": BAND_GRAV_HG},
        "labels_removed_pixels": int((mask & labels).sum()),
        "footprint_pixels_excluded_for_feature_sentinel": n_excluded,
    }
    bundle = write_validated_submission(mask, slug=slug, candidate_meta=meta, ddir=ddir,
                                        out_dir=out_dir, timestamp_tag=ts)
    bundle["note"] = note
    bundle["surface_npy"] = str(work / f"{slug}-consensus.npy")
    bundle["catalogue_pixels_in_mask_before_removal"] = int((mask & labels).sum())
    bundle["footprint_pixels_excluded_for_feature_sentinel"] = n_excluded
    return bundle


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--k", type=int, default=37654)
    ap.add_argument("--slug", default="karage3-consensus-hgrad-k37654")
    ap.add_argument("--data-dir", type=Path, default=None)
    ap.add_argument("--out-dir", type=Path, default=ROOT / "docs" / "downloads")
    args = ap.parse_args()
    if len(f"karage3 consensus-hgrad: top-{args.k} px where magnetic TMI and isostatic gravity horizontal gradients both rank high; no model fit") > 140:
        raise SystemExit("note exceeds 140 characters")
    out = build(args.k, args.slug, args.data_dir or data_dir(), args.out_dir)
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
