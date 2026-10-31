#!/usr/bin/env python3
"""E1 candidate: vertical-gravity zero-crossing ridges ranked by horizontal-gradient strength.

Hypothesis H-VGZC (experiment E1, lane = isostatic-gravity edge detection, layers
`iso_grav_anom_vg` + `iso_grav_anom_hg`):
  * Signature: a sign change of the vertical derivative of the isostatic gravity anomaly
    (zero-crossing = a density contrast edge) that coincides with a strong horizontal
    gradient (`iso_grav_anom_hg`) - the classic Blakely/Grauch-style edge test for a
    vertical density contrast.
  * Target: density contacts that are NOT in the USGS/INGENIOUS catalogue. Catalogue traces
    (labels.tif) are excluded within 3 px (300 m, the scoring kernel width).
  * Non-fault mimic: lithologic contacts, intrusion margins and basin-edge gravity steps.
  * Difference from repo lanes: the repo's gravity lanes use the horizontal gradient or the
    gravity slope; the vertical-derivative zero-crossing has not been used as a placement
    signal in the repo before this session (checked with grep over src, scripts, docs/research).

Placement rule (no tuning on the holdout):
  1. Candidate surface S = |grad_h| (smoothed hg) on pixels where vg changes sign in a
     2-pixel neighbourhood. Surface computed BEFORE placement and saved as a receipt.
  2. Exclude footprint-outside pixels, the 3,061 in-footprint nodata sentinel cells
     (-3.4e38) and their 3 px halo, and catalogue traces within 3 px.
  3. Greedy non-maximum suppression at 3 px spacing, highest S first, until K dots or exhausted.
     The zero-crossing set caps at ~21.6k dots under 3 px spacing, so K is never reached.
  K = 40,000 (the repo's typical density; budget-matched to the focus submissions).

OUTPUT: a single unsigned binary mask (npy) plus a receipt JSON. Writing the GeoTIFF
pair is done by the shared writer (`submission_writer.write_validated_submission`).
This script does not select a submission slot and does not claim a score.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter, maximum_filter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems32.paths import data_dir  # noqa: E402

K_DOTS = 40_000
STRENGTH_PCT = float(__import__("os").environ.get("VGZC_PCT", "0"))
SPACING_PX = 3
SENTINEL = -1e38


def load_band(ds, name):
    names = [d.split(" - ")[0] for d in ds.descriptions]
    arr = ds.read(names.index(name) + 1).astype(np.float64)
    arr[arr < SENTINEL] = np.nan
    return arr


def main(out_dir: Path) -> dict:
    ddir = data_dir()
    with rasterio.open(ddir / "sample_submission.tif") as t:
        foot = np.isfinite(t.read(1)) & (t.read_masks(1) > 0)
        grid = (t.crs, t.shape, t.transform)
    with rasterio.open(ddir / "training_features.tif") as ds:
        vg = load_band(ds, "iso_grav_anom_vg")
        hg = load_band(ds, "iso_grav_anom_hg")
    with rasterio.open(ddir / "labels.tif") as lab:
        if (lab.crs, lab.shape, lab.transform) != grid:
            raise ValueError("labels grid mismatch")
        catalogue = lab.read(1) > 0

    sentinel_in_foot = foot & ~np.isfinite(vg) | foot & ~np.isfinite(hg)
    valid = foot & np.isfinite(vg) & np.isfinite(hg)
    # Fill invalid cells with 0 only for the filter; they are excluded from placement below.
    vg_f = np.where(valid, vg, 0.0)
    hg_f = np.where(valid, hg, 0.0)
    vg_s = gaussian_filter(vg_f, sigma=1.0)
    hg_s = gaussian_filter(hg_f, sigma=1.0)

    # Zero-crossing: sign change to the right or down neighbour, both valid.
    zc = np.zeros(vg.shape, dtype=bool)
    sgn = np.sign(vg_s)
    ok_r = valid[:, :-1] & valid[:, 1:]
    zc[:, :-1] |= ok_r & (sgn[:, :-1] * sgn[:, 1:] < 0)
    ok_d = valid[:-1, :] & valid[1:, :]
    zc[:-1, :] |= ok_d & (sgn[:-1, :] * sgn[1:, :] < 0)

    # E2 option: require coincidence with a tmi_vg zero-crossing within 1 px (independent magnetic edge).
    coincide = __import__("os").environ.get("VGZC_COINCIDE", "")
    if coincide:
        with rasterio.open(ddir / "training_features.tif") as ds2:
            tv = load_band(ds2, coincide)
        tv_valid = foot & np.isfinite(tv)
        tv_s = gaussian_filter(np.where(tv_valid, tv, 0.0), sigma=1.0)
        zc2 = np.zeros(vg.shape, dtype=bool)
        sg2 = np.sign(tv_s)
        zc2[:, :-1] |= tv_valid[:, :-1] & tv_valid[:, 1:] & (sg2[:, :-1] * sg2[:, 1:] < 0)
        zc2[:-1, :] |= tv_valid[:-1, :] & tv_valid[1:, :] & (sg2[:-1, :] * sg2[1:, :] < 0)
        zc2_dil = maximum_filter(zc2, size=3)
        zc = zc & zc2_dil

    surface = np.where(zc & valid, np.abs(hg_s), 0.0)
    # Keep only strong edges inside the footprint (STRENGTH_PCT percentile of |hg| over the footprint; default 0 = keep every zero-crossing; the 75th-percentile variant gave only 5,464 dots).
    thr = np.percentile(np.abs(hg_s[valid]), STRENGTH_PCT)
    surface = np.where(surface >= thr, surface, 0.0)

    # Exclusions: catalogue within 3 px; sentinel/invalid cells and their 3 px halo.
    dist_cat = distance_transform_edt(~catalogue)
    bad = sentinel_in_foot | (foot & ~valid)
    dist_bad = distance_transform_edt(~bad) if bad.any() else np.full(bad.shape, np.inf)
    allowed = foot & valid & (dist_cat > SPACING_PX) & (dist_bad > SPACING_PX)
    surface = np.where(allowed, surface, 0.0)

    # Continuous surface receipt (before placement). Stored as SHA-256 of the float32 bytes.
    surf32 = surface.astype(np.float32)
    surface_sha = hashlib.sha256(surf32.tobytes()).hexdigest()

    # Greedy NMS at 3 px spacing.
    flat_order = np.argsort(-surface.ravel(), kind="stable")
    cand = flat_order[surface.ravel()[flat_order] > 0]
    H, W = surface.shape
    occupied = np.zeros((H, W), dtype=bool)
    mask = np.zeros((H, W), dtype=np.uint8)
    chosen = 0
    r = SPACING_PX
    for idx in cand:
        y, x = divmod(int(idx), W)
        y0, y1 = max(0, y - r), min(H, y + r + 1)
        x0, x1 = max(0, x - r), min(W, x + r + 1)
        if occupied[y0:y1, x0:x1].any():
            continue
        mask[y, x] = 1
        occupied[y, x] = True
        chosen += 1
        if chosen >= K_DOTS:
            break

    out_dir.mkdir(parents=True, exist_ok=True)
    np.save(out_dir / "vgzc_mask.npy", mask)
    receipt = {
        "hypothesis": "H-VGZC vertical-gravity zero-crossing edges x horizontal gradient strength",
        "layers": ["iso_grav_anom_vg", "iso_grav_anom_hg", "labels (catalogue exclusion)"],
        "footprint_cells": int(foot.sum()),
        "sentinel_in_footprint": int((foot & (~np.isfinite(vg) | ~np.isfinite(hg))).sum()),
        "zero_crossing_cells_in_footprint": int((zc & valid).sum()),
        "strength_percentile": STRENGTH_PCT,
        "strength_threshold": float(thr),
        "allowed_cells": int(allowed.sum()),
        "dots_target": K_DOTS,
        "dots_placed": int(chosen),
        "spacing_px": SPACING_PX,
        "surface_float32_sha256": surface_sha,
        "mask_npy_sha256": hashlib.sha256((out_dir / "vgzc_mask.npy").read_bytes()).hexdigest(),
        "template_grid": {"crs": str(grid[0]), "shape": list(grid[1]),
                          "transform": list(grid[2])[:6]},
        "coincidence_band": coincide or None,
        "note": "Candidate generation only. No holdout score, registry check or slot approval in this file.",
    }
    (out_dir / "vgzc_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    # Continuous surface is kept for the surface-before-placement rank-correlation check.
    np.save(out_dir / "vgzc_surface.npy", surf32)
    return receipt


if __name__ == "__main__":
    out = ROOT / ".cache" / "experiments" / "vgzc"
    print(json.dumps(main(out), indent=2))
