#!/usr/bin/env python3
"""Build the K3-OFFCAT-RIDGE binary emission (candidate `karage3-k4-offcat-ridge-20k`).

Hypothesis (catalogue-free): blind normal/strike-slip fault traces leave a persistent
edge signature in *independent* potential-field and DEM layers. We rank footprint
pixels by the mean percentile of three edge layers that were NOT derived from the
catalogue (labels.tif / existing_faults.tif are never read here, except to exclude
pixels already on the catalogue, which the shared writer enforces anyway):

    1. tmi_hg              magnetic total-intensity horizontal gradient (training band 3)
    2. iso_grav_anom_hg    isostatic gravity horizontal gradient       (training band 18)
    3. lidar step_max      DEM step / scarp height from corrected LiDAR (external, band 3)

Placement: Gaussian smoothing (sigma 1.5 px) -> 9x9 non-maximum suppression (one dot per
local maximum, no lattice) -> top-K maxima with K = 20,000. K is kept below 22,164 because
scripts/protocol_preflight.py reports that budget as the lattice-proven violation bound.

Named non-fault mimics: lithologic contacts, dikes and intrusive margins (magnetic and
gravity contrasts) and LiDAR scarps from landslides, road cuts, fences and acquisition
striping (DEM step). Canaries below test each input alone against catalogue labels.

Shared tools reused, not forked: scripts/submission_writer.py (binary contract,
label masking, 140-char note, grid match), scripts/evaluate_holdout.py (HOLDOUT-DTI).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from submission_writer import write_validated_submission  # noqa: E402

DDIR = ROOT / "data"
SLUG = "karage3-k4-offcat-ridge-20k"
K_DOTS = 20_000
NOTE = "Off-catalogue ridge detector: 20k NMS maxima of mag/grav gradient + LiDAR scarp step."


def percentile_rank(x: np.ndarray, valid: np.ndarray) -> np.ndarray:
    out = np.full(x.shape, np.nan, dtype=np.float32)
    v = x[valid]
    order = np.argsort(v, kind="stable")
    ranks = np.empty(v.size, dtype=np.float32)
    ranks[order] = (np.arange(v.size, dtype=np.float32) + 1) / v.size
    out[valid] = ranks
    return out


def read_band(path: Path, band: int, nodata_sentinel: float | None = None) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(band).astype(np.float32)
        nd = ds.nodata
    if nd is not None:
        a[a == nd] = np.nan
    if nodata_sentinel is not None:
        a[a < -1e38] = np.nan
    return a


def main() -> int:
    with rasterio.open(DDIR / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1)) & (ds.read_masks(1) > 0)
        template = (ds.crs, ds.shape, ds.transform)
    with rasterio.open(DDIR / "labels.tif") as ds:
        labels = (ds.read(1) > 0) & foot

    tmi_hg = read_band(DDIR / "training_features.tif", 3, nodata_sentinel=-3.4e38)
    iso_hg = read_band(DDIR / "training_features.tif", 18, nodata_sentinel=-3.4e38)
    step = read_band(DDIR / "external/lidar_scarp_features_u8.tif", 3)  # step_max
    valid_lidar = read_band(DDIR / "external/lidar_scarp_features_u8.tif", 12) > 0  # valid

    feats = {
        "tmi_hg": tmi_hg,
        "iso_grav_anom_hg": iso_hg,
        "lidar_step_max": np.where(valid_lidar, step, np.nan),
    }
    rank_maps = {}
    for name, arr in feats.items():
        ok = foot & np.isfinite(arr)
        rank_maps[name] = percentile_rank(arr, ok)

    all_ok = foot & np.isfinite(rank_maps["tmi_hg"]) & np.isfinite(rank_maps["iso_grav_anom_hg"]) & np.isfinite(rank_maps["lidar_step_max"])
    surface = np.zeros(foot.shape, dtype=np.float32)
    surface[all_ok] = (rank_maps["tmi_hg"][all_ok] + rank_maps["iso_grav_anom_hg"][all_ok] + rank_maps["lidar_step_max"][all_ok]) / 3.0
    surface = ndimage.gaussian_filter(surface, sigma=1.5) * all_ok
    surface[~all_ok] = 0.0

    # ----- Leakage canary (Protocol rule 4): each input alone vs catalogue labels.
    rng = np.random.default_rng(0)
    idx = np.flatnonzero(all_ok.ravel())
    sub = rng.choice(idx, size=min(400_000, idx.size), replace=False)
    yl = labels.ravel()[sub].astype(int)
    canary = {}
    for name, rm in list(rank_maps.items()) + [("combined_surface", surface)]:
        v = np.nan_to_num(rm.ravel()[sub], nan=0.0)
        canary[name] = {"auc_vs_catalogue_labels": float(roc_auc_score(yl, v)) if 0 < yl.sum() < yl.size else None}
    max_auc = max(c["auc_vs_catalogue_labels"] for c in canary.values() if c["auc_vs_catalogue_labels"] is not None)

    # ----- Placement: NMS maxima, catalogue-adjacent pixels excluded, top-K.
    near_label = ndimage.binary_dilation(labels, iterations=1)
    cand = all_ok & ~near_label
    mx = ndimage.maximum_filter(np.where(cand, surface, 0.0), size=9)
    peaks = cand & (surface > 0) & (surface == mx)
    rows, cols = np.nonzero(peaks)
    vals = surface[rows, cols]
    order = np.argsort(-vals, kind="stable")[:K_DOTS]
    mask = np.zeros(foot.shape, dtype=bool)
    mask[rows[order], cols[order]] = True
    assert mask.sum() == min(K_DOTS, rows.size), "dot count mismatch"

    # Pre-placement (surface-stage) dots: top-K surface pixels WITHOUT NMS, for the literal screen.
    pre = np.zeros(foot.shape, dtype=bool)
    sv = surface[cand]
    top_pre = np.argsort(-sv, kind="stable")[:K_DOTS]
    pre[np.flatnonzero(cand.ravel())[top_pre] // foot.shape[1], np.flatnonzero(cand.ravel())[top_pre] % foot.shape[1]] = True
    work = ROOT / ".cache" / "gems_work"
    work.mkdir(parents=True, exist_ok=True)
    np.save(work / "k4_surface.npy", surface)
    np.save(work / "k4_surface_preview_dots.npy", pre)
    np.save(work / "k4_final_dots.npy", mask)
    np.save(work / "k4_footprint.npy", foot)

    tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    meta = {
        "candidate_id": SLUG,
        "description": "Catalogue-free edge-persistence NMS detector (mag/grav gradients + LiDAR step)",
        "hypothesis": "Blind faults leave persistent edge signatures in independent potential-field and DEM layers.",
        "submission_note_zeros": NOTE,
        "submission_note_nan": NOTE,
        "feature_canary": canary,
        "n_peak_candidates": int(rows.size),
        "budget_dots": int(mask.sum()),
    }
    bundle = write_validated_submission(mask, slug=SLUG, candidate_meta=meta, ddir=DDIR,
                                        out_dir=ROOT / "docs" / "downloads", timestamp_tag=tag)
    summary = {
        "slug": SLUG,
        "timestamp": tag,
        "dots": int(mask.sum()),
        "peaks_available": int(rows.size),
        "max_single_feature_auc": max_auc,
        "canary": canary,
        "bundle": bundle,
        "template": {"crs": str(template[0]), "shape": list(template[1]), "transform": list(template[2])[:6]},
    }
    out = ROOT / "docs" / "downloads" / f"{SLUG}-{tag}-build.json"
    out.write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(json.dumps({"dots": summary["dots"], "max_auc": max_auc, "zeros": bundle["zeros_tif"]["filename"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
